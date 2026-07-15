"""The library's entry point into BIDS datasets."""

from __future__ import annotations

import os
from dataclasses import dataclass
from fnmatch import fnmatchcase
from functools import cached_property
from pathlib import Path
from typing import IO, Any, Callable, Iterable, Optional

from pandas import DataFrame
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticError

from clinicaio import dataset_description

from ._tsv_utils import _read_tsv_as_df, _write_rows_to_tsv
from .dataset_description import BIDSDatasetDescription
from .image import Image
from .image_query import ImageQuery
from .session import Session
from .subject import Subject, SubjectInfo
from .types import BIDSException, FileExtension, SubjectId


@dataclass
class BIDSDataset:
    """
    A BIDS dataset. See the :doc:`general organisation of the library <../index>`.

    Examples
    --------

    * :doc:`/examples/assorted_queries`    
    """

    _subjects: dict[SubjectId, Subject]
    bids_path: Path
    description: BIDSDatasetDescription

    def __init__(self, bids_path: Path, description: BIDSDatasetDescription):
        """
        Creates a new BIDS dataset. Useful when you want to write a new dataset to the filesystem.

        See also
        --------
        * :py:meth:`write_to_folder()`
        """
        self.bids_path = bids_path
        self.description = description
        self._subjects = {}

    def subject_by_id(self, id: SubjectId) -> Optional[Subject]:
        """
        Retrieves from this dataset the given subject by its ID.
        """

        try:
            TypeAdapter(SubjectId).validate_python(id)
        except PydanticError as e:
            raise BIDSException._from_pydantic(f"invalid subject ID {id}", e)

        return self._subjects.get(id)

    def all_subjects(self) -> Iterable[Subject]:
        """
        Retrieves all the subjects that are part of this dataset.
        """

        return self._subjects.values()

    def subjects_count(self) -> int:
        """
        Retrieves the number of subjects that are part of this dataset.
        """

        return len(self._subjects)

    def all_sessions(self) -> Iterable[Session]:
        """
        Retrieves all the sessions that this dataset's subjects are part of.
        """

        for subject in self.all_subjects():
            yield from subject.all_sessions()

    def all_images(self) -> Iterable[Image]:
        """
        Retrieves all the images present in this dataset.
        """

        for session in self.all_sessions():
            yield from session.all_images()

    def _get_full_path(self) -> Path:
        return self.bids_path

    @cached_property
    def _participants_tsv_file_name(self) -> str:
        return "participants.tsv"

    def populate_subjects_info_from_df(self, participants_tsv_df: DataFrame) -> None:
        """
        Populates the subjects information from the given dataframe.
        The dataframe must have a ``participant_id`` column which corresponds to
        a subject's ID that's already present in this dataset. The other columns
        will be used as information for the subject at hand: they will not be
        merged with the information from the existing subjects, instead they'll be replaced entirely.

        Warnings
        --------
        You should only ever use this function if it is more convenient
        for your use case when you are writing a new BIDS dataset. Filling-in
        the information directly from :py:meth:`add_subject` should be favored.
        """

        if "participant_id" not in participants_tsv_df.columns:
            raise BIDSException(
                "the dataframe did not have the required 'participant_id' column"
            )

        infos: list[dict[str, Any]] = participants_tsv_df.to_dict(orient="records")  # type: ignore
        for info in infos:
            subject_id = info.pop("participant_id", None)
            if subject_id is None:
                continue

            try:
                subject_id = TypeAdapter(SubjectId).validate_python(str(subject_id))
            except PydanticError as e:
                raise BIDSException._from_pydantic(
                    f"found invalid subject ID {subject_id} in dataframe", e
                )

            subject = self.subject_by_id(subject_id)
            if subject is None:
                continue
                # raise BIDSException(f"could not find subject of ID {subject_id} referenced by TSV file {participants_tsv_path}")

            subject.info = SubjectInfo.from_fields(info)

    def _populate_subjects_info_from_tsv(self) -> None:
        participants_tsv_path = self._get_full_path() / self._participants_tsv_file_name
        if not os.path.exists(participants_tsv_path):
            return

        participants_tsv_df = _read_tsv_as_df(participants_tsv_path)
        try:
            self.populate_subjects_info_from_df(participants_tsv_df)
        except BIDSException as e:
            raise BIDSException(
                f"could not populate subjects info from TSV file {participants_tsv_path}: {e}"
            ) from e

    @classmethod
    def populate_from_dir(
        cls,
        bids_dir: str | Path,
        *,
        subjects_info: bool,
        sessions_info: bool,
        image_scans_info: bool,
        report_unhandled_entries: Optional[Callable[[list[str]], None]] = None,
    ) -> BIDSDataset:
        """
        Read a BIDS dataset from the given BIDS directory.

        Parsing the various information for subjects/sessions/images can be toggled,
        as these take the bulk of the loading time in most cases, so it's better to
        avoid reading them if you do not have a use for them. This is due to the information
        being stored in tabular/TSV files instead of per-subject/session/image JSON file.

        Parameters
        ----------
        bids_dir :
                The directory where the BIDS dataset exists
        subjects_info :
                Whether to fill out :py:class:`subject information <clinicaio.subject.SubjectInfo>` from the ``participants.tsv`` file
        sessions_info :
                Whether to fill out :py:class:`session information <clinicaio.session.SessionInfo>` from the ``*_sessions.tsv`` files
        image_scans_info :
                Whether to fill out :py:class:`image scan information <clinicaio.image.ImageScanInfo>` from the ``*_scans.tsv`` files
        report_unhandled_entries :
                A function that will be called with the list of relative paths to files and directories that were
                ignored/not handled while populating the dataset. This is mostly useful for debugging purpose when
                your dataset has some unconvential layout or extra BIDS derivatives files/folders.

        Raises
        ------
        BIDSException
                Whenever an invalid (per BIDS specification) filename/path is encountered while walking the BIDS directory
        """
        bids_dir = Path(bids_dir)

        unhandled_entries: set[str] = set()

        try:
            description = BIDSDatasetDescription._load_from_folder(bids_dir)
        except BIDSException as e:
            raise BIDSException(
                f"could not read BIDS description from JSON file: {e}"
            ) from e

        dataset = BIDSDataset(bids_path=bids_dir, description=description)

        # Populate subjects/subjects
        for bids_child in os.scandir(bids_dir):
            # Handled once all subjects have been read
            if bids_child.name == dataset._participants_tsv_file_name:
                continue

            # Already handled above
            if bids_child.name == dataset_description._JSON_FILENAME:
                continue

            if not bids_child.name.startswith("sub-"):
                unhandled_entries.add(bids_child.path)
                continue

            if not bids_child.is_dir():
                raise BIDSException(
                    f"found sub- entry {bids_child.name} that was not a directory"
                )

            try:
                subject_id = TypeAdapter(SubjectId).validate_python(bids_child.name)
            except PydanticError as e:
                raise BIDSException._from_pydantic(
                    f"Found invalid subject/subject ID {bids_child.name}", e
                )

            try:
                subject = dataset.add_subject(id=subject_id)

                unhandled_entries |= subject._populate_sessions_from_folder(
                    sessions_info=sessions_info, image_scans_info=image_scans_info
                )
            except Exception as e:
                raise BIDSException(
                    f"got exception while adding subject {subject_id} and populating its sessions: {e}"
                ) from e

        if subjects_info:
            dataset._populate_subjects_info_from_tsv()

        if report_unhandled_entries is not None:
            relative_unhandled_entries = [
                str(Path(entry).relative_to(bids_dir)) for entry in unhandled_entries
            ]
            report_unhandled_entries(relative_unhandled_entries)

        return dataset

    def add_subject(self, id: SubjectId, info: Optional[SubjectInfo] = None) -> Subject:
        """
        Adds a new subject to this dataset.

        Raises
        ------
        BIDSException
            if the subject ID is invalid or this ID is already used by another subject in this dataset
        """

        try:
            TypeAdapter(SubjectId).validate_python(id)
        except PydanticError as e:
            raise BIDSException._from_pydantic(f"invalid subject ID {id}", e)

        if id in self._subjects:
            raise BIDSException(
                f"tried to add subject of ID {id} but it already exists within this dataset"
            )

        subject = Subject(
            parent_dataset=self,
            id=id,
            info=SubjectInfo.from_fields({}) if info is None else info,
        )
        self._subjects[id] = subject

        return subject

    def write_to_folder(self, *, readme: str) -> None:
        """
        Creates the dataset folder, writes the dataset description JSON and readme, creates the subjects and sessions
        folders with their TSV files. Images must have already been added to the sessions with
        :py:meth:`Session.write_image() <clinicaio.session.Session.write_image>` before using this method,
        otherwise the image scans info will be missing.

        Parameters
        ----------
        readme
            The content of the README file that will be placed at the root of the dataset. See the `BIDS Specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/dataset-description.html#readme>`__

        See also
        --------
        * :py:meth:`write_root_file`
        * :py:meth:`Session.write_image() <clinicaio.session.Session.write_image>`
        """
        os.makedirs(self.bids_path, exist_ok=True)

        try:
            self.description._write_to_folder(self.bids_path)
        except Exception as e:
            raise BIDSException(
                f"can't write dataset description JSON to folder {self.bids_path}: {e}"
            ) from e

        for subject in self.all_subjects():
            subject._write_to_folder()

        _write_rows_to_tsv(
            tsv_path=self.bids_path / "participants.tsv",
            first_column_name="participant_id",
            rows=(
                subject.info.all_fields_with_id(subject)
                for subject in self.all_subjects()
                if not subject.info.is_empty()
            ),
        )

        with self.write_root_file("README", write_binary=False) as f:
            print(readme, file=f)

    def write_root_file(self, file_name: str, *, write_binary: bool = False) -> IO[Any]:
        """
        Creates and opens for writing the given file at the root of the dataset, eventually in "binary" mode
        (per Python's :py:func:`open`).

        Parameters
        ----------
        file_name :
                The name of the file to write. Must not contain a ``/``
        write_binary :
                Whether to open the created file in binary or text writing mode

        Raises
        ------
        ValueError
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
            raise ValueError(
                f"BIDSDataset.write_root_file() is not meant to write in sub-folders ({file_name})"
            )

        mode = "x" + ("b" if write_binary else "")
        try:
            return open(self.bids_path / file_name, mode)
        except FileExistsError:
            raise

    def query_images(self, query: ImageQuery) -> Iterable[Image]:
        """
        Returns all the images matching the query.
        See :py:class:`~clinicaio.image_query.ImageQuery` for details on the query itself.

        See also
        --------
        * :py:meth:`query_images_nifti_paths`
        * :py:meth:`query_images_companions_paths`

        Examples
        --------

        * :doc:`/examples/assorted_queries`
        """
        filtered_subjects = (
            self.all_subjects()
            if len(query.subjects) == 0 and len(query.sub_ses) == 0
            else (
                self.subject_by_id(id)
                for id in (query.subjects or query.sub_ses.keys())
            )
        )

        for subject in filtered_subjects:
            if subject is None:
                continue

            filtered_sessions = (
                subject.all_sessions()
                if len(query.sessions) == 0
                and len(query.sub_ses.get(subject.id, set())) == 0
                else (
                    subject.session_by_id(id)
                    for id in (query.sessions or query.sub_ses[subject.id])
                )
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
                    if query.suffix is not None:
                        if (image.suffix is None) or (
                            not fnmatchcase(image.suffix, query.suffix)
                        ):
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

        See also
        --------
        * :py:meth:`Image.get_nifti_image_path() <clinicaio.image.Image.get_nifti_image_path>`

        Examples
        --------

        * :doc:`/examples/assorted_queries`
        """
        return (image.get_nifti_image_path() for image in self.query_images(query))

    def query_images_companions_paths(
        self, query: ImageQuery, extension: FileExtension, *, skip_missing: bool = False
    ) -> Iterable[Path]:
        """
        Convenience function that only returns the companion image paths with the given file extension
        instead of the images themselves. Depending on ``skip_missing`` it may or may not skip the files
        that do not currently exist.

        Parameters
        ----------
        query
            The query that the images must match
        extension
            The wanted file extension for the image's companion file
        skip_missing
            Whether to not include file paths that do not currently exist

        Note
        ----
        This method does not guarantee whether a given path is skipped when the iteration reaches it,
        or when this method returns. This is due to the lazy nature of generators in Python.

        See also
        --------
        * :py:meth:`query_images`
        * :py:meth:`Image.get_image_companion_path() <clinicaio.image.Image.get_image_companion_path>`

        Examples
        --------

        * :doc:`/examples/assorted_queries`
        """
        return (
            path
            for image in self.query_images(query)
            if (path := image.get_image_companion_path(extension))
            and ((not skip_missing) or path.exists())
        )
