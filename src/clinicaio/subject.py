from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Optional

from pandas import DataFrame
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticError

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
    _sessions: Session | dict[SessionId, Session] = field(default_factory=lambda: {})

    def _get_full_path(self) -> Path:
        return self.parent_dataset._get_full_path() / f"{self.id}"

    def add_session(self, id: SessionId, info: Optional[SessionInfo]) -> Session:
        assert not isinstance(self._sessions, Session), (
            "Adding a named/ID-ed session to a subject that only has an implicit one (sub-<label>/<data_type>/... instead of sub-<label>/ses-<label>/<data type>) is not supported"
        )

        try:
            TypeAdapter(SessionId).validate_python(id)
        except PydanticError as e:
            raise BIDSException.from_pydantic("invalid session ID", e)

        if id in self._sessions:
            raise BIDSException(
                f"tried to add session of ID {id} but it already exists within this subject"
            )

        session = Session(
            parent_subject=self,
            id=id,
            info=SessionInfo.from_fields({}) if info is None else info,
        )
        self._sessions[id] = session

        return session

    def all_sessions(self) -> Iterable[Session]:
        if isinstance(self._sessions, Session):
            return [self._sessions]
        else:
            return self._sessions.values()

    def sessions_count(self) -> int:
        if isinstance(self._sessions, Session):
            return 1
        else:
            return len(self._sessions)

    def session_by_id(self, id: SessionId) -> Optional[Session]:
        assert not isinstance(self._sessions, Session), (
            "can't get session by ID when this subject only has a single session without an ID"
        )

        try:
            TypeAdapter(SessionId).validate_python(id)
        except PydanticError as e:
            raise BIDSException.from_pydantic("invalid session ID", e)

        return self._sessions.get(id)

    def all_images(self) -> Iterable[Image]:
        for session in self.all_sessions():
            yield from session.all_images()

    @cached_property
    def _sessions_tsv_file_name(self) -> str:
        return f"{self.id}_sessions.tsv"

    def _write_to_folder(self):
        subject_path = self._get_full_path()
        os.makedirs(subject_path, exist_ok=True)

        for session in self.all_sessions():
            session._write_to_folder()

        if isinstance(self._sessions, dict):
            _write_rows_to_tsv(
                subject_path / self._sessions_tsv_file_name,
                first_column_name="session_id",
                rows=(
                    session.info.all_fields_with_id(session)
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

        assert not isinstance(self._sessions, Session), (
            "subject only has a single session without ID so populating session information makes no sense"
        )

        if "session_id" not in sessions_tsv_df.columns:
            raise BIDSException(f"dataframe did not have required session_id column")

        infos: list[dict[str, Any]] = sessions_tsv_df.to_dict(orient="records")  # type: ignore
        for info in infos:
            session_id = info.pop("session_id", None)
            if session_id is None:
                continue
            try:
                session_id = TypeAdapter(SessionId).validate_python(str(session_id))
            except PydanticError as e:
                raise BIDSException.from_pydantic(
                    f"invalid session ID {session_id} in dataframe", e
                )

            session = self.session_by_id(session_id)
            if session is None:
                continue
                # raise BIDSException(f"could not find session of ID {session_id} referenced by TSV file {sessions_tsv_path}")

            session.info = SessionInfo.from_fields(info)

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
                session_id = TypeAdapter(SessionId).validate_python(child.name)
            except PydanticError as e:
                raise BIDSException.from_pydantic(
                    f"Found invalid session ID {child.name}", e
                )

            try:
                session = self.add_session(id=session_id, info=None)

                session._populate_images_from_folder(image_scans_info=image_scans_info)
            except Exception as e:
                raise BIDSException(
                    f"got exception while adding session {session_id} and populating its images: {e}"
                )

        assert isinstance(self._sessions, dict)
        if len(self._sessions) == 0:
            try:
                session = Session(
                    parent_subject=self,
                    id=None,
                    info=SessionInfo.from_fields({}),
                )
                session._populate_images_from_folder(image_scans_info=image_scans_info)
            except Exception as e:
                raise BIDSException(
                    f"got exception while adding session without ID/dedicated folder and populating its images: {e}"
                )

            if session.images_count() > 0:
                self._sessions = session
        else:
            if sessions_info:
                self._populate_sessions_info_from_tsv()

        return unhandled_entries


# Populated from participants.tsv from root of dataset
@dataclass(init=False)
class SubjectInfo:
    """
    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#participants-file>`__
    """

    # FIXME: proper typing for the fields that BIDS defines?
    # age, handedness, etc.
    _other_fields: dict[str, Any]

    def __init__(self, *, other_fields: dict[str, Any]):
        if "participant_id" in other_fields:
            raise BIDSException("found unexpected participant_id field in subject info")

        self._other_fields = other_fields

    @classmethod
    def from_fields(cls, fields: dict[str, Any]) -> SubjectInfo:
        return SubjectInfo(
            other_fields={} if all(v is None for v in fields.values()) else fields,
        )

    def all_fields(self) -> dict[str, Any]:
        return self._other_fields

    def all_fields_with_id(self, subject: Subject) -> dict[str, Any]:
        return self.all_fields() | {"participant_id": subject.id}

    def is_empty(self) -> bool:
        return len(self._other_fields) == 0
