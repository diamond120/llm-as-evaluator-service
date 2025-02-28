import copy
from datetime import timedelta

import pandas as pd

from common.constants import GOOGLE_API_CREDENTIALS_PATH
from extra.data_ingest.gdrive_utils.sheet_utils import download_sheet_as_df
from extra.data_ingest.input_connectors.base import InputConnectorInterface
from extra.data_ingest.input_connectors.df_conn import DFConnector
from extra.data_ingest.input_connectors.retrievers.gdrive_retriever import (
    RevisionInstruction,
)


class GSheetsConnector(InputConnectorInterface):
    def __init__(
        self,
        sheet_id: str,
        sheet_names: list[str],
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

        sheet_id: Google Sheets id from the URL
        sheet_names: a list of sheet names to load and concatenate(sheet name metadata will be provided.)
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
        self.sheet_id = sheet_id
        self.sheet_names = sheet_names
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

    def _load_data(self):
        dataframes = []
        for sheet_name in self.sheet_names:
            df = download_sheet_as_df(
                GOOGLE_API_CREDENTIALS_PATH, self.sheet_id, sheet_name
            )
            df["__src_sheet_name"] = sheet_name
            dataframes.append(df)

        input_df = pd.concat(dataframes, ignore_index=True)

        df_connector = DFConnector(
            input_df=input_df,
            gdrive_file_link_column_name=self.gdrive_file_link_column_name,
            make_columns_as_per_item_metadata=self.make_columns_as_per_item_metadata,
            column_filter_map=self.column_filter_map,
            find_revision_by_timestamp_column_name=self.find_revision_by_timestamp_column_name,
            timestamp_column_timezone_delta=self.timestamp_column_timezone_delta,
            fetch_latest_revision_or_skip_if_url_contains_same_rev=self.fetch_latest_revision_or_skip_if_url_contains_same_rev,
            revision_instructions_map=self.revision_instructions_map,
            max_workers=self.max_workers,
            get_rev_from_url=self.get_rev_from_url,
        )
        df_connector.load_data()
        self._input_batch.items = df_connector.get_data().items
