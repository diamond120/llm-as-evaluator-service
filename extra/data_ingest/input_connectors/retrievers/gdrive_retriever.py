import copy
import io
import traceback
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable

import pandas as pd
from googleapiclient.http import MediaIoBaseDownload
from tqdm.auto import tqdm

from extra.data_ingest.gdrive_utils.auth import build_services


class DownloadStatus(Enum):
    OK = "OK"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass(eq=True)
class GDriveFile:
    file_id: str | None
    content: str | None = None
    original_file_uri: str | None = None
    revision_id: str | None = None
    revision_timestamp: datetime | None = None
    status: DownloadStatus = DownloadStatus.OK
    status_not_ok_msg: str | None = None


class RevisionSelectionByTS(Enum):
    """
    Enum for selecting a Google Drive file revision based on timestamp.

    Attributes:
        BEFORE_OR_EQ: Select the revision that was created before or at the same time as the specified timestamp.
        AFTER_OR_EQ: Select the revision that was created after or at the same time as the specified timestamp.
        LATEST: Select the most recent revision.
    """

    BEFORE_OR_EQ = "before_or_eq"
    AFTER_OR_EQ = "after_or_eq"
    LATEST = "latest"


class RevisionSelectionByRevId(Enum):
    """
    Enum for selecting a Google Drive file revision based on revision ID.

    Attributes:
        EQUAL: Select the revision that has the exact same revision ID.
        LATEST_NOT_EQ: Select the most recent revision and check that it is not equal to the specified revision ID.
    """

    EQUAL = "equal"
    LATEST_NOT_EQ = "latest_not_eq"


@dataclass
class RevisionInstruction(ABC):
    @abstractmethod
    def select_revision(self, revisions: list[dict], **params) -> dict | None:
        """If requested condition for selection fails, latest revision is returned with "failed_to_satisfy" field set to True."""
        pass


@dataclass
class RevisionInstructionByCallable(RevisionInstruction):
    callable: Callable[[list[dict], dict[str, Any]], dict | None] | None = None

    def select_revision(
        self, revisions: list[dict], **params: dict[str, Any]
    ) -> dict | None:
        if self.callable is None:
            raise ValueError("Callable is not defined.")
        return self.callable(revisions, params)


@dataclass
class RevisionInstructionByTS(RevisionInstruction):
    how: RevisionSelectionByTS
    utc_timestamp: datetime | None = None

    def select_revision(self, revisions: list[dict], **params) -> dict | None:
        # Implement the logic to select a revision based on timestamp here
        revisions.sort(key=lambda r: r["modifiedTime"], reverse=True)

        if self.how == RevisionSelectionByTS.LATEST:
            return revisions[0]
        if self.utc_timestamp is None:
            raise NotImplementedError(
                "The specified revision selection method is not supported."
            )
        if self.how == RevisionSelectionByTS.BEFORE_OR_EQ:
            utc_cutoff_timestamp = self.utc_timestamp

            # Sorted desc
            for revision in revisions:
                # Convert the modifiedTime of the revision to a datetime object
                modified_time = pd.to_datetime(revision["modifiedTime"], utc=True)

                if modified_time <= utc_cutoff_timestamp:
                    return revision
            print(
                f"Asked to find a revision before timestamp {utc_cutoff_timestamp} but it was not found. Returning latest!"
            )
            return {**revisions[0], "failed_to_satisfy": True}
        elif self.how == RevisionSelectionByTS.AFTER_OR_EQ:
            utc_cutoff_timestamp = self.utc_timestamp

            # Sorted desc, reversing it
            for revision in reversed(revisions):
                # Convert the modifiedTime of the revision to a datetime object
                modified_time = pd.to_datetime(revision["modifiedTime"], utc=True)

                if modified_time >= utc_cutoff_timestamp:
                    return revision
            print(
                f"Asked to find a revision after timestamp {utc_cutoff_timestamp} but it was not found. Returning latest!"
            )
            return {**revisions[0], "failed_to_satisfy": True}
        else:
            raise NotImplementedError(
                "This revision selection method is not implemented."
            )


