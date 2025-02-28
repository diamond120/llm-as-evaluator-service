import os
import pickle
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from common.constants import DATA_DIR


class InputItemStatus(Enum):
    OK = "OK"
    ERROR = "ERROR"
    SKIPPED = "SKIPPED"


@dataclass
class InputItemMetadata:
    status: InputItemStatus = InputItemStatus.OK
    data: dict = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.status, InputItemStatus):
            raise ValueError("Status must be an instance of InputItemStatus Enum.")
        if not isinstance(self.data, dict):
            raise TypeError("Details must be a dictionary.")

    def serialize(self):
        return {"status": self.status.value, "data": self.data}

    @classmethod
    def deserialize(cls, d):
        return cls(status=InputItemStatus(d["status"]), data=d["data"])


@dataclass
class InputItem:
    content: str | None
    metadata: InputItemMetadata = field(default_factory=InputItemMetadata)

    def __post_init__(self):
        """Validate the InputItem to ensure content is a string and metadata is an instance of InputItemMetadata."""
        if self.metadata.status == InputItemStatus.OK and not isinstance(
            self.content, str
        ):
            raise ValueError(
                "The 'content' attribute must be a string if metadata status is OK."
            )
        if not isinstance(self.metadata, InputItemMetadata):
            raise TypeError(
                "The 'metadata' attribute must be an instance of InputItemMetadata."
            )

    def serialize(self):
        return {"content": self.content, "metadata": self.metadata.serialize()}

    @classmethod
    def deserialize(cls, d):
        return cls(
            content=d["content"], metadata=InputItemMetadata.deserialize(d["metadata"])
        )


@dataclass
class InputBatch:
    items: list[InputItem] | None = None
    metadata: dict | None = None

    def validate(self):
        """Validate the InputBatch to ensure all items are instances of InputItem."""
        if self.items is None:
            raise ValueError("Items cannot be None.")
        if not all(isinstance(item, InputItem) for item in self.items):
            raise ValueError("All items in the batch must be instances of InputItem.")
        if self.metadata is not None and not isinstance(self.metadata, dict):
            raise TypeError("Metadata must be a dictionary.")

    def serialize(self):
        return {
            "items": (
                [item.serialize() for item in self.items]
                if self.items is not None
                else None
            ),
            "metadata": self.metadata,
        }

    @classmethod
    def deserialize(cls, d):
        return cls(
            items=(
                [InputItem.deserialize(item) for item in d["items"]]
                if d["items"] is not None
                else None
            ),
            metadata=d["metadata"],
        )


class InputConnectorInterface(ABC):
    def __init__(self, common_metadata: dict | None = None, **params):
        """Initialize the input connector with given keyword parameters."""
        self.params = params
        self._input_batch = InputBatch(metadata=common_metadata)

    def load_data(self, cached_ok=False):
        """Load data into the connector. If cached_ok is True and data is already loaded, do nothing."""

        class_name = self.__class__.__name__
        tmp_result = None
        if cached_ok and self._input_batch.items is not None:
            print(f"{class_name}: Loading data: Using cached data.")
            tmp_result = self._input_batch
        else:
            print(f"{class_name}: Loading data: No cached data available, loading...")
            tmp_result = self._load_data()
            print(f"{class_name}: Loading data: Done.")
        if self._input_batch.items and self.params.get("remove_skipped", False):
            print("Skipped are filtered out.")
            self._input_batch.items = [
                item
                for item in self._input_batch.items
                if item.metadata.status != InputItemStatus.SKIPPED
            ]
        return tmp_result

    @abstractmethod
    def _load_data(self):
        pass

    def save_data(self, relative_save_path=None):
        """Save data to a pickle file at the given path or the path provided in params."""
        if self._input_batch.items is None:
            raise ValueError("No data to save. Load data first.")

        if relative_save_path is None:
            if "relative_save_path" in self.params:
                relative_save_path = self.params["relative_save_path"]
            else:
                raise ValueError(
                    "No save path provided. Provide a path or set it in params."
                )

        # Ensure that the directories in the relative path are created if missing
        full_path = os.path.join(DATA_DIR, relative_save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        full_path += ".pkl"
        with open(full_path, "wb") as file:
            pickle.dump(self.get_data(as_json=True), file)
        return full_path

    def _validate_data_type(self):
        """Validate _input_batch."""
        self._input_batch.validate()

    def get_data(self, as_json=False) -> dict | InputBatch:
        """Retrieve data from the connector. Raise an error if data is not loaded."""
        if self._input_batch.items is None:
            raise ValueError("Data not loaded. Call load_data first.")
        self._validate_data_type()
        if as_json:
            return self._input_batch.serialize()
        else:
            return self._input_batch
