import os

from extra.data_ingest.input_connectors.base import (
    InputConnectorInterface,
    InputItem,
    InputItemMetadata,
    InputItemStatus,
)


class LocalFilesConnector(InputConnectorInterface):
    def __init__(
        self, file_list: list[dict], common_metadata: dict | None = None, **params
    ):
        """Initialize with a list of dicts containing file paths and optional metadata, and common metadata."""
        super().__init__(common_metadata, **params)
        self.file_list = file_list

    def _load_data(self):
        items = []
        for file_info in self.file_list:
            file_path = file_info["file_path"]
            metadata_dict = file_info
            status = (
                InputItemStatus.OK
                if os.path.isfile(file_path)
                else InputItemStatus.ERROR
            )
            file_data = None
            if status == InputItemStatus.OK:
                with open(file_path, "r") as file:
                    file_data = file.read()
            metadata = InputItemMetadata(status=status, data=metadata_dict)
            items.append(InputItem(content=file_data, metadata=metadata))
        self._input_batch.items = items
