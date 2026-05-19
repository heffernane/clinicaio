from pathlib import Path
from re import escape
from typing import Iterable

import pytest
from _utils import _get_dataset_description, _make_tsv, _setup_dataset_description
from pandas import DataFrame
from pyfakefs.fake_filesystem import FakeFilesystem

from clinicaio.dataset import BIDSDataset
from clinicaio.session import SessionInfo
from clinicaio.subject import SubjectInfo
from clinicaio.types import BIDSException


# Rename the pyfakefs fixture so it's clearer what it actually is
@pytest.fixture
def fakefs(fs):
    yield fs


@pytest.fixture
def bids_path():
    return Path("/tmp/bids_test")


def test_add_session(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()
    assert list(subject.all_sessions()) == []
    assert subject.sessions_count() == 0

    session = subject.add_session("ses-A", None)
    assert session.id == "ses-A"
    assert session.parent_subject is subject
    assert session.images_count() == 0
    assert list(session.all_images()) == []

    assert subject.sessions_count() == 1
    assert list(subject.all_sessions())[0] is session

    assert subject.session_by_id(session.id) is session
    assert subject.session_by_id("ses-A") is session


def test_add_session_invalid_id(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()

    with pytest.raises(
        BIDSException,
        match=escape(
            "invalid session ID: String should match pattern '^ses-[a-zA-Z0-9]+$'"
        ),
    ):
        subject.add_session("sess-A", None)


def test_add_session_already_existing_id(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()

    session = subject.add_session("ses-A", None)
    assert session.id == "ses-A"
    assert session.parent_subject is subject
    assert session.images_count() == 0
    assert list(session.all_images()) == []

    with pytest.raises(
        BIDSException,
        match=escape(
            "tried to add session of ID ses-A but it already exists within this subject"
        ),
    ):
        subject.add_session("ses-A", None)


def test_add_session_none_info(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()

    session = subject.add_session("ses-A", None)
    assert session.id == "ses-A"
    assert session.parent_subject is subject
    assert session.images_count() == 0
    assert list(session.all_images()) == []

    assert session.info.is_empty()
    assert len(session.info.all_fields()) == 0


def test_add_session_provided_info(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()

    session = subject.add_session(
        "ses-A",
        SessionInfo(
            acquisition_time="ACQT",
            pathology=None,
            other_fields={"a": "bbb", "c": "eee"},
        ),
    )
    assert session.id == "ses-A"
    assert session.parent_subject is subject
    assert session.images_count() == 0
    assert list(session.all_images()) == []

    assert subject.session_by_id(session.id) is session
    assert len(list(subject.all_sessions())) == 1
    assert subject.sessions_count() == 1
    assert list(subject.all_sessions())[0] is session

    assert len(session.info.all_fields()) == 3
    assert sorted(session.info.all_fields().items()) == [
        ("a", "bbb"),
        ("acq_time", "ACQT"),
        ("c", "eee"),
    ]


def test_get_full_path(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()

    assert subject._get_full_path() == Path("/does/not/exist/sub-001")


def test_session_by_id_invalid_id(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()

    with pytest.raises(
        BIDSException,
        match=escape(
            "invalid session ID: String should match pattern '^ses-[a-zA-Z0-9]+$'"
        ),
    ):
        # note: sub-* instead of ses-*, so invalid as a session ID
        subject.session_by_id("sub-001")


def test_session_by_id_missing_session(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)

    assert subject.session_by_id("ses-001") is None
    ses001 = subject.add_session("ses-001", None)
    ses002 = subject.add_session("ses-002", None)
    # Although not recommended it is possible to have two session with such similar
    # IDs, considering that it's ses-<label> where label is composed of any arrangement
    # of ASCII letters and digits.
    ses01 = subject.add_session("ses-01", None)
    assert subject.session_by_id("ses-001") is ses001
    assert subject.session_by_id("ses-002") is ses002
    assert subject.session_by_id("ses-01") is ses01
    assert ses001 is not ses01
    assert subject.session_by_id("ses-1") is None


def test_subject_info(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)

    info1 = SubjectInfo(other_fields={})
    assert info1.is_empty()
    assert info1.all_fields() == {}
    assert info1.all_fields_with_id(subject) == {"participant_id": "sub-001"}

    info2 = SubjectInfo(other_fields={"a": "12456abc"})
    assert not info2.is_empty()
    assert info2.all_fields() == {"a": "12456abc"}
    assert info2.all_fields_with_id(subject) == {
        "participant_id": "sub-001",
        "a": "12456abc",
    }

    info3 = SubjectInfo.from_fields({"aa": 3, "bbb": "foo", "c": None})
    assert not info3.is_empty()
    assert info3.all_fields() == {"aa": 3, "bbb": "foo", "c": None}
    # note: dict ordering does not matter for equality
    assert info3.all_fields_with_id(subject) == {
        "participant_id": "sub-001",
        "aa": 3,
        "bbb": "foo",
        "c": None,
    }


def test_subject_info_invalid_session_id_field():
    with pytest.raises(
        BIDSException, match="found unexpected participant_id field in subject info"
    ):
        SubjectInfo.from_fields({"participant_id": "sub-001", "a": "345"})

    with pytest.raises(
        BIDSException, match="found unexpected participant_id field in subject info"
    ):
        SubjectInfo(other_fields={"participant_id": "sub-001", "a": "345"})


def test_populate_sessions_info_from_df_missing_id_column(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)

    with pytest.raises(
        BIDSException, match="dataframe did not have required session_id column"
    ):
        df = DataFrame(
            [
                {"aa": 3, "bb": "38793foo", "ccc": None},
            ]
        )
        subject.populate_sessions_info_from_df(df)


def test_populate_sessions_info_from_df_none_id_field(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)
    session = subject.add_session("ses-001", None)
    assert session.parent_subject is subject
    assert session.info.is_empty()

    df = DataFrame(
        [
            # note the None (n/a) ID column.
            {"session_id": None, "aa": 3, "bb": "38793foo", "ccc": None},
            {"session_id": "ses-001", "aa": 3, "bb": "38793foo", "ccc": None},
            {"session_id": None, "aa": 3, "bb": "38793foo", "ccc": None},
        ]
    )
    subject.populate_sessions_info_from_df(df)

    assert not session.info.is_empty()
    assert session.info.all_fields() == {"aa": 3, "bb": "38793foo", "ccc": None}
    assert subject.sessions_count() == 1
    assert list(subject.all_sessions()) == [session]


def test_populate_sessions_info_from_df_invalid_id(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)
    session = subject.add_session("ses-001", None)
    assert session.parent_subject is subject
    assert session.info.is_empty()

    df = DataFrame(
        [
            # note: sub-* instead of ses-*
            {"session_id": "sub-001", "aa": 3, "bb": "38793foo", "ccc": None},
        ]
    )
    with pytest.raises(BIDSException, match="invalid session ID sub-001 in dataframe"):
        subject.populate_sessions_info_from_df(df)


def test_populate_sessions_info_from_df_valid_id_missing_session(
    fakefs: FakeFilesystem,
):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)
    session = subject.add_session("ses-001", None)
    assert session.parent_subject is subject
    assert session.info.is_empty()

    df = DataFrame(
        [
            # note: This session ID is valid but no session has this ID for this subject.
            {"session_id": "ses-002", "aa": 3, "bb": "38793foo", "ccc": None},
        ]
    )
    subject.populate_sessions_info_from_df(df)

    assert session.info.is_empty()
