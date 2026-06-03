from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Annotated, TypeAlias

from pydantic import Strict, StringConstraints
from pydantic import ValidationError as PydanticError

Suffix: TypeAlias = Annotated[
    str, Strict(), StringConstraints(pattern="^[a-zA-Z0-9]+$")
]
"""
An image file's suffix part. `BIDS specification <https://bids-specification.readthedocs.io/en/stable/common-principles.html#definitions>`__

In a usual image file path ``sub-<label>/ses-<label>/<data_type>/sub-<label>_ses-<label>[_<entities>][_<SUFFIX>].<extension>``

Suffixes must be ASCII alphanumeric strings.
"""


# subject id = sub-<label> (for folder names, entities, participants.tsv, etc.)
SubjectId: TypeAlias = Annotated[
    str, Strict(), StringConstraints(pattern="^sub-[a-zA-Z0-9]+$")
]
"""
`BIDS specification <https://bids-specification.readthedocs.io/en/stable/common-principles.html#filesystem-structure>`__

A string of the form ``"sub-<label>"`` where label is an ASCII alphanumeric string
"""

# session id = ses-<label> (for folder names, entities, sessions.tsv, etc.)
SessionId: TypeAlias = Annotated[
    str, Strict(), StringConstraints(pattern="^ses-[a-zA-Z0-9]+$")
]
"""
`BIDS specification <https://bids-specification.readthedocs.io/en/stable/common-principles.html#filesystem-structure>`__

A string of the form ``"ses-<label>"`` where label is an ASCII alphanumeric string
"""


@dataclass
class Label:
    """
    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/common-principles.html#definitions>`__
    """

    value: str

    def __init__(self, value: str):
        if len(value) == 0:
            raise BIDSException("BIDS label can't be empty")

        if not (value.isascii() and value.isalnum()):
            raise BIDSException(
                f"BIDS label {value} must be all [a-zA-Z0-9] characters"
            )
        self.value = value

    def __str__(self) -> str:
        return self.value


class BIDSException(Exception):
    @classmethod
    def _from_pydantic(cls, prefix: str, err: PydanticError) -> BIDSException:
        last_err = err.errors()[0]
        err_loc = f'field "{last_err["loc"][0]}": ' if len(last_err["loc"]) > 0 else ""
        pydantic_msg = f"{err_loc}{last_err['msg']}"

        return BIDSException(f"{prefix}: {pydantic_msg}")


class DataType(str, Enum):
    """
    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/common-principles.html#definitions>`__
    """

    FUNC = "func"
    """task based and resting state functional MRI"""

    DWI = "dwi"
    """diffusion weighted imaging"""

    FMAP = "fmap"
    """field inhomogeneity mapping data such as field maps"""

    ANAT = "anat"
    """structural imaging such as T1, T2, PD, and so on"""

    PERF = "perf"
    """perfusion"""

    MEG = "meg"
    """magnetoencephalography"""

    EEG = "eeg"
    """electroencephalography"""

    IEEG = "ieeg"
    """intracranial electroencephalography"""

    BEH = "beh"
    """behavioral"""

    PET = "pet"
    """positron emission tomography"""

    MICR = "micr"
    """microscopy"""

    NIRS = "nirs"
    """near infrared spectroscopy"""

    MOTION = "motion"
    """motion"""

    MRS = "mrs"
    """magnetic resonance spectroscopy"""

    PHENOTYPE = "phenotype"
    """measurement and survey data"""

    EMG = "emg"
    """electromyography"""

    def __repr__(self) -> str:
        return f"'{self}'"

    def __str__(self) -> str:
        return self.value


class FileExtension(str, Enum):
    """The file extensions that can be encountered for BIDS image files and their companion files."""

    NII = "nii"
    """Uncompressed NIFTI"""

    NII_GZ = "nii.gz"
    """GZIP compressed NIFTI"""

    BVAL = "bval"
    """`BIDS specification <https://bids-specification.readthedocs.io/en/stable/glossary.html#bval-extensions>`__"""

    BVEC = "bvec"
    """`BIDS specification <https://bids-specification.readthedocs.io/en/stable/glossary.html#bvec-extensions>`__"""

    JSON = "json"
    """
	JSON. In the context of image files, these are
	`sidecar files <https://bids-specification.readthedocs.io/en/stable/glossary.html#bvec-extensions>`__
	which provide metadata that can't be stored/provided by the main NIFTI file itself (e.g. when converting
	from DICOM to NIFTI).
	"""

    MAT = "mat"
    TSV = "tsv"

    def is_nifti(self) -> bool:
        """Returns whether this is a NIFTI file extension (as compressed form is also common)"""
        return self == FileExtension.NII or self == FileExtension.NII_GZ

    def __repr__(self) -> str:
        return f"'{self}'"

    # FIXME: needed until migrated to Python >= 3.11 StrEnum
    def __str__(self) -> str:
        return self.value
