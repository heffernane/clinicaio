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
	_subjects: dict[SubjectId, Subject]
	_bids_path: Path
	description: BIDSDatasetDescription

	def __init__(self, bids_path: Path, description: BIDSDatasetDescription):
		self._bids_path = bids_path
		self.description = description
		self._subjects = {}

	def subject_by_id(self, id: str | SubjectId) -> Optional[Subject]:
		return self._subjects.get(id if isinstance(id, SubjectId) else SubjectId(id))

	def all_subjects(self) -> Iterable[Subject]:
		return self._subjects.values()

	def subjects_count(self) -> int:
		return len(self._subjects)

	def all_sessions(self) -> Iterable[Session]:
		for subject in self.all_subjects():
			yield from (session for session in subject.all_sessions())

	def all_images(self) -> Iterable[Image]:
		for session in self.all_sessions():
			yield from session.all_images()

	def _get_full_path(self) -> Path:
		return self._bids_path


	# read sessions.tsv and fill out info in all sessions
	@staticmethod
	def _populate_sessions_info(subject_dir: Path, subject_id: SubjectId, sessions: dict[SessionId, Session]):
		sessions_tsv_path = Path(subject_dir) / f"{subject_id}_sessions.tsv"
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
	def _populate_subjects_info(bids_dir: Path, subjects: dict[SubjectId, Subject]):
		participants_tsv_path = bids_dir / "participants.tsv"
		if not os.path.exists(participants_tsv_path):
			return
		
		subject_tsv_df = _read_tsv_as_df(participants_tsv_path)
		if "participant_id" not in subject_tsv_df.columns:
			raise BIDSException(f"{participants_tsv_path} did not have required participant_id column")
		
		for df_row in subject_tsv_df.itertuples(index=False):
			subject_id = df_row.participant_id
			if subject_id == None:
				continue
			try:
				subject_id = SubjectId(str(subject_id))
			except BIDSException as e:
				raise BIDSException(f"found invalid subject ID {subject_id} in TSV file {participants_tsv_path}: {e}")
			
			try:
				subject = subjects[subject_id]
			except KeyError:
				continue
				#raise BIDSException(f"could not find subject of ID {subject_id} referenced by TSV file {participants_tsv_path}")

			info: dict[str, Any] = df_row._asdict()
			subject.info = SubjectInfo(
				other_fields=info
			)

	@classmethod
	def populate_from_dir(cls, bids_dir: Path, sessions_info: bool = False, subjects_info: bool = False) -> BIDSDataset:
		unhandled_entries: list[str] = []

		try:
			description = BIDSDatasetDescription.load_from_folder(bids_dir)
		except BIDSException as e:
			raise BIDSException(f"could not read BIDS description from JSON file: {e}")
		
		dataset = BIDSDataset(bids_path=bids_dir, description=description)

		# Populate subjects/subjects
		for bids_child in os.scandir(bids_dir):
			# Handled once all subjects have been read
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
				subject_id = SubjectId(bids_child.name)
			except BIDSException as e:
				raise BIDSException(f"Found invalid subject/subject ID {bids_child.name}: {e}")
			
			subject = dataset.add_subject(id=subject_id, info=None)

			# Populate subject's sessions
			for subject_child in os.scandir(bids_child.path):
				# Handled after all sessions have been read, to fill out the session info from the TSV file
				if subject_child.name == f"{subject.id}_sessions.tsv":
					continue

				if not subject_child.name.startswith("ses-"):
					unhandled_entries.append(subject_child.path)
					continue

				if not subject_child.is_dir():
					raise BIDSException(f"found ses- entry {bids_child.name}/{subject_child.name} that was not a directory")

				try:
					session_id = SessionId(subject_child.name)
				except BIDSException as e:
					raise BIDSException(f"Found invalid session ID {subject_child.name}: {e}")
				
				session = subject.add_session(id=session_id, info=None)

				# Populate the session's images, per-datatype
				for session_child in os.scandir(subject_child.path):
					try:
						data_type = DataType(session_child.name)
					except:
						unhandled_entries.append(session_child.path)
						continue

					if not session_child.is_dir():
						raise BIDSException(f"Found data type entry {bids_child.name}/{subject_child.name}/{session_child.name} that was not a directory")

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

						sub_ses_prefix = f"{subject.id}_{session.id}_"
						if not before_ext.startswith(sub_ses_prefix):
							raise BIDSException(f"expected {bids_child.name}/{subject_child.name}/{session_child.name}/{data_type_child.name} \
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

						session._add_image(
							data_type=data_type,

							nifti_extension=extension, 
							entities=entities, 
							suffix=suffix,
							scan_info=None,
						)
			
			if sessions_info:
				BIDSDataset._populate_sessions_info(
					subject_dir=Path(bids_child.path),
					subject_id=subject.id,
					sessions=subject._sessions
				)
		
		if subjects_info:
			BIDSDataset._populate_subjects_info(
				bids_dir=bids_dir,
				subjects=dataset._subjects
			)


		unhandled_entries = [str(Path(entry).relative_to(bids_dir)) for entry in unhandled_entries]
		print("UNHANDLED =", unhandled_entries)
		return dataset

	
	def write_root_file(self, file_name: str, write_binary: bool) -> Any:
		if "/" in file_name:
			raise BIDSException(f"BIDSDataset.write_root_file() is not meant to write in sub-folders ({file_name})")

		mode = "x" + ("b" if write_binary else "")
		try:
			return open(self._bids_path / file_name, mode)
		except FileExistsError:
			raise BIDSException(f"can't write root dataset file {filename} as it already exists")
		
	def add_subject(self, id: SubjectId, info: Optional[SubjectInfo]) -> Subject:
		if id in self._subjects:
			raise BIDSException(f"tried to add subject of ID {id} but it already exists within this dataset")

		subject = Subject(
			parent_dataset=self,
			id=id,
			info=info
		)
		self._subjects[id] = subject

		return subject

	# Creates the dataset folder, writes the dataset description JSON, creates the subjects and sessions
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
		for subject in self.all_subjects():
			subject._write_to_folder()

		_write_rows_to_tsv(
			tsv_path=self._bids_path / "participants.tsv",
			first_column_name="participant_id",
			rows=(subject.info.other_fields | {"participant_id": subject.id} for subject in self.all_subjects() if subject.info is not None),
		)

	
	def query_images(self, query: ImageQuery) -> Iterable[Image]:
		filtered_subjects = self.all_subjects() if len(query.subjects) == 0 else (self.subject_by_id(id) for id in query.subjects)
		
		for subject in filtered_subjects:
			if subject is None:
				continue

			filtered_sessions = subject.all_sessions() if len(query.sessions) == 0 else (subject.session_by_id(id) for id in query.sessions)

			for session in filtered_sessions:
				if session is None:
					continue
				
				image_per_data_type = session.all_images() if query.data_type is None else session.images_by_data_type(query.data_type)
				
				for image in image_per_data_type:
					if (query.suffix is not None) and (image.suffix != query.suffix):
						continue

					if len(query.entities) > 0 and (not image.entities.contains_all(query.entities)):
						continue
					
					yield image

	def query_images_nifti_paths(self, query: ImageQuery) -> Iterable[Path]:
		return (image.get_nifti_image_path() for image in self.query_images(query))
	
	def query_images_companions_paths(self, query: ImageQuery, extension: FileExtension) -> Iterable[Path]:
		return (image.get_image_companion_file_path(extension) for image in self.query_images(query))


# Populated from participants.tsv from root of dataset
@dataclass
class SubjectInfo:
	# FIXME: proper typing for the fields that BIDS defines?
	#age, handedness, etc.
	other_fields: dict[str, Any]

# aka Subject
# populated from sub-* folders
@dataclass
class Subject:
	parent_dataset: BIDSDataset

	id: SubjectId
	# https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#participants-file
	# from participants.tsv, matched by participant_id, if available (all Optional[Type] = None, if line missing or n/a value)
	info: Optional[SubjectInfo] = None
	_sessions: dict[SessionId, Session] = field(default_factory=lambda: {})

	def _get_full_path(self) -> Path:
		return self.parent_dataset._get_full_path() / f"{self.id}"

	def add_session(self, id: SessionId, info: Optional[SessionInfo]) -> Session:
		if id in self._sessions:
			raise BIDSException(f"tried to add session of ID {id} but it already exists within this subject")
		
		session = Session(
			parent_subject=self,
			id=id,
			info=info
		)
		self._sessions[id] = session

		return session

	def all_sessions(self) -> Iterable[Session]:
		return self._sessions.values()

	def sessions_count(self) -> int:
		return len(self._sessions)

	def session_by_id(self, id: str | SessionId) -> Optional[Session]:
		return self._sessions.get(id if isinstance(id, SessionId) else SessionId(id))

	def all_images(self) -> Iterable[Image]:
		for session in self.all_sessions():
			yield from session.all_images()

	def _write_to_folder(self):
		subject_path = self._get_full_path()
		try:
			os.mkdir(subject_path)
		except FileExistsError:
			raise BIDSException(f"BIDS subject folder {subject_path} can't be written as it already exists")
		except FileNotFoundError:
			raise BIDSException(f"BIDS subject folder {subject_path} can't be written as one of its parent folders is missing")
		
		for session in self.all_sessions():
			session._write_to_folder()

		_write_rows_to_tsv(
			subject_path / f"{self.id}_sessions.tsv",
			first_column_name="session_id",
			rows=(session.info.other_fields | {"session_id": session.id} for session in self.all_sessions() if session.info is not None),
		 )



# Populated from sub-<label>/sub-<label>_sessions.tsv
@dataclass
class SessionInfo:
	# TODO: actual date type (handle BIDS units)
	acquisition_time: Optional[str]
	pathology: Optional[str]
	other_fields: dict[str, Any]

@dataclass
class ImagesWriter:
	session: Session
	
	def write_image(
		self, 
		data_type: DataType,
		nifti_extension: FileExtension,
		entities: Entities,
		suffix: Optional[Suffix],
		scan_info: Optional[ImageScanInfo],
	) -> Image:
		image = self.session._add_image(data_type, nifti_extension, entities, suffix, scan_info)

		session_path = self.session._get_full_path()

		data_type_folder_path = session_path / f"{data_type}"
		try:
			os.mkdir(data_type_folder_path)
		except FileExistsError:
			pass
		except FileNotFoundError:
			raise BIDSException(f"one of the parent folders of {data_type_folder_path} does not exist. Make sure to create the subject and session folders first.")
		
		return image
	
	def __enter__(self):
		return self
	
	def __exit__(self, exc_type, exc, tb):
		# Do not write the scans.tsv if an error occurred
		if all(v is None for v in [exc_type, exc, tb]):
			sub_id = self.session.parent_subject.id
			ses_id = self.session.id
			session_path = self.session._get_full_path()
			scans_tsv_path = session_path / f"{sub_id}_{ses_id}_scans.tsv"

			rows = (
				({} if image.scan_info is None else image.scan_info.other_fields)
				| { "filename": str(image.get_nifti_image_path().relative_to(session_path)) }
				for image in self.session.all_images()
			)

			# We need to write the scans.tsv at the very end of the ImagesWriter "with ...: " scope because all the images
			# may not have the same fields, so the TSV header must be the union of all of them done once we know all
			# the images to write
			_write_rows_to_tsv(
				scans_tsv_path,
				first_column_name="filename",
				rows=rows,
			)

@dataclass
class Session:
	parent_subject: Subject

	id: SessionId
	_images: dict[DataType, list[Image]] = field(default_factory=lambda: {})
	info: Optional[SessionInfo] = None

	def _get_full_path(self) -> Path:
		return self.parent_subject._get_full_path() / f"{self.id}"

	def images_by_data_type(self, data_type: str | DataType) -> Iterable[Image]:
		return self._images.get(DataType(data_type)) or []

	def all_images(self) -> Iterable[Image]:
		for images in self._images.values():
			yield from (image for image in images)

	def images_count(self, data_type: Optional[DataType] = None) -> int:
		if data_type is None:
			return sum(len(images) for images in self._images.values())
		else:
			images_for_data_type = self._images.get(data_type)
			return 0 if images_for_data_type is None else len(images_for_data_type)

	def _write_to_folder(self):
		session_path = self._get_full_path()
		try:
			os.mkdir(session_path)
		except FileExistsError:
			raise BIDSException(f"BIDS session folder {session_path} can't be written as it already exists")
		except FileNotFoundError:
			raise BIDSException(f"BIDS session folder {session_path} can't be written as one of its parent folders is missing")
		
	def _add_image(
		self,
		data_type: DataType,
		nifti_extension: FileExtension,
		entities: Entities,
		suffix: Optional[Suffix],
		scan_info: Optional[ImageScanInfo],
	) -> Image:
		if not nifti_extension.is_nifti():
			raise BIDSException(f"provided non-NIFTI file extension {nifti_extension} when adding image to session")

		image = Image(
			parent_session=self,
			data_type=data_type,
			nifti_extension=nifti_extension,
			entities=entities,
			suffix=suffix,
			scan_info=scan_info
		)

		if data_type not in self._images:
			self._images[data_type] = []

		self._images[data_type].append(image)

		return image

	def write_images(self) -> ImagesWriter:
		return ImagesWriter(session=self)

# sidecar file .json
class ImageInfo:
	# ...
	#sidecar_dict: dict[str, Any]
	pass

@dataclass
class ImageScanInfo:
	# TODO: proper typing for fields defined in BIDS specification
	other_fields: dict[str, Any]

@dataclass
class Image:
	parent_session: Session
	data_type: DataType

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

	def _get_image_base_full_path(
		self,
	) -> Path:
		ses_id = self.parent_session.id
		sub_id = self.parent_session.parent_subject.id
		entities = "" if len(self.entities) == 0 else f"_{self.entities}"
		suffix = "" if self.suffix is None else f"_{self.suffix}"

		return self.parent_session._get_full_path() / f"{self.data_type}/{sub_id}_{ses_id}{entities}{suffix}"
	
	def get_image_companion_file_path(self, extension: FileExtension) -> Path:
		return self._get_image_base_full_path().with_suffix(f".{extension}")
	
	def get_nifti_image_path(self) -> Path:
		return self.get_image_companion_file_path(self.nifti_extension)
