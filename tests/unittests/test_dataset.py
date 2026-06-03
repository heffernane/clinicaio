from pathlib import Path
from re import escape

import pytest
from _utils import _get_dataset_description, _make_tsv, _setup_dataset_description
from packaging.version import Version
from pyfakefs.fake_filesystem import FakeFilesystem

from clinicaio.dataset import BIDSDataset
from clinicaio.dataset_description import BIDSDatasetDescription, BIDSDatasetType
from clinicaio.subject import SubjectInfo
from clinicaio.types import BIDSException

# NOTE: Each test has its own pyfakefs/it's reset after the individual test run ends. Pytest runs tests sequentially.
# See:
# - https://pytest-pyfakefs.readthedocs.io/en/latest/intro.html#features
# - https://docs.pytest.org/en/stable/explanation/flaky.html#thread-safety

# NOTE: all the fakefs.create_*() calls create the whole file hierarchy that appears in the path, for convenience.


# NOTE: do not create global Path here as they will not be setup in the fakefs, which will cause issues later.
# https://github.com/pytest-dev/pyfakefs/discussions/1312
# https://pytest-pyfakefs.readthedocs.io/en/latest/troubleshooting.html#pathlib-path-objects-created-outside-of-tests
#
# Essentially when one of the paths used is a "real" pathlib one and
# an other one is from pyfakefs's fake pathlib replacement module, then
# Path.relative_to() (in BIDSDataset.populate_from_dir()) does not work well
# as it outputs '/tmp/bids_test/README' is not in the subpath of '/tmp/bids_test'
# which is nonsense.


# Rename the pyfakefs fixture so it's clearer what it actually is
@pytest.fixture
def fakefs(fs):
    yield fs


@pytest.fixture
def bids_path():
    return Path("/tmp/bids_test")


def test_make_tsv():
    expected = "participant_id\ta\tb\tc\nv\t2\t3\t4"

    assert (
        _make_tsv(
            [
                ["participant_id", "a", "b", "c"],
                "v234",
            ]
        )
        == expected
    )

    assert (
        _make_tsv(
            [
                ["participant_id", "a", "b", "c"],
                ["v", "2", "3", "4"],
            ]
        )
        == expected
    )

    assert _make_tsv(["abc", "123"]) == "a\tb\tc\n1\t2\t3"

    assert _make_tsv(["a", "1"]) == "a\n1"


def test_fakefs_setup(fakefs: FakeFilesystem):
    assert type(fakefs) == FakeFilesystem


# Deeper testing of the dataset description happens in the eponymous test
def test_read_dataset_description(fakefs: FakeFilesystem, bids_path: Path):
    _setup_dataset_description(fakefs, bids_path)

    dataset = BIDSDataset.populate_from_dir(
        bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
    )
    assert type(dataset.description) == BIDSDatasetDescription
    assert dataset.description.name == "TEST 123"
    assert str(dataset.description.bids_version) == "1.11.0"
    assert dataset.description.bids_version == Version("1.11.0")
    assert dataset.description.dataset_type == BIDSDatasetType.DERIVATIVE


def test_missing_dataset_description(fakefs: FakeFilesystem, bids_path: Path):
    with pytest.raises(
        BIDSException,
        match=f"^could not read BIDS description from JSON file: could not open BIDS description JSON file: ",
    ):
        BIDSDataset.populate_from_dir(
            bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
        )


def test_read_participants_tsv_missing_id_column(
    fakefs: FakeFilesystem, bids_path: Path
):
    _setup_dataset_description(fakefs, bids_path)

    tsv_path = bids_path / "participants.tsv"
    fakefs.create_file(
        tsv_path,
        contents=_make_tsv(["abc", "123"]),
    )

    msg = f"could not populate subjects info from TSV file {tsv_path}: dataframe did not have required participant_id column"
    with pytest.raises(BIDSException, match=escape(msg)):
        BIDSDataset.populate_from_dir(
            bids_path, subjects_info=True, sessions_info=False, image_scans_info=False
        )


