from __future__ import annotations

from fileinput import filename
from typing import Optional, Iterable, Any
from dataclasses import dataclass, field
from pathlib import Path
# pydantic

import os

from .types import *
from .entities import *
from .dataset_description import *
from .query import *
from .tsv_utils import *

@dataclass
class BIDSDataset :
	_participants: dict[ParticipantId, Participant]
	_bids_path: Path
	description: BIDSDatasetDescription

	def __init__(self, bids_path: Path, description: BIDSDatasetDescription, participants: dict[ParticipantId, Participant] = {}):
		self._bids_path = bids_path
		self.description = description
		self._participants = participants

	def participant_by_id(self, id: str | ParticipantId) -> Optional[Participant]:
		return self._participants.get(id if isinstance(id, ParticipantId) else ParticipantId(id))

	def all_participants(self) -> Iterable[Participant]:
		return self._participants.values()

	def participants_count(self) -> int:
		return len(self._participants)

	def all_sessions(self) -> Iterable[tuple[Participant, Session]]:
		for participant in self.all_participants():
			yield from ((participant, session) for session in participant.all_sessions())

	def all_images(self) -> Iterable[tuple[Participant, Session, DataType, Image]]:
		for participant, session in self.all_sessions():
			yield from ((participant, session, data_type, image) for data_type, image in session.all_images())


	# read sessions.tsv and fill out info in all sessions
	@staticmethod
	def _populate_sessions_info(participant_dir: Path, participant_id: ParticipantId, sessions: dict[SessionId, Session]):
		sessions_tsv_path = Path(participant_dir) / f"{participant_id}_sessions.tsv"
		if not os.path.exists(sessions_tsv_path):
			return
		
		sessions_tsv_df = _read_tsv_as_df(sessions_tsv_path)
		if "session_id" not in sessions_tsv_df.columns:
			raise BIDSException(f"found sessions.tsv file {sessions_tsv_path} without required session_id column")

		for df_row in sessions_tsv_df.itertuples(index=False):
			session_id = df_row.session_id
			if session_id == None:
				continue
			try:
				session_id = SessionId(str(session_id))
			except BIDSException as e:
				raise BIDSException(f"found invalid session ID {session_id} in sessions.tsv file {sessions_tsv_path}: {e}")
			
			try:
				session = sessions[session_id]
			except KeyError:
				continue
				#raise BIDSException(f"could not find session of ID {session_id} referenced by TSV file {sessions_tsv_path}")

			info: dict[str, Any] = df_row._asdict()
			session.info = SessionInfo(
				acquisition_time=info.get("acq_time"),
				pathology=info.get("pathology"),
				other_fields=info
			)

	@staticmethod
	def _populate_participants_info(bids_dir: Path, participants: dict[ParticipantId, Participant]):
		participants_tsv_path = bids_dir / "participants.tsv"
		if not os.path.exists(participants_tsv_path):
			return
		
		participant_tsv_df = _read_tsv_as_df(participants_tsv_path)
		if "participant_id" not in participant_tsv_df.columns:
			raise BIDSException(f"{participants_tsv_path} did not have required participant_id column")
		
		for df_row in participant_tsv_df.itertuples(index=False):
			participant_id = df_row.participant_id
			if participant_id == None:
				continue
			try:
				participant_id = ParticipantId(str(participant_id))
			except BIDSException as e:
				raise BIDSException(f"found invalid participant ID {participant_id} in TSV file {participants_tsv_path}: {e}")
			
			try:
				participant = participants[participant_id]
			except KeyError:
				continue
				#raise BIDSException(f"could not find participant of ID {participant_id} referenced by TSV file {participants_tsv_path}")

			info: dict[str, Any] = df_row._asdict()
			participant.info = ParticipantInfo(
				other_fields=info
			)

	@classmethod
	def populate_from_dir(cls, bids_dir: Path, sessions_info: bool = False, participants_info: bool = False) -> BIDSDataset:
		unhandled_entries: list[str] = []

		try:
			description = BIDSDatasetDescription.load_from_folder(bids_dir)
		except BIDSException as e:
			raise BIDSException(f"could not read BIDS description from JSON file: {e}")

		participants: dict[ParticipantId, Participant] = {}

		# Populate participants/subjects
		for bids_child in os.scandir(bids_dir):
			# Handled once all participants have been read
			if bids_child.name == "participants.tsv":
				continue

			# Already handled above
			if bids_child.name == "dataset_description.json":
				continue

			if not bids_child.name.startswith("sub-"):
				unhandled_entries.append(bids_child.path)
				continue

			if not bids_child.is_dir():
				raise BIDSException(f"found sub- entry {bids_child.name} that was not a directory")
			
			try:
				participant_id = ParticipantId(bids_child.name)
			except BIDSException as e:
				raise BIDSException(f"Found invalid participant/subject ID {bids_child.name}: {e}")
			
			participant = Participant(sessions={}, id=participant_id)
			participants[participant.id] = participant

			# Populate participant's sessions
			for participant_child in os.scandir(bids_child.path):
				# Handled after all sessions have been read, to fill out the session info from the TSV file
				if participant_child.name == f"{participant.id}_sessions.tsv":
					continue

				if not participant_child.name.startswith("ses-"):
					unhandled_entries.append(participant_child.path)
					continue

				if not participant_child.is_dir():
					raise BIDSException(f"found ses- entry {bids_child.name}/{participant_child.name} that was not a directory")

				try:
					session_id = SessionId(participant_child.name)
				except BIDSException as e:
					raise BIDSException(f"Found invalid session ID {participant_child.name}: {e}")
				
				session = Session(id=session_id, _images={}, info=None)
				participant.sessions[session.id] = session

				# Populate the session's images, per-datatype
				for session_child in os.scandir(participant_child.path):
					try:
						data_type = DataType(session_child.name)
					except:
						unhandled_entries.append(session_child.path)
						continue

					if not session_child.is_dir():
						raise BIDSException(f"Found data type entry {bids_child.name}/{participant_child.name}/{session_child.name} that was not a directory")

					session_images: list[Image] = []

					for data_type_child in os.scandir(session_child.path):
						try:
							[before_ext, file_ext] = data_type_child.name.split(".", maxsplit=1)
						except ValueError:
							# no "." in string so can't decompose list in assignment
							unhandled_entries.append(data_type_child.path)
							continue

						try:
							extension = FileExtension(file_ext)
						except ValueError:
							# If this happens for legitimate files, you may need to add the file extension to the enumeration
							raise BIDSException(f"Found unknown file extension {file_ext} for file {data_type_child.path}")

						sub_ses_prefix = f"{participant.id}_{session.id}_"
						if not before_ext.startswith(sub_ses_prefix):
							raise BIDSException(f"expected {bids_child.name}/{participant_child.name}/{session_child.name}/{data_type_child.name} \
								filename to start with {sub_ses_prefix} due to its placement in the BIDS directory hierarchy")
						
						entities_and_suffix = before_ext.removeprefix(sub_ses_prefix)
						if len(entities_and_suffix) == 0:
							raise BIDSException(f"found image file {data_type_child.path} without any entity or suffix")
						
						entities = entities_and_suffix.split("_")
						suffix = None
						if "-" not in entities[-1]:
							try:
								suffix = Suffix(entities[-1])
							except BIDSException as e:
								raise BIDSException(f"found invalid suffix label for image file {data_type_child.path}: {e}")
							
							entities = entities[:-1]
						
						try:
							entities = Entities.from_str_list(entities)
						except BIDSException as e:
							raise BIDSException(f"found invalid entities for image file {data_type_child.path}: {e}")

						# All the usual filename validation is done for non-NIFTI files, so that
						# we do not end up in a situation where the companion files (.json, etc.)
						# are inaccessible due to invalid naming. We do not store those companion
						# files however: we just validate the paths, but only actually accessing
						# such companion files by their paths will tell if a particular one exists.
						if not extension.is_nifti():
							continue

						image = Image(nifti_extension=extension, entities=entities, suffix=suffix)
						session_images.append(image)


					session._images[data_type] = session_images
			
			if sessions_info:
				BIDSDataset._populate_sessions_info(
					participant_dir=Path(bids_child.path),
					participant_id=participant.id,
					sessions=participant.sessions
				)
		
		if participants_info:
			BIDSDataset._populate_participants_info(
				bids_dir=bids_dir,
				participants=participants
			)


		unhandled_entries = [str(Path(entry).relative_to(bids_dir)) for entry in unhandled_entries]
		print("UNHANDLED =", unhandled_entries)
		return BIDSDataset(bids_path=bids_dir, description=description, participants=participants)

	def _get_image_base_path(
		self,
		query_result: ImageQueryResult,
	) -> str:
		pid = query_result.participant.id
		sid = query_result.session.id
		image = query_result.image
		entities = "" if len(image.entities) == 0 else f"_{image.entities}"
		suffix = "" if image.suffix is None else f"_{image.suffix}"

		return str(self._bids_path / f"{pid}/{sid}/{query_result.data_type}/{pid}_{sid}{entities}{suffix}")
	
	def get_image_companion_file_path(
		self,
		query_result: ImageQueryResult,
		extension: FileExtension,
	) -> Path:
		return Path(f"{self._get_image_base_path(query_result)}.{extension}")
	
	def get_nifti_image_path(
		self,
		query_result: ImageQueryResult,
	) -> Path:
		return self.get_image_companion_file_path(query_result, query_result.image.nifti_extension)
	
	def write_root_file(self, file_name: str, write_binary: bool) -> Any:
		if "/" in file_name:
			raise BIDSException(f"BIDSDataset.write_root_file() is not meant to write in sub-folders ({file_name})")

		mode = "x" + ("b" if write_binary else "")
		try:
			return open(self._bids_path / file_name, mode)
		except FileExistsError:
			raise BIDSException(f"can't write root dataset file {filename} as it already exists")
		
	# Creates the dataset folder, writes the dataset description JSON, creates the participants and sessions
	# folders with their TSV files. Images are not written here. To decide what content to write in each image
	# file, you must then use Session.write_images().
	def write_dataset(self):
		try:
			os.mkdir(self._bids_path)
		except FileExistsError:
			raise BIDSException(f"BIDS can't be written as it already exists at {self._bids_path}")
		except FileNotFoundError:
			raise BIDSException(f"BIDS can't be written as one of its parent folders is missing ({self._bids_path})")
		
		self.description._write_to_folder(self._bids_path)
		for participant in self.all_participants():
			participant._write_to_folder(self._bids_path)

		_write_rows_to_tsv(
			tsv_path=self._bids_path / "participants.tsv",
			first_column_name="participant_id",
			rows=(participant.info.other_fields for participant in self.all_participants() if participant.info is not None),
		)


