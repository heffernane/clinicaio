from enum import StrEnum
from dataclasses import dataclass

@dataclass
class Label:
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
		return f"{self._prefix}{self._id}"
	
	def __hash__(self):
		return self._id.value.__hash__()

# session id = ses-<label> (for folder names, entities, sessions.tsv, etc.)
@dataclass
class SessionId:
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
		return f"{self._prefix}{self._id}"
	
	def __hash__(self):
		return self._id.value.__hash__()

class BIDSException(Exception):
	pass

class BIDSDatasetType(StrEnum):
	RAW = "raw"
	DERIVATIVE = "derivative"
	STUDY = "study"

class BIDSVersion(str):
	pass

class DataType(StrEnum):
	FUNC = "func"
	DWI = "dwi"
	FMAP = "fmap"
	ANAT = "anat"
	PERF = "perf"
	MEG = "meg"
	EEG = "eeg"
	IEEG = "ieeg"
	BEH = "beh"
	PET = "pet"
	MICR = "micr"
	NIRS = "nirs"
	MOTION = "motion"
	MRS = "mrs"
	PHENOTYPE = "phenotype"
	EMG = "emg"

@dataclass
class Suffix(Label):
	def __hash__(self):
		return self.value.__hash__()

class FileExtension(StrEnum):
	NII = "nii"
	NII_GZ = "nii.gz"
	BVAL = "bval"
	BVEC = "bvec"
	JSON = "json"
	MAT = "mat"

	def is_nifti(self) -> bool:
		return self == FileExtension.NII or self == FileExtension.NII_GZ