def test_read_participants_tsv_missing_id_column_disabled(
    fakefs: FakeFilesystem, bids_path: Path
):
    _setup_dataset_description(fakefs, bids_path)

    tsv_path = bids_path / "participants.tsv"
    fakefs.create_file(
        tsv_path,
        contents=_make_tsv(["abc", "123"]),
    )

    # Note that the participants.tsv/subject_info reading is disabled,
    # so even an invalid TSV will not raise an exception, as expected.
    BIDSDataset.populate_from_dir(
        bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
    )


def test_read_participants_tsv_invalid_id(fakefs: FakeFilesystem, bids_path: Path):
    _setup_dataset_description(fakefs, bids_path)

    tsv_path = bids_path / "participants.tsv"
    fakefs.create_file(
        tsv_path,
        contents=_make_tsv(
            [
                ["participant_id", "a", "b", "c"],
                "v234",
            ]
        ),
    )
    # We want to make sure that the code does not just blindly check if the given ID is a sub-directory
    # of the BIDS directory, without validating the ID itself.
    fakefs.create_dir(bids_path / "v")

    msg = f"could not populate subjects info from TSV file {tsv_path}: found invalid subject ID v in dataframe: String should match pattern '^sub-[a-zA-Z0-9]+$'"
    with pytest.raises(BIDSException, match=escape(msg)):
        BIDSDataset.populate_from_dir(
            bids_path, subjects_info=True, sessions_info=False, image_scans_info=False
        )


def test_read_participants_tsv_na_none_participant_id(
    fakefs: FakeFilesystem, bids_path: Path
):
    _setup_dataset_description(fakefs, bids_path)

    tsv_path = bids_path / "participants.tsv"
    fakefs.create_file(
        tsv_path,
        contents=_make_tsv(
            [
                ["participant_id", "a", "b", "c"],
                ["n/a", "abc", "bce", "cef"],
                ["n/a", "n/a", "n/a", "n/a"],
                ["sub-001", "abc", "bce", "cef"],
            ]
        ),
    )
    fakefs.create_dir(bids_path / "sub-001")

    dataset = BIDSDataset.populate_from_dir(
        bids_path, subjects_info=True, sessions_info=False, image_scans_info=False
    )
    assert dataset.subjects_count() == 1
    subject = list(dataset.all_subjects())[0]
    assert subject.id == "sub-001"
    assert subject.parent_dataset is dataset
    assert subject.sessions_count() == 0
    assert subject.info == SubjectInfo.from_fields({"a": "abc", "b": "bce", "c": "cef"})


def test_read_participants_tsv_not_found_participant_by_id(
    fakefs: FakeFilesystem, bids_path: Path
):
    _setup_dataset_description(fakefs, bids_path)

    tsv_path = bids_path / "participants.tsv"
    fakefs.create_file(
        tsv_path,
        contents=_make_tsv(
            [
                ["participant_id", "a", "b", "c"],
                ["sub-001", "abc", "bce", "cef"],
                # Note: this subject does not exist in this dataset, but for now we do not throw an error for it.
                ["sub-002", "abc", "bce", "cef"],
            ]
        ),
    )
    fakefs.create_dir(bids_path / "sub-001")

    dataset = BIDSDataset.populate_from_dir(
        bids_path, subjects_info=True, sessions_info=False, image_scans_info=False
    )
    assert dataset.subjects_count() == 1
    subject = list(dataset.all_subjects())[0]
    assert subject.id == "sub-001"
    assert subject.parent_dataset is dataset
    assert subject.sessions_count() == 0
    assert subject.info == SubjectInfo.from_fields({"a": "abc", "b": "bce", "c": "cef"})


