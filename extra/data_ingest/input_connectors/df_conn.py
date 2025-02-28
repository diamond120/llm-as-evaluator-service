import copy
from datetime import timedelta

import pandas as pd

from common.constants import GOOGLE_API_CREDENTIALS_PATH
from extra.data_ingest.gdrive_utils.sheet_utils import download_sheet_as_df
from extra.data_ingest.input_connectors.base import InputConnectorInterface
from extra.data_ingest.input_connectors.gdrive import GDriveConnector
from extra.data_ingest.input_connectors.retrievers.gdrive_retriever import (
    RevisionInstruction,
    RevisionInstructionByRevId,
    RevisionInstructionByTS,
    RevisionSelectionByRevId,
    RevisionSelectionByTS,
)


class DFConnector(InputConnectorInterface):
    def __init__(
        self,
        input_df: pd.DataFrame,
        gdrive_file_link_column_name: str,
        common_metadata: dict | None = None,
        make_columns_as_per_item_metadata: bool | list[str] = True,
        column_filter_map: dict[str, str] | None = None,
        # Revision instructions, one of
        # by time
        find_revision_by_timestamp_column_name: str | None = None,
        timestamp_column_timezone_delta: timedelta | None = None,
        # by revision id in url
        fetch_latest_revision_or_skip_if_url_contains_same_rev: bool = False,
        get_rev_from_url=False,
        # custom
        revision_instructions_map: (
            dict[str, RevisionInstruction] | RevisionInstruction | None
        ) = None,
        # general
        max_workers=10,
        **params,
    ):
        """
        Download google colab files specified by input params and google sheets.

        df instead of google sheet ids
        gdrive_file_link_column_name: name of the column containing the link to the colab file. Expected format is https://colab.research.google.com/*
        common_metadata: a dict to save as metadata for this input batch. Can be anything you need.
        make_columns_as_per_item_metadata: if True, keeps the rest of the columns for each row as item metadata.
        column_filter_map: a dict of column_name->value to filter the sheet by equality check.

        # Revision instuctions section, can be one or none of the following

        # Revision selection by timestamp

        find_revision_by_timestamp_column_name: column name containing a timestamp by which we find a revision of the file. The revision selected will be <= timestamp.
        timestamp_column_timezone_delta: timedelta to specify time offset from UTC for the timestamp. For example UTC+4 is timedelta(hours=4), can't be None if timestamp is used.

        # Revision selection by revision id in URL

        fetch_latest_revision_or_skip_if_url_contains_same_rev: if True, revision id is extracted from the URL and the file is downloaded
            only if latest revision is no longer revision in the URL (status SKIPPED). If no revision is provided, latest is returned.

        # Revision selection by a custom rule:
        revision_instructions_map: a map or a single default value for all items. A map is a dict initial_url->RevisionInstruction().
            See src/input_connectors/retrievers/gdrive_retriever.py for more on the instructions format.

        Specified columns must be present. rows with nan values for specified columns will be dropped
        """
        super().__init__(common_metadata, **params)
        self._input_df = input_df
        self.get_rev_from_url = get_rev_from_url
        self.gdrive_file_link_column_name = gdrive_file_link_column_name
        self.find_revision_by_timestamp_column_name = (
            find_revision_by_timestamp_column_name
        )
        self.timestamp_column_timezone_delta = timestamp_column_timezone_delta
        self.revision_instructions_map = copy.deepcopy(revision_instructions_map)
        self.column_filter_map = column_filter_map
        self.make_columns_as_per_item_metadata = make_columns_as_per_item_metadata
        self.fetch_latest_revision_or_skip_if_url_contains_same_rev = (
            fetch_latest_revision_or_skip_if_url_contains_same_rev
        )
        self.max_workers = max_workers

        if (
            bool(revision_instructions_map)
            + bool(find_revision_by_timestamp_column_name)
            + bool(self.fetch_latest_revision_or_skip_if_url_contains_same_rev)
        ) > 1:
            raise ValueError(
                "Exactly one of 'revision_instructions_map', 'find_revision_by_timestamp_column_name', "
                "or 'self.fetch_latest_revision_or_skip_if_url_contains_same_rev' must be provided."
            )
        if (
            find_revision_by_timestamp_column_name
            and not timestamp_column_timezone_delta
        ):
            raise ValueError(
                "'timestamp_column_timezone_delta' must be provided when 'find_revision_by_timestamp_column_name' is provided."
            )

    def filter_df(self, df):
        if not self.column_filter_map:
            return df
        for column, value in self.column_filter_map.items():
            df = df[df[column] == value]
        return df.copy()

    def get_source_df(self):
        """Assumes same structure for all sheets. Filters by provided map on init."""
        tasks_sheets_df = self._input_df
        print("All sheets are concatenated and dataframe is generated.")
        self._ensure_columns_presence(tasks_sheets_df)
        tasks_sheets_df = self.filter_df(tasks_sheets_df)
        return tasks_sheets_df

    def _ensure_columns_presence(self, df):
        columns_check = [
            self.gdrive_file_link_column_name,
            self.find_revision_by_timestamp_column_name,
        ]
        if self.column_filter_map:
            columns_check += [c for c in self.column_filter_map]
        columns_check = [col for col in columns_check if col is not None]
        for column_name in columns_check:
            if column_name is not None and column_name not in df.columns:
                raise ValueError(
                    f"Column '{column_name}' is missing from the dataframe but was provided at init."
                )
        self._drop_nan_rows_in_required_columns(df, columns_check)

    def _drop_nan_rows_in_required_columns(self, df, columns_check):
        before_drop_count = len(df)
        dropped_rows = df[df[columns_check].isna().any(axis=1)]
        df.dropna(subset=columns_check, inplace=True)
        after_drop_count = len(df)
        dropped_count = before_drop_count - after_drop_count
        if dropped_count > 0:
            dropped_row_indices = dropped_rows.index.tolist()
            print(
                f"Dropped {dropped_count} rows with NaN values in columns: {columns_check}"
            )
            # print(f"Rows dropped: {dropped_row_indices}")
        return df

    def df_to_file_items_with_metadata(self, df):
        if isinstance(self.make_columns_as_per_item_metadata, bool):
            gdrive_file_items = df.to_dict("records")
            for item in gdrive_file_items:
                item["file_uri"] = item.pop(self.gdrive_file_link_column_name)
        else:
            # make_columns_as_per_item_metadata is a list of specific columns
            gdrive_file_items = []
            for record in df.to_dict("records"):
                item_metadata = {
                    col: record[col] for col in self.make_columns_as_per_item_metadata
                }
                item_metadata["file_uri"] = record[self.gdrive_file_link_column_name]
                gdrive_file_items.append(item_metadata)
        return gdrive_file_items

    def generate_revision_instructions_map_from_ts_column(self, df):
        revisions_ts = df[
            [
                self.gdrive_file_link_column_name,
                self.find_revision_by_timestamp_column_name,
            ]
        ].copy()
        # Convert the column to datetime, taking into account the timezone delta, then to UTC
        timestamp_column = self.find_revision_by_timestamp_column_name
        datetime_series = pd.to_datetime(revisions_ts[timestamp_column])
        datetime_series = datetime_series.dt.tz_localize(
            None
        )  # Remove existing timezone information
        datetime_series = (
            datetime_series - self.timestamp_column_timezone_delta
        )  # Apply the timedelta
        revisions_ts[timestamp_column] = datetime_series.dt.tz_localize(
            "UTC"
        )  # Convert to UTC
        revision_instructions_map = {}
        for _, row in revisions_ts.iterrows():
            file_uri = row[self.gdrive_file_link_column_name]
            timestamp = row[self.find_revision_by_timestamp_column_name]
            revision_instructions_map[file_uri] = RevisionInstructionByTS(
                how=RevisionSelectionByTS.BEFORE_OR_EQ, utc_timestamp=timestamp
            )
        return revision_instructions_map

    def generate_revision_instructions_map_from_revisions_in_urls(self, df):
        gdrive_files_uris_to_prev_revisions = {}
        for uri in df[self.gdrive_file_link_column_name]:
            if "#revisionId=" in uri:
                uri_parts = uri.split("#revisionId=")
                gdrive_files_uris_to_prev_revisions[uri] = uri_parts[1].split("&")[0]
            else:
                gdrive_files_uris_to_prev_revisions[uri] = None

        revision_instructions_map = {}
        for uri, rev in gdrive_files_uris_to_prev_revisions.items():
            if rev is None:
                instruction = RevisionInstructionByTS(how=RevisionSelectionByTS.LATEST)
            else:
                if self.fetch_latest_revision_or_skip_if_url_contains_same_rev:
                    instruction = RevisionInstructionByRevId(
                        how=RevisionSelectionByRevId.LATEST_NOT_EQ, revision_id=rev
                    )
                elif self.get_rev_from_url:
                    instruction = RevisionInstructionByRevId(
                        how=RevisionSelectionByRevId.EQUAL, revision_id=rev
                    )
                else:
                    raise

            revision_instructions_map[uri] = instruction
        return revision_instructions_map

    def _load_data(self):
        df = self.get_source_df()

        if self.make_columns_as_per_item_metadata:
            gdrive_file_items = self.df_to_file_items_with_metadata(df)
        else:
            gdrive_file_items = df[self.gdrive_file_link_column_name].to_list()

        revision_instructions_map = self.revision_instructions_map
        if self.find_revision_by_timestamp_column_name is not None:
            revision_instructions_map = (
                self.generate_revision_instructions_map_from_ts_column(df)
            )
        if (
            self.fetch_latest_revision_or_skip_if_url_contains_same_rev
            or self.get_rev_from_url
        ):
            revision_instructions_map = (
                self.generate_revision_instructions_map_from_revisions_in_urls(df)
            )

        # revision_instructions_map = construct revision_instructions_map
        gdrive_connector = GDriveConnector(
            gdrive_file_items,
            common_metadata=None,
            revision_instructions_map=revision_instructions_map,
            max_workers=self.max_workers,
        )
        gdrive_connector.load_data()
        self._input_batch.items = gdrive_connector.get_data().items
