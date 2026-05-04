from enum import StrEnum
from dataclasses import dataclass

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
			raise BIDSException(f"BIDS label {value} must be all [a-zA-Z0-9] characters")
		self.value = value

	def __str__(self):
		return self.value

# subject id = sub-<label> (for folder names, entities, participants.tsv, etc.)
@dataclass
class SubjectId:
	"""
	`BIDS specification <https://bids-specification.readthedocs.io/en/stable/common-principles.html#filesystem-structure>`__

	Parameters
	----------
	id : str
		a string of the form ``"sub-<label>"`` where label is an ASCII alphanumeric string

	Raises
	------
	BIDSException
		if the passed id string does not match the expected description above.
	"""

	_id: Label
	_prefix = "sub-"

	def __init__(self, id: str):
		if not id.startswith(self._prefix):
			raise BIDSException(f"BIDS subject ID {id} must start with {self._prefix}")
		
		try:
			self._id = Label(id.removeprefix(self._prefix))
		except BIDSException as e:
			raise BIDSException(f"BIDS subject id {id} had invalid label (in sub-<label>): {e}")

	def __str__(self):
		"""Returns the "sub-<label>" form of the subject ID"""
		return f"{self._prefix}{self._id}"
	
	def __repr__(self) -> str:
		return f"'{self}'"
	
	def __hash__(self):
		return self._id.value.__hash__()

# session id = ses-<label> (for folder names, entities, sessions.tsv, etc.)
@dataclass
class SessionId:
	"""
	`BIDS specification <https://bids-specification.readthedocs.io/en/stable/common-principles.html#filesystem-structure>`__

	Parameters
	----------
	id : str
		a string of the form ``"ses-<label>"`` where label is an ASCII alphanumeric string

	Raises
	------
	BIDSException
		if the passed id string does not match the expected description above.
	"""

	_id: Label
	_prefix = "ses-"

	def __init__(self, id: str):
		if not id.startswith(self._prefix):
			raise BIDSException(f"BIDS session ID {id} must start with {self._prefix}")
		
		try:
			self._id = Label(id.removeprefix(self._prefix))
		except BIDSException as e:
			raise BIDSException(f"BIDS session id {id} had invalid label (in ses-<label>): {e}")

	def __str__(self):
		"""Returns the "ses-<label>" form of the subject ID"""
		return f"{self._prefix}{self._id}"
	
	def __repr__(self) -> str:
		return f"'{self}'"
	
	def __hash__(self):
		return self._id.value.__hash__()

class BIDSException(Exception):
	pass

class DataType(StrEnum):
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

@dataclass
class Suffix(Label):
	"""
	An image file's suffix part. `BIDS specification <https://bids-specification.readthedocs.io/en/stable/common-principles.html#definitions>`__

	In a usual image file path ``sub-<label>/ses-<label>/<data_type>/sub-<label>_ses-<label>[_<entities>][_<SUFFIX>].<extension>``

	Suffixes must be ASCII alphanumeric strings.
	"""
	def __hash__(self):
		return self.value.__hash__()
	
	def __repr__(self) -> str:
		return f"'{self}'"

class FileExtension(StrEnum):
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

	def is_nifti(self) -> bool:
		"""Returns whether this is a NIFTI file extension (as compressed form is also common)"""
		return self == FileExtension.NII or self == FileExtension.NII_GZ

	def __repr__(self) -> str:
		return f"'{self}'"