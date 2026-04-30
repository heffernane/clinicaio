from dataclasses import dataclass
from typing import Any, Optional

# sidecar file .json
#class ImageInfo:
	# ...
	#sidecar_dict: dict[str, Any]
	#pass


@dataclass
class ImageScanInfo:
	"""
	`BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#scans-file>`__
	"""
	
	# TODO: proper typing for fields defined in BIDS specification
	other_fields: dict[str, Any]


# Populated from sub-<label>/sub-<label>_sessions.tsv
@dataclass
class SessionInfo:
	"""
	`BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#sessions-file>`__
	"""
	
	# TODO: actual date type (handle BIDS units)
	acquisition_time: Optional[str]
	pathology: Optional[str]
	other_fields: dict[str, Any]

	def all_fields(self) -> dict[str, Any]:
		return self.other_fields | {
			"acq_time": self.acquisition_time,
			"pathology": self.pathology,
		}


# Populated from participants.tsv from root of dataset
@dataclass
class SubjectInfo:
	"""
	`BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#participants-file>`__
	"""
	# FIXME: proper typing for the fields that BIDS defines?
	#age, handedness, etc.
	other_fields: dict[str, Any]