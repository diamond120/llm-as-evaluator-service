import os
import pickle

from common.constants import DATA_DIR
from extra.data_ingest.input_connectors.base import InputConnectorInterface


class PickleConnector(InputConnectorInterface):
    def __init__(
        self, relative_file_path: str, common_metadata: dict | None = None, **params
    ):
        """Path is relative to the DATA_DIR"""
        super().__init__(common_metadata, **params)
        self.relative_file_path = relative_file_path

    def _load_data(self):
        full_path = os.path.join(DATA_DIR, self.relative_file_path)
        try:
            with open(full_path, "rb") as file:
                self._input_batch = pickle.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found at path: {full_path}")
