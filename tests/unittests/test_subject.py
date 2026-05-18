from pathlib import Path
from re import escape
from typing import Iterable

import pytest
from _utils import _make_tsv, _setup_dataset_description
from pyfakefs.fake_filesystem import FakeFilesystem

from clinicaio.dataset import BIDSDataset
from clinicaio.session import SessionInfo
from clinicaio.types import BIDSException


# Rename the pyfakefs fixture so it's clearer what it actually is
@pytest.fixture
def fakefs(fs):
    yield fs


@pytest.fixture
def bids_path():
    return Path("/tmp/bids_test")


def test_add_session(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test")

    dataset = BIDSDataset(bids_path, _setup_dataset_description(fakefs, bids_path))
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
    bids_path = Path("/tmp/bids_test")

    dataset = BIDSDataset(bids_path, _setup_dataset_description(fakefs, bids_path))
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
    bids_path = Path("/tmp/bids_test")

    dataset = BIDSDataset(bids_path, _setup_dataset_description(fakefs, bids_path))
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
    bids_path = Path("/tmp/bids_test")

    dataset = BIDSDataset(bids_path, _setup_dataset_description(fakefs, bids_path))
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
    bids_path = Path("/tmp/bids_test")

    dataset = BIDSDataset(bids_path, _setup_dataset_description(fakefs, bids_path))
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

    assert len(session.info.all_fields()) == 3
    assert sorted(session.info.all_fields().items()) == [
        ("a", "bbb"),
        ("acq_time", "ACQT"),
        ("c", "eee"),
    ]