@dataclass
class RevisionInstructionByRevId(RevisionInstruction):
    how: RevisionSelectionByRevId
    revision_id: str | None = None

    def select_revision(self, revisions: list[dict], **params) -> dict | None:
        # Implement the logic to select a revision based on revision ID here
        revisions.sort(key=lambda r: r["modifiedTime"], reverse=True)
        if self.revision_id is None:
            raise Exception("Revision value not defined for instruction by rev id!")
        if self.how == RevisionSelectionByRevId.EQUAL:
            # Find the revision that matches the revision_id
            for revision in revisions:
                if revision["id"] == self.revision_id:
                    return revision
            # If the revision is not found, return None
            print(f"Revision with id {self.revision_id} not found.")
            return {**revisions[0], "failed_to_satisfy": True}
        elif self.how == RevisionSelectionByRevId.LATEST_NOT_EQ:
            if revisions[0]["id"] == self.revision_id:
                return {**revisions[0], "failed_to_satisfy": True}
            else:
                return revisions[0]
        else:
            raise NotImplementedError(
                "The specified revision selection method is not supported."
            )


class GDriveRetriever:
    def __init__(
        self,
        gdrive_files_uri: list[str],
        revision_instructions_map: (
            dict[str, RevisionInstruction] | RevisionInstruction | None
        ) = None,
        max_workers: int = 10,
    ):
        """Revision instuctions that evaluate to failed will force the retriever to skip dowloading these files and mark them as SKIPPED."""
        if isinstance(revision_instructions_map, RevisionInstruction):
            revision_instructions_map = {"default": revision_instructions_map}

        if revision_instructions_map is not None:
            self.revision_instructions_map = copy.deepcopy(revision_instructions_map)
        else:
            self.revision_instructions_map = {}

        if "default" not in self.revision_instructions_map:
            self.revision_instructions_map["default"] = RevisionInstructionByTS(
                how=RevisionSelectionByTS.LATEST
            )

        self.gdrive_files_uri = gdrive_files_uri
        self.file_ids_map = self.parse_uri_to_ids(gdrive_files_uri)

        gdrive_files = []
        for original_uri, file_id in self.file_ids_map.items():
            gdrive_files.append(
                GDriveFile(
                    file_id=file_id,
                    original_file_uri=original_uri,
                )
            )
        self.gdrive_files = gdrive_files

        self.max_workers = max_workers

    def parse_uri_to_ids(self, uris: list[str]) -> dict[str, str | None]:
        """
        Parses a list of URIs to extract file IDs. URIs can be direct file IDs or Google Drive URLs.
        Returns a dictionary mapping each URI to its file ID or None if parsing fails.
        Prints an error message if parsing fails.
        """
        uri_to_file_id = {}
        for uri in uris:
            try:
                # Assuming the URI could be a direct file ID or a Google Drive URL
                if "colab.research.google.com" in uri:
                    # Extract the file ID from the URI and clean up any trailing '#' or '?'
                    file_id = uri.split("/")[-1].split("#")[0].split("?")[0]
                    uri_to_file_id[uri] = file_id
                else:
                    # If the URI is not a URL, assume it's a direct file ID
                    # Ensure that the URI does not contain a forward slash
                    if "/" not in uri:
                        uri_to_file_id[uri] = uri
                    else:
                        print(f"Invalid file ID format in URI '{uri}'")
                        uri_to_file_id[uri] = None
            except Exception as e:
                print(f"Failed to parse URI '{uri}': {e.__class__.__name__}: {str(e)}")
                uri_to_file_id[uri] = None
        return uri_to_file_id

    def _download_file(self, gdrive_file: GDriveFile) -> GDriveFile:
        if gdrive_file.file_id is None:
            gdrive_file.status = DownloadStatus.ERROR
            gdrive_file.status_not_ok_msg = "File id was not provided."
            return gdrive_file
        try:
            gdrive_file.content = self.__download_file(
                gdrive_file.file_id, gdrive_file.revision_id
            )
        except Exception as e:
            gdrive_file.status = DownloadStatus.ERROR
            gdrive_file.status_not_ok_msg = (
                f"Download failed with error: {e.__class__.__name__}: {str(e)}"
            )
            print(gdrive_file.status_not_ok_msg)
        return gdrive_file

    def __download_file(self, file_id: str, revision_id: str | None) -> str:
        """
        Downloads a notebook from Google Drive using a file ID and a revision ID.
        Returns a dictionary with the file ID and the parsed notebook content.
        """

        drive_service = build_services(services=["drive"])["drive"]
        # Request to download the file
        # Request to download the file, optionally specifying a revision
        if revision_id is not None:
            request = drive_service.revisions().get_media(
                fileId=file_id, revisionId=revision_id
            )
        else:
            request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        # Download the file
        done = False
        while not done:
            status, done = downloader.next_chunk()
            # print(f"Download progress: {int(status.progress() * 100)}%.")

        # Move the buffer's pointer to the beginning
        fh.seek(0)
        # Read the notebook content as a plain string
        file_content = fh.read().decode("utf-8")
        return file_content

    def populate_files_with_content(self):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for gdrive_file in self.gdrive_files:
                if gdrive_file.status != DownloadStatus.SKIPPED:
                    future = executor.submit(self._download_file, gdrive_file)
                    futures.append(future)
            for future in tqdm(futures, desc="Loading file contents"):
                try:
                    result = future.result()
                except Exception as e:
                    print(f"Failed to download file: {e.__class__.__name__}: {str(e)}")

    def _get_all_revisions(self, service, file_id, fields="id,modifiedTime"):
        try:
            # Get the revisions of the file
            revisions = (
                service.revisions()
                .list(fileId=file_id, pageSize=1000, fields=f"revisions({fields})")
                .execute()
            )
            return revisions["revisions"]
        except Exception as e:
            print(
                f"Error for file: {file_id}.\n Error: {e.__class__.__name__}: {str(e)}"
            )
            # traceback.print_exc()
            return None

    def get_revision(
        self, file_id: str, revision_instruction: RevisionInstruction
    ) -> dict | None:
        drive_service = build_services(services=["drive"])["drive"]
        # Get the revisions of the file
        revisions = self._get_all_revisions(drive_service, file_id)
        if revisions is None:
            return None
        return revision_instruction.select_revision(revisions, file_id=file_id)

    def populate_files_with_revisions(self):
        results = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for gdrive_file in self.gdrive_files:
                if gdrive_file.file_id is None:
                    continue

                revision_instruction = self.revision_instructions_map.get(
                    gdrive_file.original_file_uri,
                    self.revision_instructions_map["default"],
                )
                future = executor.submit(
                    self.get_revision, gdrive_file.file_id, revision_instruction
                )
                futures.append({"gdrive_file": gdrive_file, "revision": future})
            for future in tqdm(futures, desc="Loading revisions"):
                try:
                    revision = future["revision"].result() or {}
                    gdrive_file = future["gdrive_file"]
                    gdrive_file.revision_id = revision.get("id")
                    gdrive_file.revision_timestamp = revision.get("modifiedTime")
                    if revision.get("failed_to_satisfy"):
                        gdrive_file.status = DownloadStatus.SKIPPED
                        gdrive_file.status_not_ok_msg = (
                            "Failed to satisfy revision instruction."
                        )
                except Exception as e:
                    print(
                        f"An error occurred while getting the result from the revision id getter future: {e.__class__.__name__}: {str(e)}"
                    )
        return results

    def retrieve(self) -> list[GDriveFile]:
        """Retrieves the files with necessary revision ids."""
        self.populate_files_with_revisions()
        self.populate_files_with_content()
        return self.gdrive_files
