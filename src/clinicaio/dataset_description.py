"""Describing a BIDS dataset"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated

from packaging.version import Version
from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PlainSerializer,
)
from pydantic import (
    ValidationError as PydanticError,
)

from .types import BIDSException

_JSON_FILENAME = "dataset_description.json"


# dataset_description.json at the root of the BIDS dataset
class BIDSDatasetDescription(BaseModel):
    """
    The information that describes a given BIDS dataset.

    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/dataset-description.html>`__
    """

    model_config = ConfigDict(
        validate_assignment=True,
        validate_default=True,
        arbitrary_types_allowed=True,
        extra="ignore",
        strict=True,
    )

    name: str = Field(alias="Name")
    bids_version: Annotated[
        Version,
        Field(alias="BIDSVersion"),
        BeforeValidator(Version),
        PlainSerializer(str, return_type=str),
    ]
    dataset_type: BIDSDatasetType = Field(
        alias="DatasetType",
        # DatasetType is recommended with "raw" as default
        default_factory=lambda: BIDSDatasetType.RAW,
    )

    # Such an unidiomatic constructor is necessary because Pydantic defines its own in the parent
    # class and expects it to be there when going from JSON input, so we can't just redefine __init__()
    @classmethod
    def new(
        cls, dataset_type: BIDSDatasetType, *, name: str, bids_version: str
    ) -> BIDSDatasetDescription:
        """
        Creates a new dataset description object, to describe a BIDS dataset.
        """

        try:
            return BIDSDatasetDescription.model_validate(
                {
                    "name": name,
                    "dataset_type": dataset_type,
                    "bids_version": bids_version,
                },
                by_name=True,
            )
        except PydanticError as e:
            raise BIDSException._from_pydantic(
                "could not create new dataset description", e
            )

    def _write_to_folder(self, folder: Path) -> None:
        try:
            json_file = open(folder / _JSON_FILENAME, mode="x")
        except FileExistsError:
            raise
        except FileNotFoundError:
            raise

        # NOTE: the error handling needs to happen above, but make sure to use a with ...: construct
        # as otherwise the file will not be flushed or closed
        with json_file:
            print(self.model_dump_json(by_alias=True), file=json_file, end="")

    @classmethod
    def _load_from_folder(cls, desc_json_folder: Path) -> BIDSDatasetDescription:
        try:
            desc_file = open(desc_json_folder / _JSON_FILENAME, mode="r")
        except OSError as e:
            raise BIDSException("could not open BIDS description JSON file") from e

        with desc_file:
            return BIDSDatasetDescription._load_from_data(desc_file.read())

    @classmethod
    def _load_from_data(cls, desc_json: str) -> BIDSDatasetDescription:
        try:
            return BIDSDatasetDescription.model_validate_json(desc_json)
        except PydanticError as e:
            raise BIDSException._from_pydantic(
                f"could not validate BIDS dataset description from JSON {desc_json}", e
            )
        except TypeError as e:
            raise BIDSException(
                f"could not validate BIDS dataset description from JSON {desc_json} as one of the keys had the wrong type: {e}"
            ) from e


class BIDSDatasetType(str, Enum):
    """
    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/dataset-description.html#dataset_descriptionjson>`__
    """

    RAW = "raw"
    DERIVATIVE = "derivative"
    STUDY = "study"

    # FIXME: needed until migrated to Python >= 3.11 StrEnum
    def __str__(self) -> str:
        return self.value
