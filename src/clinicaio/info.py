from dataclasses import dataclass
from typing import Any, Optional

# sidecar file .json
# class ImageInfo:
# ...
# sidecar_dict: dict[str, Any]
# pass


@dataclass
class ImageScanInfo:
    """
    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#scans-file>`__
    """

    # TODO: proper typing for fields defined in BIDS specification
    other_fields: dict[str, Any]

    def all_fields(self) -> dict[str, Any]:
        return self.other_fields

    def is_empty(self) -> bool:
        return len(self.other_fields) == 0


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

    # It's preferable to avoid having two None-like SessionInfo: the real None stored in
    # session.info, and a SessionInfo with all None and {} fields. As such, just always
    # store a non optional SessionInfo in session.info, and check here if any field is actually
    # set. This is notably necessary to avoid having code that relies on the info being None
    # when there are some TSV files that have a row with all n/a values (except for the ID column)
    def is_empty(self) -> bool:
        return len(self.other_fields) == 0 and all(
            v is None for v in [self.acquisition_time, self.pathology]
        )


# Populated from participants.tsv from root of dataset
@dataclass
class SubjectInfo:
    """
    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#participants-file>`__
    """

    # FIXME: proper typing for the fields that BIDS defines?
    # age, handedness, etc.
    other_fields: dict[str, Any]

    def all_fields(self) -> dict[str, Any]:
        return self.other_fields

    def is_empty(self) -> bool:
        return len(self.other_fields) == 0
