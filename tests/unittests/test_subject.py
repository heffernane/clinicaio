from pathlib import Path
from re import escape

import pytest
from _utils import _get_dataset_description, _make_tsv, _setup_dataset_description
from pandas import DataFrame
from pyfakefs.fake_filesystem import FakeFilesystem

from clinicaio.dataset import BIDSDataset
from clinicaio.entities import Entities
from clinicaio.session import SessionInfo
from clinicaio.subject import SubjectInfo
from clinicaio.types import BIDSException, DataType, FileExtension


# Rename the pyfakefs fixture so it's clearer what it actually is
@pytest.fixture
def fakefs(fs):
    yield fs


def test_add_session(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001")

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()
    assert list(subject.all_sessions()) == []
    assert subject.sessions_count() == 0

    session = subject.add_session("ses-A")
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
    subject = dataset.add_subject("sub-001")

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()

    with pytest.raises(
        BIDSException,
        match=escape(
            "invalid session ID: String should match pattern '^ses-[a-zA-Z0-9]+$'"
        ),
    ):
        subject.add_session("sess-A")


def test_add_session_already_existing_id(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001")

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()

    session = subject.add_session("ses-A")
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
        subject.add_session("ses-A")


def test_add_session_none_info(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001")

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()

    session = subject.add_session("ses-A")
    assert session.id == "ses-A"
    assert session.parent_subject is subject
    assert session.images_count() == 0
    assert list(session.all_images()) == []

    assert session.info.is_empty()
    assert len(session.info.all_fields()) == 0


def test_add_session_none_info_implicit(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001")

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()

    # NOTE: the info is not passed explicitely
    session = subject.add_session("ses-A")
    assert session.id == "ses-A"
    assert session.parent_subject is subject
    assert session.images_count() == 0
    assert list(session.all_images()) == []

    assert session.info.is_empty()
    assert len(session.info.all_fields()) == 0


def test_add_session_provided_info(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001")

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
    subject = dataset.add_subject("sub-001")

    assert subject.parent_dataset is dataset
    assert subject.id == "sub-001"
    assert subject.info.is_empty()

    assert subject._get_full_path() == Path("/does/not/exist/sub-001")


def test_session_by_id_invalid_id(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001")

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
    subject = dataset.add_subject("sub-001")

    assert subject.session_by_id("ses-001") is None
    ses001 = subject.add_session("ses-001")
    ses002 = subject.add_session("ses-002")
    # Although not recommended it is possible to have two session with such similar
    # IDs, considering that it's ses-<label> where label is composed of any arrangement
    # of ASCII letters and digits.
    ses01 = subject.add_session("ses-01")
    assert subject.session_by_id("ses-001") is ses001
    assert subject.session_by_id("ses-002") is ses002
    assert subject.session_by_id("ses-01") is ses01
    assert ses001 is not ses01
    assert subject.session_by_id("ses-1") is None


def test_subject_info(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001")

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
    subject = dataset.add_subject("sub-001")

    with pytest.raises(
        BIDSException,
        match="the dataframe did not have the required 'session_id' column",
    ):
        df = DataFrame(
            [
                {"aa": 3, "bb": "38793foo", "ccc": None},
            ]
        )
        subject.populate_sessions_info_from_df(df)


def test_populate_sessions_info_from_df_none_id_field(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-001")
    session = subject.add_session("ses-001")
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
    subject = dataset.add_subject("sub-001")
    session = subject.add_session("ses-001")
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
    subject = dataset.add_subject("sub-001")
    session = subject.add_session("ses-001")
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


def test_implicit_session(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test")

    _setup_dataset_description(fakefs, bids_path)

    fakefs.create_file(bids_path / "sub-1/anat/sub-1_sfx.nii.gz")
    fakefs.create_file(bids_path / "sub-1/anat/sub-1_task-rest.nii.gz")
    fakefs.create_file(bids_path / "sub-1/pet/sub-1_task-rest_sfx2.nii")
    fakefs.create_file(
        bids_path / "sub-1/sub-1_scans.tsv",
        contents=_make_tsv(
            [
                ["filename", "a", "bcd"],
                ["anat/sub-1_sfx.nii.gz", "1", "n/a"],
                ["anat/sub-1_task-rest.nii.gz", "2", "3"],
                ["pet/sub-1_task-rest_sfx2.nii", "n/a", "4"],
            ]
        ),
    )

    fakefs.create_file(bids_path / "sub-2/ses-A/anat/sub-2_ses-A_sfx.nii.gz")
    fakefs.create_file(bids_path / "sub-2/ses-A/anat/sub-2_ses-A_task-rest.nii.gz")
    fakefs.create_file(bids_path / "sub-2/ses-A/pet/sub-2_ses-A_task-rest_sfx2.nii")
    fakefs.create_file(
        bids_path / "sub-2/ses-A/sub-2_ses-A_scans.tsv",
        contents=_make_tsv(
            [
                ["filename", "a", "bcd"],
                ["anat/sub-2_ses-A_sfx.nii.gz", "1", "n/a"],
                ["anat/sub-2_ses-A_task-rest.nii.gz", "2", "3"],
                ["pet/sub-2_ses-A_task-rest_sfx2.nii", "n/a", "4"],
            ]
        ),
    )

    dataset = BIDSDataset.populate_from_dir(
        bids_path, subjects_info=True, sessions_info=True, image_scans_info=True
    )
    assert dataset.subjects_count() == 2

    # Implicit session without ID
    sub1 = dataset.subject_by_id("sub-1")
    assert sub1 is not None
    assert sub1.sessions_count() == 1
    with pytest.raises(
        AssertionError,
        match=escape(
            "Adding a named/ID-ed session to a subject that only has an implicit one (sub-<label>/<data_type>/... instead of sub-<label>/ses-<label>/<data type>) is not supported"
        ),
    ):
        sub1.add_session("ses-789")
    with pytest.raises(
        AssertionError,
        match="subject only has a single session without ID so populating session information makes no sense",
    ):
        sub1.populate_sessions_info_from_df(DataFrame())
    with pytest.raises(
        AssertionError,
        match=escape(
            "can't get session by ID when this subject only has a single session without an ID"
        ),
    ):
        sub1.session_by_id("ses-789")
    session = list(sub1.all_sessions())[0]
    assert list(sub1.all_sessions()) == [session]
    assert session.parent_subject is sub1

    assert session.id is None
    assert session.images_count() == 3
    with pytest.raises(
        AssertionError,
        match="can not attach ID field to info for implicit session without ID",
    ):
        assert session.info.all_fields_with_id(session)
    images = list(session.all_images())
    assert len(images) == 3
    for data_type, entities, suffix, ext, scan_info in [
        (DataType.ANAT, {}, "sfx", FileExtension.NII_GZ, {"a": "1", "bcd": None}),
        (
            DataType.ANAT,
            {"task": "rest"},
            None,
            FileExtension.NII_GZ,
            {"a": "2", "bcd": "3"},
        ),
        (
            DataType.PET,
            {"task": "rest"},
            "sfx2",
            FileExtension.NII,
            {"a": None, "bcd": "4"},
        ),
    ]:
        assert any(
            image.entities == Entities.from_dict(entities)
            and image.suffix == suffix
            and image.nifti_extension == ext
            and image.scan_info.all_fields() == scan_info
            and image.data_type == data_type
            for image in images
        )

    assert [
        str(image.get_nifti_image_path().relative_to(bids_path))
        for image in sub1.all_images()
    ] == [
        "sub-1/anat/sub-1_sfx.nii.gz",
        "sub-1/anat/sub-1_task-rest.nii.gz",
        "sub-1/pet/sub-1_task-rest_sfx2.nii",
    ]

    # Session with explicit ID/folder level
    sub2 = dataset.subject_by_id("sub-2")
    assert sub2 is not None
    assert sub2.sessions_count() == 1
    sesA = list(sub2.all_sessions())[0]
    assert list(sub2.all_sessions()) == [sesA]
    assert sesA.parent_subject is sub2
    sub2.add_session("ses-789")
    sub2.populate_sessions_info_from_df(
        DataFrame(
            {
                "session_id": ["ses-A", "ses-789"],
                "a": ["111", "222"],
            }
        )
    )
    ses789 = sub2.session_by_id("ses-789")
    assert ses789 is not None
    assert ses789.id == "ses-789"

    assert sesA.id == "ses-A"
    assert sesA.images_count() == 3
    images = list(sesA.all_images())
    assert len(images) == 3
    for data_type, entities, suffix, ext, scan_info in [
        (DataType.ANAT, {}, "sfx", FileExtension.NII_GZ, {"a": "1", "bcd": None}),
        (
            DataType.ANAT,
            {"task": "rest"},
            None,
            FileExtension.NII_GZ,
            {"a": "2", "bcd": "3"},
        ),
        (
            DataType.PET,
            {"task": "rest"},
            "sfx2",
            FileExtension.NII,
            {"a": None, "bcd": "4"},
        ),
    ]:
        assert any(
            image.entities == Entities.from_dict(entities)
            and image.suffix == suffix
            and image.nifti_extension == ext
            and image.scan_info.all_fields() == scan_info
            and image.data_type == data_type
            for image in images
        )

    print(
        [
            image.get_nifti_image_path().relative_to(bids_path)
            for image in sub2.all_images()
        ]
    )
    assert [
        str(image.get_nifti_image_path().relative_to(bids_path))
        for image in sub2.all_images()
    ] == [
        "sub-2/ses-A/anat/sub-2_ses-A_sfx.nii.gz",
        "sub-2/ses-A/anat/sub-2_ses-A_task-rest.nii.gz",
        "sub-2/ses-A/pet/sub-2_ses-A_task-rest_sfx2.nii",
    ]