# Populated from participants.tsv from root of dataset
@dataclass
class ParticipantInfo:
	# FIXME: proper typing for the fields that BIDS defines?
	#age, handedness, etc.
	other_fields: dict[str, Any]

# aka Subject
# populated from sub-* folders
@dataclass
class Participant:
	sessions: dict[SessionId, Session]
	id: ParticipantId
	# https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#participants-file
	# from participants.tsv, matched by participant_id, if available (all Optional[Type] = None, if line missing or n/a value)
	info: Optional[ParticipantInfo] = None

	def all_sessions(self) -> Iterable[Session]:
		return self.sessions.values()

	def sessions_count(self) -> int:
		return len(self.sessions)

	def session_by_id(self, id: str | SessionId) -> Optional[Session]:
		return self.sessions.get(id if isinstance(id, SessionId) else SessionId(id))

	def all_images(self) -> Iterable[tuple[Session, DataType, Image]]:
		for session in self.all_sessions():
			yield from ((session, data_type, image) for data_type, image in session.all_images())

	def _write_to_folder(self, bids_dir: Path):
		participant_path = bids_dir / str(self.id)
		try:
			os.mkdir(participant_path)
		except FileExistsError:
			raise BIDSException(f"BIDS participant folder {participant_path} can't be written as it already exists")
		except FileNotFoundError:
			raise BIDSException(f"BIDS participant folder {participant_path} can't be written as one of its parent folders is missing")
		
		for session in self.all_sessions():
			session._write_to_folder(participant_path, self.id)

		_write_rows_to_tsv(
			participant_path / f"{self.id}_sessions.tsv",
			first_column_name="session_id",
			rows=(session.info.other_fields for session in self.all_sessions() if session.info is not None),
		 )