def test_read_dataset_subject_structure(fakefs: FakeFilesystem, bids_path: Path):
    _setup_dataset_description(fakefs, bids_path)
    desc = _get_dataset_description()
    fakefs.create_file(bids_path / "README")
    fakefs.create_dir(bids_path / "sub-001")
    fakefs.create_dir(bids_path / "sub-01")
    fakefs.create_dir(bids_path / "sub001")
    fakefs.create_dir(bids_path / "fmap")
    fakefs.create_file(bids_path / "sub002")
    fakefs.create_file(bids_path / ".DS_Store")
    # NOTE: we do not put any information there, as we're not reading it from this test
    fakefs.create_file(bids_path / "participants.tsv")

    global checked_unhandled_entries
    checked_unhandled_entries = False

    def f(unhandled_entries: list[str]):
        assert sorted(unhandled_entries) == sorted(
            [
                "README",
                "sub001",
                "fmap",
                "sub002",
                ".DS_Store",
            ]
        ), f"{unhandled_entries}"
        global checked_unhandled_entries
        checked_unhandled_entries = True

    dataset = BIDSDataset.populate_from_dir(
        bids_path,
        subjects_info=False,
        sessions_info=False,
        image_scans_info=False,
        _report_unhandled_entries=f,
    )
    assert dataset.description == desc
    assert checked_unhandled_entries

    assert dataset.subjects_count() == 2
    subjects = sorted(list(dataset.all_subjects()), key=lambda subject: str(subject.id))
    assert len(subjects) == 2
    assert subjects[0].id == "sub-001"
    assert subjects[0].id != "sub-01"
    assert subjects[1].id == "sub-01"
    assert subjects[1].id != "sub-001"
    assert subjects[0].info == SubjectInfo.from_fields({})
    assert subjects[1].info == SubjectInfo.from_fields({})
    assert subjects[0].info.is_empty()
    assert subjects[1].info.is_empty()
    assert subjects[0].parent_dataset is dataset
    assert subjects[1].parent_dataset is dataset
    assert subjects[0].sessions_count() == 0
    assert subjects[1].sessions_count() == 0
    assert list(subjects[0].all_sessions()) == []
    assert list(subjects[1].all_sessions()) == []


def test_read_dataset_non_directory_subject(fakefs: FakeFilesystem, bids_path: Path):
    _setup_dataset_description(fakefs, bids_path)
    fakefs.create_file(bids_path / "sub-001")

    with pytest.raises(
        BIDSException, match=f"found sub- entry sub-001 that was not a directory"
    ):
        BIDSDataset.populate_from_dir(
            bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
        )


def test_read_dataset_invalid_subject_folder_id(
    fakefs: FakeFilesystem, bids_path: Path
):
    _setup_dataset_description(fakefs, bids_path)
    fakefs.create_dir(bids_path / "sub-é001")

    with pytest.raises(
        BIDSException,
        match=escape(
            "Found invalid subject/subject ID sub-é001: String should match pattern '^sub-[a-zA-Z0-9]+$'"
        ),
    ):
        BIDSDataset.populate_from_dir(
            bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
        )


def test_read_dataset_propagate_sessions_exceptions(
    fakefs: FakeFilesystem, bids_path: Path
):
    _setup_dataset_description(fakefs, bids_path)
    # Note that we're creating a file here, not a directory (which is incorrect BIDS-wise)
    fakefs.create_file(bids_path / "sub-001" / "ses-001")

    with pytest.raises(
        BIDSException,
        match=f"got exception while adding subject sub-001 and populating its sessions: ",
    ):
        BIDSDataset.populate_from_dir(
            bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
        )


def test_add_subject_duplicate_id(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())

    assert dataset.subjects_count() == 0
    assert list(dataset.all_subjects()) == []

    subject = dataset.add_subject("sub-001", None)
    assert dataset.subjects_count() == 1
    assert len(list(dataset.all_subjects())) == 1
    assert list(dataset.all_subjects())[0] is subject

    assert subject.id == "sub-001"
    assert subject.info.is_empty()
    assert subject.parent_dataset is dataset
    assert subject.sessions_count() == 0
    assert list(subject.all_sessions()) == []

    with pytest.raises(
        BIDSException,
        match="tried to add subject of ID sub-001 but it already exists within this dataset",
    ):
        dataset.add_subject("sub-001", None)


def test_add_subject_none_info(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())

    subject = dataset.add_subject("sub-001", None)
    assert subject.info.all_fields() == {}
    assert subject.info.is_empty()


def test_add_subject_provided_info(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())

    dct = {"a": "abc", "bcd": "a"}
    subject = dataset.add_subject("sub-001", SubjectInfo.from_fields(dct))
    assert subject.info.all_fields() == dct
    assert subject.info == SubjectInfo.from_fields(dct)


