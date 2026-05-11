from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from pandas import DataFrame

from ._tsv_utils import _read_tsv_as_df, _write_rows_to_tsv
from .dataset_description import BIDSDatasetDescription
from .entities import Entities, EntitiesLike
from .image_query import ImageQuery
from .info import ImageScanInfo, SessionInfo, SubjectInfo
from .types import BIDSException, DataType, FileExtension, SessionId, SubjectId, Suffix


@dataclass
class BIDSDataset:
    """A BIDS dataset"""

    _subjects: dict[SubjectId, Subject]
    _bids_path: Path
    description: BIDSDatasetDescription

    def __init__(self, bids_path: Path, description: BIDSDatasetDescription):
        """
        Creates a new BIDS dataset. Useful when you want to write a new dataset to the filesystem.

        See also
        --------
        * :py:meth:`write_to_folder()`
        """
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
            yield from subject.all_sessions()

    def all_images(self) -> Iterable[Image]:
        for session in self.all_sessions():
            yield from session.all_images()

    def _get_full_path(self) -> Path:
        return self._bids_path

    @cached_property
    def _participants_tsv_file_name(self) -> str:
        return "participants.tsv"

    def populate_subjects_info_from_df(self, participants_tsv_df: DataFrame):
        """
        Populates the subjects informations from the given dataframe.
        The dataframe must have a ``participant_id`` column which corresponds to
        a subject's ID that's already present in this dataset. The other columns
        will be used as informations for the subject at hand: they will not be
        merged with the existing ones, instead they'll be replaced entirely.

        Warnings
        --------
        You should only ever use this function if it is more convenient enough
        for your use case when you are writing a new BIDS dataset. Filling-in
        the information directly from :py:meth:`add_subject` should be favored.
        """

        if "participant_id" not in participants_tsv_df.columns:
            raise BIDSException(
                f"dataframe did not have required participant_id column"
            )

        infos: list[dict[str, Any]] = participants_tsv_df.to_dict(orient="records")  # type: ignore
        for info in infos:
            subject_id = info.pop("participant_id", None)
            if subject_id is None:
                continue
            try:
                subject_id = SubjectId(str(subject_id))
            except BIDSException as e:
                raise BIDSException(
                    f"found invalid subject ID {subject_id} in dataframe: {e}"
                )

            subject = self.subject_by_id(subject_id)
            if subject is None:
                continue
                # raise BIDSException(f"could not find subject of ID {subject_id} referenced by TSV file {participants_tsv_path}")

            subject.info = SubjectInfo(
                other_fields={} if all(v is None for v in info.values()) else info
            )

    def _populate_subjects_info_from_tsv(self):
        participants_tsv_path = self._get_full_path() / self._participants_tsv_file_name
        if not os.path.exists(participants_tsv_path):
            return

        participants_tsv_df = _read_tsv_as_df(participants_tsv_path)
        try:
            self.populate_subjects_info_from_df(participants_tsv_df)
        except BIDSException as e:
            raise BIDSException(
                f"could not populate subjects info from TSV file {participants_tsv_path}: {e}"
            )

    @classmethod
    def populate_from_dir(
        cls,
        bids_dir: Path,
        *,
        subjects_info: bool,
        sessions_info: bool,
        image_scans_info: bool,
        _report_unhandled_entries: Callable[[list[str]], None] = lambda entries: None,
    ) -> BIDSDataset:
        """
        Read a BIDS dataset from the given BIDS directory.

        Parsing the various informations for subjects/sessions/images can be toggled,
        as these take the bulk of the loading time in most cases, so it's better to
        avoid reading them if you do not have a use for them. This is due to the informations
        being stored in tabular/TSV files instead of per-subject/session/image JSON file.

        Parameters
        ----------
        bids_dir : Path
                The directory where the BIDS dataset exists
        subjects_info : bool
                Whether to fill out subject information from the ``participants.tsv`` file
        sessions_info : bool
                Whether to fill out session information from the ``*_sessions.tsv`` files
        image_scans_info : bool
                Whether to fill out image scan information from the ``*_scans.tsv`` files

        Raises
        ------
        BIDSException
                Whenever an invalid (per BIDS specification) filename/path is encountered while walking the BIDS directory
        """
        unhandled_entries: list[str] = []

        try:
            description = BIDSDatasetDescription._load_from_folder(bids_dir)
        except BIDSException as e:
            raise BIDSException(f"could not read BIDS description from JSON file: {e}")

        dataset = BIDSDataset(bids_path=bids_dir, description=description)

        # Populate subjects/subjects
        for bids_child in os.scandir(bids_dir):
            # Handled once all subjects have been read
            if bids_child.name == dataset._participants_tsv_file_name:
                continue

            # Already handled above
            if bids_child.name == BIDSDatasetDescription._JSON_FILENAME:
                continue

            if not bids_child.name.startswith("sub-"):
                unhandled_entries.append(bids_child.path)
                continue

            if not bids_child.is_dir():
                raise BIDSException(
                    f"found sub- entry {bids_child.name} that was not a directory"
                )

            try:
                subject_id = SubjectId(bids_child.name)
            except BIDSException as e:
                raise BIDSException(
                    f"Found invalid subject/subject ID {bids_child.name}: {e}"
                )

            try:
                subject = dataset.add_subject(id=subject_id, info=None)

                unhandled_entries += subject._populate_sessions_from_folder(
                    sessions_info=sessions_info, image_scans_info=image_scans_info
                )
            except Exception as e:
                raise BIDSException(
                    f"got exception while adding subject {subject_id} and populating its sessions: {e}"
                )

        if subjects_info:
            dataset._populate_subjects_info_from_tsv()

        unhandled_entries = [
            str(Path(entry).relative_to(bids_dir)) for entry in unhandled_entries
        ]
        _report_unhandled_entries(unhandled_entries)
        return dataset

    def add_subject(self, id: str | SubjectId, info: Optional[SubjectInfo]) -> Subject:
        id = id if isinstance(id, SubjectId) else SubjectId(id)

        if id in self._subjects:
            raise BIDSException(
                f"tried to add subject of ID {id} but it already exists within this dataset"
            )

        subject = Subject(
            parent_dataset=self, id=id, info=SubjectInfo({}) if info is None else info
        )
        self._subjects[id] = subject

        return subject

    def write_to_folder(self, *, readme: str):
        """
        Creates the dataset folder, writes the dataset description JSON, creates the subjects and sessions
        folders with their TSV files. Images are not written here. To decide what content to write in each image
        file, you must then use :py:meth:`Session.write_images()`

        See also
        --------
        * :py:meth:`write_root_file`
        """
        try:
            os.mkdir(self._bids_path)
        except FileExistsError:
            raise BIDSException(
                f"BIDS can't be written as it already exists at {self._bids_path}"
            )
        except FileNotFoundError:
            raise BIDSException(
                f"BIDS can't be written as one of its parent folders is missing ({self._bids_path})"
            )

        self.description._write_to_folder(self._bids_path)
        for subject in self.all_subjects():
            subject._write_to_folder()

        _write_rows_to_tsv(
            tsv_path=self._bids_path / "participants.tsv",
            first_column_name="participant_id",
            rows=(
                subject.info.all_fields() | {"participant_id": subject.id}
                for subject in self.all_subjects()
                if not subject.info.is_empty()
            ),
        )

        with self.write_root_file("README", write_binary=False) as f:
            print(readme, file=f)

    def write_root_file(self, file_name: str, *, write_binary: bool) -> Any:
        """
        Creates and opens for writing the given file at the root of the dataset, eventually in "binary" mode
        (per Python's :py:func:`open`).

        Parameters
        ----------
        file_name : str
                The name of the file to write. Must not contain a ``/``
        write_binary : bool
                Whether to open the created file in binary or text writing mode

        Raises
        ------
        BIDSException
                if the file name contains ``/``, or if the file already exists.

        Returns
        -------
        the corresponding file-object opened in writing mode

        Examples
        --------

        .. code-block:: python

                with dataset.write_root_file("README", write_binary=False) as f:
                        print("Hello world!", file=f)
        """

        if "/" in file_name:
            raise BIDSException(
                f"BIDSDataset.write_root_file() is not meant to write in sub-folders ({file_name})"
            )

        mode = "x" + ("b" if write_binary else "")
        try:
            return open(self._bids_path / file_name, mode)
        except FileExistsError:
            raise BIDSException(
                f"can't write root dataset file {file_name} as it already exists"
            )

    def query_images(self, query: ImageQuery) -> Iterable[Image]:
        """
        Returns all the images matching the query.
        See :py:class:`~clinicaio.image_query.ImageQuery` for details on the query itself.

        See also
        --------
        * :py:meth:`query_images_nifti_paths`
        * :py:meth:`query_images_companions_paths`
        """
        filtered_subjects = (
            self.all_subjects()
            if len(query.subjects) == 0
            else (self.subject_by_id(id) for id in query.subjects)
        )

        for subject in filtered_subjects:
            if subject is None:
                continue

            filtered_sessions = (
                subject.all_sessions()
                if len(query.sessions) == 0
                else (subject.session_by_id(id) for id in query.sessions)
            )

            for session in filtered_sessions:
                if session is None:
                    continue

                image_per_data_type = (
                    session.all_images()
                    if query.data_type is None
                    else session.images_by_data_type(query.data_type)
                )

                for image in image_per_data_type:
                    if (query.suffix is not None) and (image.suffix != query.suffix):
                        continue

                    if len(query.entities) > 0 and (
                        not image.entities.contains_all(query.entities)
                    ):
                        continue

                    yield image

    def query_images_nifti_paths(self, query: ImageQuery) -> Iterable[Path]:
        """
        Convenience function that only returns the NIFTI image paths instead of the images themselves.
        See :py:meth:`query_images`.
        """
        return (image.get_nifti_image_path() for image in self.query_images(query))

    def query_images_companions_paths(
        self, query: ImageQuery, extension: FileExtension
    ) -> Iterable[Path]:
        """
        Convenience function that only returns the companion image paths with the given file extension
        instead of the images themselves. See :py:meth:`query_images`.
        """
        return (
            image.get_image_companion_file_path(extension)
            for image in self.query_images(query)
        )