# Populated from sub-<label>/sub-<label>_sessions.tsv
@dataclass
class SessionInfo:
	# TODO: actual date type (handle BIDS units)
	acquisition_time: Optional[str]
	pathology: Optional[str]
	other_fields: dict[str, Any]

@dataclass
class ImageWriter:
	image: Image
	file_path_prefix: str

	def write_nifti(self) -> Any:
		"""Returns a file-object opened for binary writing, for the NIFTI image itself."""
		nifti_path = f"{self.file_path_prefix}.{self.image.nifti_extension}"
		try:
			return open(nifti_path, "xb")
		except FileExistsError:
			raise BIDSException("Can't write NIFTI image as it already exists")
	
	def write_companion_file(self, extension: FileExtension, write_binary: bool) -> Any:
		"""Returns a file-object opened for (eventually binary) writing, for this image's companion file with the given file extension"""
		companion_file_path = f"{self.file_path_prefix}.{extension}"
		mode = "x" + ("b" if write_binary else "")
		try:
			return open(companion_file_path, mode)
		except FileExistsError:
			raise BIDSException(f"can't write companion image file {extension} as it already exists")

@dataclass
class ImagesWriter:
	dataset: BIDSDataset
	participant: Participant
	session: Session

	# the key is the path of the image file relative to the session directory
	_scan_infos: dict[str, ImageScanInfo] = field(default_factory=lambda: {})
	
	def write_image(
		self, 
		data_type: DataType,
		image: Image,
	) -> ImageWriter:
		query_result = ImageQueryResult(
			participant=self.participant,
			session=self.session,
			data_type=data_type,
			image=image,
		)

		session_path = self.dataset._bids_path / f"{self.participant.id}/{self.session.id}"
		if image.scan_info is not None:
			image_nifti_path = self.dataset.get_nifti_image_path(query_result)
			image_relative_path = image_nifti_path.relative_to(session_path)
			self._scan_infos[str(image_relative_path)] = image.scan_info

		data_type_folder_path = session_path / f"{data_type}"
		try:
			os.mkdir(data_type_folder_path)
		except FileExistsError:
			pass
		except FileNotFoundError as e:
			raise BIDSException(f"one of the parent folders of {data_type_folder_path} does not exist. Make sure to create the participant and session folders first.")
		
		prefix = self.dataset._get_image_base_path(query_result)
		return ImageWriter(image=image, file_path_prefix=prefix)
	
	def __enter__(self):
		return self
	
	def __exit__(self, exc_type, exc, tb):
		# Do not write the scans.tsv if an error occurred
		if all(v is None for v in [exc_type, exc, tb]):
			# TODO: write scans.tsv from all the image info passed to the subsequent write_image() calls
			pid = self.participant.id
			sid = self.session.id
			scans_tsv_path = self.dataset._bids_path / f"{pid}/{sid}/{pid}_{sid}_scans.tsv"
			_write_rows_to_tsv(
				scans_tsv_path,
				first_column_name="filename",
				rows=(scan_info.other_fields | {"filename": filename} for filename, scan_info in self._scan_infos.items()),
			)

