from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import json

from .types import BIDSException, BIDSVersion, BIDSDatasetType

# dataset_description.json at the root of the BIDS dataset
@dataclass
class BIDSDatasetDescription:
	name: str
	version: BIDSVersion
	dataset_type: BIDSDatasetType

	_JSON_FILENAME = "dataset_description.json"

	def _write_to_folder(self, folder: Path):
		try:
			json_file = open(folder / BIDSDatasetDescription._JSON_FILENAME, mode="x")
		except FileExistsError:
			raise BIDSException(f"can't write dataset description JSON to folder {folder} as it already exists there")

		json_out = {
			"Name": self.name,
			"BIDSVersion": str(self.version),
			"DatasetType": str(self.dataset_type)
		}
		json.dump(json_out, json_file)

	@classmethod
	def load_from_folder(cls, desc_json_folder: Path) -> BIDSDatasetDescription:
		try:
			desc_file = open(desc_json_folder / BIDSDatasetDescription._JSON_FILENAME, mode="r")
		except OSError as e:
			raise BIDSException(f"could not open BIDS description JSON file: {e}")
		
		return BIDSDatasetDescription._load_from_data(desc_file)
	
	@classmethod
	def _load_from_data(cls, reader: Any) -> BIDSDatasetDescription:
		try:
			json_data = json.load(reader)
		except Exception as e:
			raise BIDSException(f"could not read or parse BIDS JSON description file: {e}")
		
		if not isinstance(json_data, dict):
			raise BIDSException("BIDS JSON description is invalid (not a JSON object)")

		try:
			name = json_data["Name"]
			version = json_data["BIDSVersion"]
		except KeyError as e:
			raise BIDSException(f"missing mandatory field in BIDS JSON description file: {e}")
		
		try:
			dataset_type = json_data["DatasetType"]
		except KeyError:
			# DatasetType is recommended with "raw" as default
			dataset_type = BIDSDatasetType.RAW

		if not isinstance(name, str):
			raise BIDSException(f"invalid type for Name field in BIDS JSON description file: {name}")

		try:
			return BIDSDatasetDescription(name=name, version=BIDSVersion(version), dataset_type=BIDSDatasetType(dataset_type))
		except ValueError:
			raise BIDSException(f"invalid dataset type {dataset_type}")
