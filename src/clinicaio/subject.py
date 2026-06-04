"""A subject that is part of a BIDS dataset."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Optional

from pandas import DataFrame
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticError
from typing_extensions import TypedDict

from ._tsv_utils import _read_tsv_as_df, _write_rows_to_tsv
from .session import Session, SessionInfo
from .types import BIDSException, SessionId, SubjectId

if TYPE_CHECKING:
    from .dataset import BIDSDataset
    from .image import Image


# populated from sub-* folders
@dataclass
class Subject:
    parent_dataset: BIDSDataset = field(repr=False, compare=False)

    id: SubjectId
    # https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#participants-file
    # from participants.tsv, matched by participant_id, if available (all Optional[Type] = None, if line missing or n/a value)
    info: SubjectInfo
    """Non-empty only if enabled when reading the dataset with :py:meth:`BIDSDataset.populate_from_dir() <clinicaio.dataset.BIDSDataset.populate_from_dir>`."""

    _sessions: Session | dict[SessionId, Session] = field(default_factory=lambda: {})

    def _get_full_path(self) -> Path:
        return self.parent_dataset._get_subjects_path() / f"{self.id}"

    def add_session(self, id: SessionId, info: Optional[SessionInfo] = None) -> Session:
        """
        Adds a new session to this subject.

        Raises
        ------
        AssertionError
            if this subject only has an implicit session. This may only happens if the dataset was populated from the filesystem.
        BIDSException
            if the session ID is invalid or this ID is already used by another session for this particular subject.
        """

        assert not isinstance(self._sessions, Session), (
            "Adding a named/ID-ed session to a subject that only has an implicit one (sub-<label>/<data_type>/... instead of sub-<label>/ses-<label>/<data type>) is not supported"
        )

        try:
            TypeAdapter(SessionId).validate_python(id)
        except PydanticError as e:
            raise BIDSException._from_pydantic("invalid session ID", e)

        if id in self._sessions:
            raise ValueError(
                f"tried to add session of ID {id} but it already exists within this subject"
            )

        session = Session(
            parent_subject=self,
            id=id,
            info=TypeAdapter(SessionInfo).validate_python({}) if info is None else info,
        )
        self._sessions[id] = session

        return session

    def all_sessions(self) -> Iterable[Session]:
        """
        Retrieves all the sessions that this subject is part of.
        """

        if isinstance(self._sessions, Session):
            return [self._sessions]
        else:
            return self._sessions.values()

    def sessions_count(self) -> int:
        """
        Retrieves the number of sessions that this subject is part of.
        """

        if isinstance(self._sessions, Session):
            return 1
        else:
            return len(self._sessions)

    def session_by_id(self, id: SessionId) -> Optional[Session]:
        """
        Get this subject's session with the given ID. It is a programmer error to call this method
        if this subject only has an implicit session without an ID.
        """

        assert not isinstance(self._sessions, Session), (
            "can't get session by ID when this subject only has a single session without an ID"
        )

        try:
            TypeAdapter(SessionId).validate_python(id)
        except PydanticError as e:
            raise BIDSException._from_pydantic("invalid session ID", e)

        return self._sessions.get(id)

    def all_images(self) -> Iterable[Image]:
        """
        Retrieves all the images that are part of this subject's sessions.
        """
        for session in self.all_sessions():
            yield from session.all_images()

    @cached_property
    def _sessions_tsv_file_name(self) -> str:
        return f"{self.id}_sessions.tsv"

    def _write_to_folder(self) -> None:
        subject_path = self._get_full_path()
        os.makedirs(subject_path, exist_ok=True)

        for session in self.all_sessions():
            session._write_to_folder()

        if isinstance(self._sessions, dict):
            _write_rows_to_tsv(
                subject_path / self._sessions_tsv_file_name,
                first_column_name="session_id",
                rows=(
                    {"session_id": session.id} | session.info
                    for session in self.all_sessions()
                    if len(session.info) != 0
                ),
            )

    def populate_sessions_info_from_df(self, sessions_tsv_df: DataFrame) -> None:
        """
        Populates the sessions information from the given dataframe.
        The dataframe must have a ``session_id`` column which corresponds to
        a session's ID that's already present in this dataset's subject. The other columns
        will be used as information for the session at hand: they will not be
        merged with the information from the existing sessions, instead they'll be replaced entirely.

        Warnings
        --------
        You should only ever use this function if it is more convenient
        for your use case when you are writing a new BIDS dataset. Filling-in
        the information directly from :py:meth:`add_session` should be favored.

        Examples
        --------

        See :py:meth:`BIDSDataset.populate_subjects_info_from_df() <clinicaio.dataset.BIDSDataset.populate_subjects_info_from_df>`
        """

        assert not isinstance(self._sessions, Session), (
            "subject only has a single session without ID so populating session information makes no sense"
        )

        if "session_id" not in sessions_tsv_df.columns:
            raise ValueError(
                "the dataframe did not have the required 'session_id' column"
            )

        infos: list[dict[str, Any]] = sessions_tsv_df.to_dict(orient="records")  # type: ignore
        for info in infos:
            session_id = info.pop("session_id", None)
            if session_id is None:
                continue
            try:
                session_id = TypeAdapter(SessionId).validate_python(str(session_id))
            except PydanticError as e:
                raise BIDSException._from_pydantic(
                    f"invalid session ID {session_id} in dataframe", e
                )

            session = self.session_by_id(session_id)
            if session is None:
                continue
                # raise BIDSException(f"could not find session of ID {session_id} referenced by TSV file {sessions_tsv_path}")

            try:
                session.info = TypeAdapter(SessionInfo).validate_python(info)
            except PydanticError as e:
                raise BIDSException._from_pydantic(
                    f"invalid session info {info} in dataframe", e
                )

    def _populate_sessions_info_from_tsv(self) -> None:
        """Reads the subject's sessions.tsv and fills out info in all sessions"""
        sessions_tsv_path = self._get_full_path() / self._sessions_tsv_file_name
        if not os.path.exists(sessions_tsv_path):
            return

        sessions_tsv_df = _read_tsv_as_df(sessions_tsv_path)
        try:
            self.populate_sessions_info_from_df(sessions_tsv_df)
        except Exception as e:
            raise BIDSException(
                f"could not populate sessions info from TSV file {sessions_tsv_path}: {e}"
            ) from e

    def _populate_sessions_from_folder(
        self, *, sessions_info: bool, image_scans_info: bool
    ) -> set[str]:
        unhandled_entries: set[str] = set()

        # Populate subject's sessions
        for child in os.scandir(self._get_full_path()):
            # Handled after all sessions have been read, to fill out the session info from the TSV file
            if child.name == self._sessions_tsv_file_name:
                continue

            if not child.name.startswith("ses-"):
                unhandled_entries.add(child.path)
                continue

            if not child.is_dir():
                raise ValueError(
                    f"found ses- entry {child.name} that was not a directory"
                )

            try:
                session_id = TypeAdapter(SessionId).validate_python(child.name)
            except PydanticError as e:
                raise BIDSException._from_pydantic(
                    f"Found invalid session ID {child.name}", e
                )

            try:
                session = self.add_session(id=session_id)

                unhandled_entries |= session._populate_images_from_folder(
                    image_scans_info=image_scans_info
                )
            except Exception as e:
                raise ValueError(
                    f"got exception while adding session {session_id} and populating its images: {e}"
                ) from e

        # Handling of implicit sessions, e.g. sub-1/anat/... instead of sub-1/ses-A/anat/...
        assert isinstance(self._sessions, dict)
        if len(self._sessions) == 0:
            # The eventual unhandled entries that we may have at this point only
            # make sense in a context where we were expecting proper session folders.
            # Since that's not the case, reset the entries: it will be filled up
            # again with only the necessary ones that do not match any filename
            # valid *inside* a "session" folder (which here is implicit/at the same
            # level as the subject folder).
            unhandled_entries.clear()

            try:
                session = Session(
                    parent_subject=self,
                    id=None,
                    info=TypeAdapter(SessionInfo).validate_python({}),
                )
                unhandled_entries |= session._populate_images_from_folder(
                    image_scans_info=image_scans_info
                )
            except Exception as e:
                raise ValueError(
                    f"got exception while adding session without ID/dedicated folder and populating its images: {e}"
                ) from e

            if session.images_count() > 0:
                self._sessions = session
        else:
            if sessions_info:
                self._populate_sessions_info_from_tsv()

        return unhandled_entries


# Populated from participants.tsv from root of dataset
# FIXME: https://github.com/python/mypy/issues/18176
class SubjectInfo(TypedDict, extra_items=Any):  # type: ignore
    """
    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#participants-file>`__
    """