# populated from sub-* folders
@dataclass
class Subject:
    parent_dataset: BIDSDataset = field(repr=False, compare=False)

    id: SubjectId
    # https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#participants-file
    # from participants.tsv, matched by participant_id, if available (all Optional[Type] = None, if line missing or n/a value)
    info: SubjectInfo
    _sessions: dict[SessionId, Session] = field(default_factory=lambda: {})

    def _get_full_path(self) -> Path:
        return self.parent_dataset._get_full_path() / f"{self.id}"

    def add_session(self, id: str | SessionId, info: Optional[SessionInfo]) -> Session:
        id = id if isinstance(id, SessionId) else SessionId(id)

        if id in self._sessions:
            raise BIDSException(
                f"tried to add session of ID {id} but it already exists within this subject"
            )

        session = Session(
            parent_subject=self,
            id=id,
            info=SessionInfo(None, None, {}) if info is None else info,
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

    @cached_property
    def _sessions_tsv_file_name(self) -> str:
        return f"{self.id}_sessions.tsv"

    def _write_to_folder(self):
        subject_path = self._get_full_path()
        try:
            os.mkdir(subject_path)
        except FileExistsError:
            raise BIDSException(
                f"BIDS subject folder {subject_path} can't be written as it already exists"
            )
        except FileNotFoundError:
            raise BIDSException(
                f"BIDS subject folder {subject_path} can't be written as one of its parent folders is missing"
            )

        for session in self.all_sessions():
            session._write_to_folder()

        _write_rows_to_tsv(
            subject_path / self._sessions_tsv_file_name,
            first_column_name="session_id",
            rows=(
                session.info.all_fields() | {"session_id": session.id}
                for session in self.all_sessions()
                if not session.info.is_empty()
            ),
        )

    def populate_sessions_info_from_df(self, sessions_tsv_df: DataFrame):
        """
        Populates the sessions informations from the given dataframe.
        The dataframe must have a ``session_id`` column which corresponds to
        a session's ID that's already present in this dataset's subject. The other columns
        will be used as informations for the session at hand: they will not be
        merged with the existing ones, instead they'll be replaced entirely.

        Warnings
        --------
        You should only ever use this function if it is more convenient enough
        for your use case when you are writing a new BIDS dataset. Filling-in
        the information directly from :py:meth:`add_session` should be favored.
        """

        if "session_id" not in sessions_tsv_df.columns:
            raise BIDSException(f"dataframe did not have required session_id column")

        infos: list[dict[str, Any]] = sessions_tsv_df.to_dict(orient="records")  # type: ignore
        for info in infos:
            session_id = info.pop("session_id", None)
            if session_id is None:
                continue
            try:
                session_id = SessionId(str(session_id))
            except BIDSException as e:
                raise BIDSException(
                    f"found invalid session ID {session_id} in dataframe: {e}"
                )

            session = self.session_by_id(session_id)
            if session is None:
                continue
                # raise BIDSException(f"could not find session of ID {session_id} referenced by TSV file {sessions_tsv_path}")

            has_any_field = all(v is None for v in info)
            session.info = SessionInfo(
                acquisition_time=info.pop("acq_time", None),
                pathology=info.pop("pathology", None),
                other_fields=info if has_any_field else {},
            )

    def _populate_sessions_info_from_tsv(self):
        """Reads the subject's sessions.tsv and fills out info in all sessions"""
        sessions_tsv_path = self._get_full_path() / self._sessions_tsv_file_name
        if not os.path.exists(sessions_tsv_path):
            return

        sessions_tsv_df = _read_tsv_as_df(sessions_tsv_path)
        try:
            self.populate_sessions_info_from_df(sessions_tsv_df)
        except BIDSException as e:
            raise BIDSException(
                f"could not populate sessions info from TSV file {sessions_tsv_path}: {e}"
            )

    def _populate_sessions_from_folder(
        self, *, sessions_info: bool, image_scans_info: bool
    ) -> list[str]:
        unhandled_entries: list[str] = []

        # Populate subject's sessions
        for child in os.scandir(self._get_full_path()):
            # Handled after all sessions have been read, to fill out the session info from the TSV file
            if child.name == self._sessions_tsv_file_name:
                continue

            if not child.name.startswith("ses-"):
                unhandled_entries.append(child.path)
                continue

            if not child.is_dir():
                raise BIDSException(
                    f"found ses- entry {child.name} that was not a directory"
                )

            try:
                session_id = SessionId(child.name)
            except BIDSException as e:
                raise BIDSException(f"Found invalid session ID {child.name}: {e}")

            try:
                session = self.add_session(id=session_id, info=None)

                session._populate_images_from_folder(image_scans_info=image_scans_info)
            except Exception as e:
                raise BIDSException(
                    f"got exception while adding session {session_id} and populating its images: {e}"
                )

        if sessions_info:
            self._populate_sessions_info_from_tsv()

        return unhandled_entries


@dataclass
class ImagesWriter:
    """
    Automatic image scan info writer.

    The goal of this class is to automatically write the session's ``*_scans.tsv`` file with all the information
    provided in each image's scan_info. This is necessary due to the tabular nature of the file, and the missing
    guarantee that all images will provide the same columns.

    Examples
    --------

    `Jupyter BIDS writing example <demo_BIDS_write_images.ipynb>`__

    TODO: use nbsphinx or myst-nb to display the notebook **inline** here instead of copy pasting or moving it
    """

    session: Session

    def write_image(
        self,
        data_type: DataType,
        nifti_extension: FileExtension,
        entities: EntitiesLike,
        suffix: Optional[Suffix | str],
        scan_info: Optional[ImageScanInfo],
    ) -> Image:
        if suffix is not None:
            suffix = suffix if isinstance(suffix, Suffix) else Suffix(suffix)

        image = self.session._add_image(
            data_type, nifti_extension, Entities.from_any(entities), suffix, scan_info
        )

        session_path = self.session._get_full_path()

        data_type_folder_path = session_path / f"{data_type}"
        try:
            os.mkdir(data_type_folder_path)
        except FileExistsError:
            pass
        except FileNotFoundError:
            raise BIDSException(
                f"one of the parent folders of {data_type_folder_path} does not exist. Make sure to create the subject and session folders first."
            )

        return image

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Do not write the scans.tsv if an error occurred
        if all(v is None for v in [exc_type, exc, tb]):
            session_path = self.session._get_full_path()
            scans_tsv_path = session_path / self.session._scans_tsv_file_name

            rows = (
                image.scan_info.all_fields()
                | {
                    "filename": str(
                        image.get_nifti_image_path().relative_to(session_path)
                    )
                }
                for image in self.session.all_images()
                if not image.scan_info.is_empty()
            )

            # We need to write the scans.tsv at the very end of the ImagesWriter "with ...: " scope because all the images
            # may not have the same fields, so the TSV header must be the union of all of them done once we know all
            # the images to write
            _write_rows_to_tsv(
                scans_tsv_path,
                first_column_name="filename",
                rows=rows,
            )


@dataclass
class Session:
    parent_subject: Subject = field(repr=False, compare=False)

    id: SessionId
    info: SessionInfo
    _images: dict[DataType, list[Image]] = field(default_factory=lambda: {})

    def _get_full_path(self) -> Path:
        return self.parent_subject._get_full_path() / f"{self.id}"

    def images_by_data_type(self, data_type: str | DataType) -> Iterable[Image]:
        return self._images.get(DataType(data_type)) or []

    def all_images(self) -> Iterable[Image]:
        """Returns all the images that are part of this session"""
        for images in self._images.values():
            yield from images

    def images_count(self, data_type: Optional[DataType] = None) -> int:
        """
        Parameters
        ----------
        data_type : Optional[DataType], default=None
                The data type that the considered images should have to be counted, or ``None`` to count all images

        Returns
        -------
        The images count of this session, eventually only considering images that have a given data type.
        """
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
            raise BIDSException(
                f"BIDS session folder {session_path} can't be written as it already exists"
            )
        except FileNotFoundError:
            raise BIDSException(
                f"BIDS session folder {session_path} can't be written as one of its parent folders is missing"
            )

    def _add_image(
        self,
        data_type: DataType,
        nifti_extension: FileExtension,
        entities: Entities,
        suffix: Optional[Suffix],
        scan_info: Optional[ImageScanInfo],
    ) -> Image:
        if not nifti_extension.is_nifti():
            raise BIDSException(
                f"provided non-NIFTI file extension {nifti_extension} when adding image to session"
            )

        image = Image(
            parent_session=self,
            data_type=data_type,
            nifti_extension=nifti_extension,
            entities=entities,
            suffix=suffix,
            scan_info=ImageScanInfo({}) if scan_info is None else scan_info,
        )

        if data_type not in self._images:
            self._images[data_type] = []

        self._images[data_type].append(image)

        return image

    def write_images(self) -> ImagesWriter:
        """
        Start the images writing process for this session. This must happen after calling :py:meth:`BIDSDataset.write_to_folder`.

        See also
        --------
        * :py:class:`ImagesWriter`
        """
        return ImagesWriter(session=self)

    @cached_property
    def _scans_tsv_file_name(self) -> str:
        return f"{self.parent_subject.id}_{self.id}_scans.tsv"

    def populate_image_scans_info_from_df(self, scans_tsv_df: DataFrame):
        """
        Populates the images informations from the given dataframe.
        The dataframe must have a ``filename`` column which corresponds to
        the relative path of the image file relative to its parent session/this session,
        e.g. ``<data type>/sub-..._ses-..._<.....>.nii.gz``. The corresponding
        Image must already be present in this session. The other columns
        will be used as informations for the image at hand: they will not be
        merged with the existing ones, instead they'll be replaced entirely.

        Warnings
        --------
        You should only ever use this function if it is more convenient enough
        for your use case when you are writing a new BIDS dataset. Filling-in
        the information directly from :py:meth:`ImagesWriter.write_image` should be favored.
        """
        if "filename" not in scans_tsv_df.columns:
            raise BIDSException(f"dataframe did not have required filename column")

        sub_ses_prefix = f"{self.parent_subject.id}_{self.id}_"

        infos: list[dict[str, Any]] = scans_tsv_df.to_dict(orient="records")  # type: ignore
        for info in infos:
            image_filename = info.pop("filename", None)
            if image_filename is None:
                continue
            try:
                data_type, image_basename = str(image_filename).split(
                    sep="/", maxsplit=1
                )
            except ValueError:
                raise BIDSException(
                    f"expected image/scan filename of format <data_type>/<...> for {image_filename} in dataframe"
                )

            try:
                data_type = DataType(data_type)
            except ValueError:
                raise BIDSException(
                    f"expected valid data type as first folder of filename {image_filename} in dataframe"
                )

            if not image_basename.startswith(sub_ses_prefix):
                raise BIDSException(
                    f"expected image basename {image_basename} of filename {image_filename} in dataframe to have prefix {sub_ses_prefix}"
                )

            after_sub_ses = image_basename.removeprefix(sub_ses_prefix)
            try:
                filename_components = Image._parse_filename_components(after_sub_ses)
            except BIDSException as e:
                raise BIDSException(
                    f"found invalid image filename {image_filename} in dataframe: {e}"
                )

            if filename_components is None:
                raise BIDSException(
                    f"found image filename {image_filename} in dataframe without any file extension"
                )
            entities, suffix, extension = filename_components

            if not extension.is_nifti():
                continue

            image = None
            for img_by_data_type in self.images_by_data_type(data_type):
                if (
                    img_by_data_type.nifti_extension == extension
                    and img_by_data_type.entities == entities
                    and img_by_data_type.suffix == suffix
                ):
                    image = img_by_data_type
                    break

            if image is None:
                raise BIDSException(
                    f"could not find image for filename {image_filename} in dataframe"
                )

            image.scan_info = ImageScanInfo(
                other_fields={} if all(v is None for v in info) else info
            )

    # read the session's _scans.tsv and fill out scan info for all images
    def _populate_image_scans_info_from_tsv(self):
        scans_tsv_path = self._get_full_path() / self._scans_tsv_file_name
        if not os.path.exists(scans_tsv_path):
            return

        scans_tsv_df = _read_tsv_as_df(scans_tsv_path)
        try:
            self.populate_image_scans_info_from_df(scans_tsv_df)
        except BIDSException as e:
            raise BIDSException(
                f"could not populate images scans info from TSV file {scans_tsv_path}: {e}"
            )

    def _populate_images_from_folder(self, *, image_scans_info: bool) -> list[str]:
        unhandled_entries: list[str] = []

        # Populate the session's images, per-datatype
        for child in os.scandir(self._get_full_path()):
            if child.name == self._scans_tsv_file_name:
                continue

            try:
                data_type = DataType(child.name)
            except:
                unhandled_entries.append(child.path)
                continue

            if not child.is_dir():
                raise BIDSException(
                    f"Found data type entry {data_type} that was not a directory"
                )

            for child_image in os.scandir(child.path):
                sub_ses_prefix = f"{self.parent_subject.id}_{self.id}_"
                if not child_image.name.startswith(sub_ses_prefix):
                    raise BIDSException(
                        f"expected {data_type}/{child_image.name} "\
						f"filename to start with {sub_ses_prefix} due to its placement in the BIDS directory hierarchy"
                    )
                
                after_sub_ses = child_image.name.removeprefix(sub_ses_prefix)

                try:
                    filename_components = Image._parse_filename_components(
                        after_sub_ses
                    )
                except BIDSException as e:
                    raise BIDSException(
                        f"Found invalid image filename {child_image.name} in folder {data_type}: {e}"
                    )

                # For now we just exclude any file without a file extension, without raising
                # an error.
                if filename_components is None:
                    unhandled_entries.append(child_image.path)
                    continue
                entities, suffix, extension = filename_components

                # All the usual filename validation is done for non-NIFTI files, so that
                # we do not end up in a situation where the companion files (.json, etc.)
                # are inaccessible due to invalid naming. We do not store those companion
                # files however: we just validate the paths, but only actually accessing
                # such companion files by their paths will tell whether a particular one exists.
                if not extension.is_nifti():
                    continue

                self._add_image(
                    data_type=data_type,
                    nifti_extension=extension,
                    entities=entities,
                    suffix=suffix,
                    scan_info=None,
                )

        if image_scans_info:
            self._populate_image_scans_info_from_tsv()

        return unhandled_entries


@dataclass
class Image:
    parent_session: Session = field(repr=False, compare=False)
    data_type: DataType

    nifti_extension: FileExtension
    entities: Entities
    scan_info: ImageScanInfo
    suffix: Optional[Suffix] = None

    @cached_property
    def json_sidecar(self) -> dict[str, Any]:
        import json

        sidecar_path = self.get_image_companion_file_path(FileExtension.JSON)
        with open(sidecar_path, mode="r") as f:
            json_dict = json.load(f)
            if not isinstance(json_dict, dict):
                raise BIDSException(
                    f"expected JSON sidecar {sidecar_path} to contain an object as root node"
                )

        return json_dict

    @staticmethod
    def _parse_filename_components(
        filename_after_sub_ses: str,
    ) -> Optional[tuple[Entities, Optional[Suffix], FileExtension]]:
        """
        A given BIDS image filename is of the form ``sub-<label_ses-<label>_<rest>``,
        where ``<rest>`` is ``<entities>[_<suffix>].<extension>``.
        This function's role is to parse the ``<rest>`` part into its components.
        It returns ``None`` if there is no file extension, or a :py:class:`~clinicaio.types.BIDSException` if
        the passed string is invalid.
        """
        try:
            [before_ext, file_ext] = filename_after_sub_ses.split(".", maxsplit=1)
        except ValueError:
            # no "." in string so can't decompose list in assignment
            return None

        entities_and_suffix = before_ext
        if len(entities_and_suffix) == 0:
            raise BIDSException(
                f"found image filename {filename_after_sub_ses} without any entity or suffix"
            )

        try:
            extension = FileExtension(file_ext)
        except ValueError:
            # If this happens for legitimate files, you may need to add the file extension to the enumeration
            raise BIDSException(
                f"Found unknown file extension {file_ext} for filename {filename_after_sub_ses}"
            )

        entities = entities_and_suffix.split("_")
        suffix = None
        if "-" not in entities[-1]:
            try:
                suffix = Suffix(entities[-1])
            except BIDSException as e:
                raise BIDSException(
                    f"found invalid suffix label for image filename {filename_after_sub_ses}: {e}"
                )

            entities = entities[:-1]

        try:
            entities = Entities.from_str_list(entities)
        except BIDSException as e:
            raise BIDSException(
                f"found invalid entities for image filename {filename_after_sub_ses}: {e}"
            )
    
        return (entities, suffix, extension)

    def _get_image_base_full_path(
        self,
    ) -> Path:
        ses_id = self.parent_session.id
        sub_id = self.parent_session.parent_subject.id
        entities = "" if len(self.entities) == 0 else f"_{self.entities}"
        suffix = "" if self.suffix is None else f"_{self.suffix}"

        return (
            self.parent_session._get_full_path()
            / f"{self.data_type}/{sub_id}_{ses_id}{entities}{suffix}"
        )

    def get_nifti_image_path(self) -> Path:
        """Returns the full path to this image's NIFTI file"""
        return self.get_image_companion_file_path(self.nifti_extension)

    def get_image_companion_file_path(self, extension: FileExtension) -> Path:
        """
        BIDS is a format centered around organizing NIFTI image files, but NIFTI does not include
        all the information that one might want from a brain image or its acquisition process
        (equipment parameters, etc.). As such each NIFTI image file has zero or more "companion" files
        (or "sidecar" in BIDS-parlance for the JSON ones) that have the same file name as the main NIFTI
        ones apart from their file extension.

        This method returns the path of such an image's companion file given its file extension.

        .. code-block::

                sub-OAS30542
                └── ses-M126
                    └── dwi
                        ├── sub-OAS30542_ses-M126_run-01_dwi.bval
                        ├── sub-OAS30542_ses-M126_run-01_dwi.bvec
                        ├── sub-OAS30542_ses-M126_run-01_dwi.json
                        └── sub-OAS30542_ses-M126_run-01_dwi.nii.gz

        """
        return self._get_image_base_full_path().with_suffix(f".{extension}")
