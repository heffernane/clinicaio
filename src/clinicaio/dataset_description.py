from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version

from .types import BIDSException


# dataset_description.json at the root of the BIDS dataset
@dataclass(init=False)
class BIDSDatasetDescription:
    name: str
    version: Version
    dataset_type: BIDSDatasetType

    _JSON_FILENAME = "dataset_description.json"

    def __init__(
        self, dataset_type: BIDSDatasetType, *, name: str, version: str
    ) -> None:
        self.name = name
        try:
            self.version = Version(version)
        except InvalidVersion as e:
            raise BIDSException(f"invalid BIDS version {version}: {e}")

        self.dataset_type = dataset_type

    def _write_to_folder(self, folder: Path):
        try:
            json_file = open(folder / BIDSDatasetDescription._JSON_FILENAME, mode="x")
        except FileExistsError:
            raise BIDSException(
                f"can't write dataset description JSON to folder {folder} as it already exists there"
            )

        json_out = {
            "Name": self.name,
            "BIDSVersion": str(self.version),
            "DatasetType": str(self.dataset_type),
        }
        json.dump(json_out, json_file)

    @classmethod
    def _load_from_folder(cls, desc_json_folder: Path) -> BIDSDatasetDescription:
        try:
            desc_file = open(
                desc_json_folder / BIDSDatasetDescription._JSON_FILENAME, mode="r"
            )
        except OSError as e:
            raise BIDSException(f"could not open BIDS description JSON file: {e}")

        return BIDSDatasetDescription._load_from_data(desc_file)

    @classmethod
    def _load_from_data(cls, reader: Any) -> BIDSDatasetDescription:
        try:
            json_data = json.load(reader)
        except Exception as e:
            raise BIDSException(
                f"could not read or parse BIDS JSON description file: {e}"
            )

        if not isinstance(json_data, dict):
            raise BIDSException("BIDS JSON description is invalid (not a JSON object)")

        try:
            name = json_data["Name"]
            version = json_data["BIDSVersion"]
        except KeyError as e:
            raise BIDSException(
                f"missing mandatory field in BIDS JSON description file: {e}"
            )

        try:
            dataset_type = json_data["DatasetType"]
            try:
                dataset_type = BIDSDatasetType(dataset_type)
            except ValueError:
                raise BIDSException(f"invalid dataset type {dataset_type}")
        except KeyError:
            # DatasetType is recommended with "raw" as default
            dataset_type = BIDSDatasetType.RAW

        if not isinstance(name, str):
            raise BIDSException(
                f"invalid type for Name field in BIDS JSON description file: {name}"
            )
        if not isinstance(version, str):
            raise BIDSException(
                f"invalid type for BIDSVersion field in BIDS JSON description file: {version}"
            )

        return BIDSDatasetDescription(
            name=name, version=version, dataset_type=dataset_type
        )


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
