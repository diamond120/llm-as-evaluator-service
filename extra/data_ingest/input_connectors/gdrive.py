from extra.data_ingest.input_connectors.base import (
    InputConnectorInterface,
    InputItem,
    InputItemMetadata,
    InputItemStatus,
)
from extra.data_ingest.input_connectors.retrievers.gdrive_retriever import (
    DownloadStatus,
    GDriveRetriever,
    RevisionInstruction,
    RevisionInstructionByRevId,
    RevisionInstructionByTS,
)


class GDriveConnector(InputConnectorInterface):
    def __init__(
        self,
        gdrive_file_items: list[dict] | list[str],
        common_metadata: dict | None = None,
        revision_instructions_map: (
            dict[str, RevisionInstruction] | RevisionInstruction | None
        ) = None,
        max_workers=10,
        **params,
    ):
        """gdrive_file_items must include file_uri, the rest is metadata or be a str"""
        super().__init__(common_metadata, **params)
        self.gdrive_file_items = gdrive_file_items

        self._gdrive_files_uris, self._per_item_metadata = self._parse_file_items()

        self.revision_instructions_map = revision_instructions_map
        self.max_workers = max_workers

    def _parse_file_items(self):
        if self.gdrive_file_items and isinstance(self.gdrive_file_items[0], str):
            gdrive_files_uris = self.gdrive_file_items
            per_item_metadata = None
        else:
            gdrive_files_uris = [item["file_uri"] for item in self.gdrive_file_items]
            per_item_metadata = {
                item["file_uri"]: {k: v for k, v in item.items() if k != "file_uri"}
                for item in self.gdrive_file_items
            }
        return gdrive_files_uris, per_item_metadata

    def _convert_gdrive_files_to_items(self, gdrive_files):
        status_map = {
            DownloadStatus.SKIPPED: InputItemStatus.SKIPPED,
            DownloadStatus.ERROR: InputItemStatus.ERROR,
            DownloadStatus.OK: InputItemStatus.OK,
        }
        items = []
        for f in gdrive_files:
            metadata_dict = {
                "original_uri": f.original_file_uri,
                "file_id": f.file_id,
                "requested_revision_id": f.revision_id,
                "requested_revision_ts": f.revision_timestamp,
            }
            if f.status_not_ok_msg:
                metadata_dict["input_status_not_ok_msg"] = f.status_not_ok_msg
            if self._per_item_metadata is not None:
                metadata_dict.update(self._per_item_metadata[f.original_file_uri])

            status = status_map[f.status]
            metadata = InputItemMetadata(status=status, data=metadata_dict)
            file_data = InputItem(content=f.content, metadata=metadata)
            items.append(file_data)
        return items

    def _load_data(self):
        retriever = GDriveRetriever(
            self._gdrive_files_uris,
            revision_instructions_map=self.revision_instructions_map,
            max_workers=self.max_workers,
        )
        gdrive_files = retriever.retrieve()
        self._input_batch.items = self._convert_gdrive_files_to_items(gdrive_files)
