from data_ingest.input_connectors.base import (
    InputConnectorInterface,
    InputItem,
    InputItemMetadata,
    InputItemStatus,
)


class JSONConnector(InputConnectorInterface):
    def __init__(
        self, data_list: list[dict], common_metadata: dict | None = None, **params
    ):
        """Initialize with a list of dicts containing raw data field("content") and optional metadata, and common metadata."""
        super().__init__(common_metadata, **params)
        self.data_list = data_list
        for item in self.data_list:
            if not isinstance(item, dict) or "content" not in item:
                raise ValueError("Each item must be a dict and have a 'content' key")

    def _load_data(self):
        items = []
        for data_item in self.data_list:
            metadata_dict = {k: v for k, v in data_item.items() if k != "content"}
            metadata = InputItemMetadata(status=InputItemStatus.OK, data=metadata_dict)
            items.append(InputItem(content=data_item["content"], metadata=metadata))
        self._input_batch.items = items