def test_add_subject_invalid_id(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())

    with pytest.raises(
        BIDSException,
        match=escape(
            "invalid subject ID sub-é: String should match pattern '^sub-[a-zA-Z0-9]+$'"
        ),
    ):
        dataset.add_subject("sub-é", None)


def test_write_root_file_non_root_file_name(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())

    with pytest.raises(
        BIDSException,
        match=escape(
            "BIDSDataset.write_root_file() is not meant to write in sub-folders (foo/README)"
        ),
    ):
        with dataset.write_root_file("foo/README", write_binary=False) as f:
            pass


def test_write_root_file_already_existing(fakefs: FakeFilesystem, bids_path: Path):
    fakefs.create_file(bids_path / "README")
    dataset = BIDSDataset(bids_path, _get_dataset_description())

    with pytest.raises(
        BIDSException,
        match=escape("can't write root dataset file README as it already exists"),
    ):
        with dataset.write_root_file("README", write_binary=False) as f:
            pass


def test_write_root_file_already_existing_directory(
    fakefs: FakeFilesystem, bids_path: Path
):
    # Note that here a directory is created instead of a file
    fakefs.create_dir(bids_path / "README")
    dataset = BIDSDataset(bids_path, _get_dataset_description())

    with pytest.raises(
        BIDSException,
        match=escape("can't write root dataset file README as it already exists"),
    ):
        with dataset.write_root_file("README", write_binary=False) as f:
            pass


def test_write_root_file_text_mode(fakefs: FakeFilesystem, bids_path: Path):
    dataset = BIDSDataset(bids_path, _get_dataset_description())

    dataset.write_to_folder(readme="readme test")
    with dataset.write_root_file("FOO", write_binary=False) as f:
        f.write("foo")
        f.flush()
        file = fakefs.get_object(bids_path / "FOO")
        assert file.contents == "foo"

        with pytest.raises(
            TypeError, match=escape("write() argument must be str, not bytes")
        ):
            f.write(b"foo")


def test_write_root_file_binary_mode(fakefs: FakeFilesystem, bids_path: Path):
    dataset = BIDSDataset(bids_path, _get_dataset_description())

    dataset.write_to_folder(readme="readme test")
    with dataset.write_root_file("FOO", write_binary=True) as f:
        f.write(b"foo")
        f.flush()
        file = fakefs.get_object(bids_path / "FOO")
        assert file.byte_contents == b"foo"

        with pytest.raises(
            TypeError, match=escape("a bytes-like object is required, not 'str'")
        ):
            f.write("bar")


def test_subject_by_id_invalid_id():
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())

    with pytest.raises(
        BIDSException,
        match=escape(
            "invalid subject ID 001: String should match pattern '^sub-[a-zA-Z0-9]+$'"
        ),
    ):
        # note the missing sub- prefix
        dataset.subject_by_id("001")


def test_all_sessions_and_images(fakefs: FakeFilesystem, bids_path: Path):
    _setup_dataset_description(fakefs, bids_path)

    image_paths = []

    for path in [
        "sub-1/ses-A/anat/sub-1_ses-A_task-rest_sfx.nii.gz",
        "sub-1/ses-A/pet/sub-1_ses-A_task-rest_sfx2.nii.gz",
        "sub-1/ses-B/anat/sub-1_ses-B_task-rest_sfx3.nii.gz",
        "sub-2/ses-A/anat/sub-2_ses-A_task-rest_sfx4.nii.gz",
        "sub-2/ses-B/pet/sub-2_ses-B_task-rest_sfx5.nii.gz",
    ]:
        full_path = bids_path / path
        image_paths.append(full_path)
        fakefs.create_file(full_path)

    assert len(image_paths) == 5

    dataset = BIDSDataset.populate_from_dir(
        bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
    )

    assert sorted(
        (session.parent_subject.id, session.id) for session in dataset.all_sessions()
    ) == [
        ("sub-1", "ses-A"),
        ("sub-1", "ses-B"),
        ("sub-2", "ses-A"),
        ("sub-2", "ses-B"),
    ]

    assert (
        sorted(image.get_nifti_image_path() for image in dataset.all_images())
        == image_paths
    )