@dataclass
class Session:
	# FIXME: maybe Optional/None if sub-M01/anat/sub-M01_T1w.* as allowed for single-session subjects
	id: SessionId
	_images: dict[DataType, list[Image]] = field(default_factory=lambda: {})
	info: Optional[SessionInfo] = None

	def images_by_data_type(self, data_type: str | DataType) -> Iterable[Image]:
		return self._images.get(DataType(data_type)) or []

	def all_images(self) -> Iterable[tuple[DataType, Image]]:
		for data_type, images in self._images.items():
			yield from ((data_type, image) for image in images)

	def images_count(self, data_type: Optional[DataType] = None) -> int:
		if data_type is None:
			return sum(len(images) for images in self._images.values())
		else:
			images_for_data_type = self._images.get(data_type)
			return 0 if images_for_data_type is None else len(images_for_data_type)
		
	def _write_to_folder(self, participant_folder: Path, participant_id: ParticipantId):
		pass
		
	def write_images(self, dataset: BIDSDataset, participant: Participant) -> ImagesWriter:
		return ImagesWriter(dataset=dataset, participant=participant, session=self)

# sidecar file .json
class ImageInfo:
	# ...
	#sidecar_dict: dict[str, Any]
	pass

class ImageScanInfo:
	# TODO: proper typing for fields defined in BIDS specification
	other_fields: dict[str, Any]




@dataclass
class Image:
	nifti_extension: FileExtension
	entities: Entities
	suffix: Optional[Suffix] = None
	scan_info: Optional[ImageScanInfo] = None

	###### Loaded lazily and cached ####
	# from the session's *_scans.tsv
	# TODO: DATAFRAME?
	#scan_data_dict: dict[str, Any]
	# sidecar .json
	#info: ImageInfo
	# todo: expose filepath and data itself?
	#bval: int
	#bvec: int
