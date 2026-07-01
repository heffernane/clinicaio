import os
from pathlib import Path
from re import escape

import pytest
from _utils import _get_dataset_description, _setup_dataset_description
from pandas import DataFrame
from pyfakefs.fake_filesystem import FakeFilesystem

from clinicaio.dataset import BIDSDataset
from clinicaio.entities import Entities
from clinicaio.image import Image
from clinicaio.types import BIDSException, DataType, FileExtension


# Rename the pyfakefs fixture so it's clearer what it actually is
@pytest.fixture
def fakefs(fs):
    yield fs


def test_duplicated_images_different_file_extension(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test")

    fakefs.create_file(
        bids_path / "dataset_description.json",
        contents='{"Name": "TEST 123", "BIDSVersion": "1.11.0", "DatasetType": "derivative"}',
    )

    session_dir = bids_path / "sub-A/ses-A/"
    images_dir = session_dir / "anat"

    nii_gz_path = images_dir / "sub-A_ses-A_trc-18FFDG_task-rest_sfx.nii.gz"
    faulty_path = images_dir / "sub-A_ses-A_trc-18FFDG_task-rest_sfx.nii"
    fakefs.create_file(nii_gz_path)
    fakefs.create_file(images_dir / "sub-A_ses-A_trc-18FFDG_sfx.nii.gz")
    fakefs.create_file(images_dir / "sub-A_ses-A_trc-18FFDG_task-rest.nii.gz")
    fakefs.create_file(images_dir / "sub-A_ses-A_sfx.nii.gz")
    fakefs.create_file(images_dir / "sub-A_ses-A_sfx2.nii.gz")

    # This one is the same except for the data type, so they can safely exist along one another
    fakefs.create_file(
        session_dir / "pet" / "sub-A_ses-A_trc-18FFDG_task-rest_sfx.nii.gz"
    )

    # No real duplicate at this point
    BIDSDataset.populate_from_dir(
        bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
    )

    # This is the "duplicate" image file (with only .nii vs .nii.gz as difference)
    fakefs.create_file(faulty_path)

    with pytest.raises(
        BIDSException,
        match=escape(
            f"got exception while adding subject sub-A and populating its sessions: got exception while adding session ses-A and "
            f"populating its images: found image {faulty_path} that only had file extension as difference from ['{nii_gz_path}'] "
            "(i.e. .nii vs .nii.gz with same subject+session+datatype+entities+suffix)"
        ),
    ):
        BIDSDataset.populate_from_dir(
            bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
        )


def test_write_image_parent_directories(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test")

    dataset = BIDSDataset(bids_path, _get_dataset_description())
    subject = dataset.add_subject("sub-001", None)
    session = subject.add_session("ses-A", None)

    assert not fakefs.exists(bids_path)

    session.write_image(
        DataType.ANAT, FileExtension.NII_GZ, entities={}, suffix="T1w", scan_info=None
    )

    assert sorted(list(os.listdir(bids_path))) == ["sub-001"]
    assert fakefs.isdir(bids_path / "sub-001" / "ses-A" / "anat")

    dataset.write_to_folder(readme="README test")

    assert sorted(list(os.listdir(bids_path))) == [
        "README",
        "dataset_description.json",
        "sub-001",
    ]


def test_images_count(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test")

    ses_path = bids_path / "sub-1/ses-A/"
    fakefs.create_file(ses_path / "anat/sub-1_ses-A_task-rest_sfx1.nii.gz")
    fakefs.create_file(ses_path / "anat/sub-1_ses-A_task-rest_sfx2.nii.gz")
    fakefs.create_file(ses_path / "pet/sub-1_ses-A_task-rest_sfx3.nii.gz")
    _setup_dataset_description(fakefs, bids_path)

    dataset = BIDSDataset.populate_from_dir(
        bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
    )

    assert len(list(dataset.all_images())) == 3

    subject = dataset.subject_by_id("sub-1")
    assert subject is not None
    session = subject.session_by_id("ses-A")
    assert session is not None

    assert list(session.images_by_data_type(DataType.FMAP)) == []
    assert session.images_count(DataType.FMAP) == 0
    assert list(
        map(Image.get_nifti_image_path, session.images_by_data_type(DataType.PET))
    ) == [
        bids_path / "sub-1/ses-A/pet/sub-1_ses-A_task-rest_sfx3.nii.gz",
    ]
    assert session.images_count(DataType.PET) == 1
    assert list(
        map(Image.get_nifti_image_path, session.images_by_data_type(DataType.ANAT))
    ) == list(
        map(
            lambda path: bids_path / "sub-1/ses-A" / path,
            [
                "anat/sub-1_ses-A_task-rest_sfx1.nii.gz",
                "anat/sub-1_ses-A_task-rest_sfx2.nii.gz",
            ],
        )
    )
    assert session.images_count(DataType.ANAT) == 2

    assert session.images_count() == 3


def test_write_image_invalid_file_extension(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-01", None)
    session = subject.add_session("ses-A", None)

    with pytest.raises(
        BIDSException,
        match="provided non-NIFTI file extension json when adding image to session",
    ):
        session.write_image(
            # Note the non-NIFTI file extension
            DataType.PET,
            FileExtension.JSON,
            entities={},
            suffix=None,
            scan_info=None,
        )


def test_write_image_invalid_suffix(fakefs: FakeFilesystem):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-01", None)
    session = subject.add_session("ses-A", None)

    with pytest.raises(
        BIDSException,
        match=escape("invalid suffix: String should match pattern '^[a-zA-Z0-9]+$'"),
    ):
        session.write_image(
            # Note the invalid suffix
            DataType.PET,
            FileExtension.NII_GZ,
            entities={},
            suffix="é",
            scan_info=None,
        )


def test_scans_info_df_no_filename_column():
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-01", None)
    session = subject.add_session("ses-A", None)

    with pytest.raises(
        BIDSException, match="dataframe did not have required filename column"
    ):
        session.populate_image_scans_info_from_df(DataFrame({"a": [1, 2], "b": [3, 4]}))


def test_scans_info_df_none_filename():
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-01", None)
    session = subject.add_session("ses-A", None)
    image = session._add_image(
        DataType.PET,
        FileExtension.NII_GZ,
        entities=Entities.from_dict({}),
        suffix="sfx",
        scan_info=None,
    )
    assert image.parent_session is session

    session.populate_image_scans_info_from_df(
        DataFrame(
            {
                "a": ["1", "2"],
                "b": ["3", "4"],
                # Note the None filename
                "filename": [None, "pet/sub-01_ses-A_sfx.nii.gz"],
            }
        )
    )

    assert image.scan_info.all_fields() == {"a": "2", "b": "4"}


def test_scans_info_df_missing_data_type_dir():
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-01", None)
    session = subject.add_session("ses-A", None)
    image = session._add_image(
        DataType.PET,
        FileExtension.NII_GZ,
        entities=Entities.from_dict({}),
        suffix="sfx",
        scan_info=None,
    )
    assert image.parent_session is session

    with pytest.raises(
        BIDSException,
        match=escape(
            "expected image/scan filename of format <data_type>/<...> for sub-01_ses-A_sfx.nii.gz in dataframe"
        ),
    ):
        session.populate_image_scans_info_from_df(
            DataFrame(
                {
                    "a": ["2"],
                    "b": ["4"],
                    "filename": ["sub-01_ses-A_sfx.nii.gz"],
                }
            )
        )

    assert image.scan_info.all_fields() == {}


def test_scans_info_df_invalid_data_type():
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-01", None)
    session = subject.add_session("ses-A", None)
    image = session._add_image(
        DataType.PET,
        FileExtension.NII_GZ,
        entities=Entities.from_dict({}),
        suffix="sfx",
        scan_info=None,
    )
    assert image.parent_session is session

    with pytest.raises(
        BIDSException,
        match=escape(
            "expected valid data type as first folder of filename PET/sub-01_ses-A_sfx.nii.gz in dataframe"
        ),
    ):
        session.populate_image_scans_info_from_df(
            DataFrame(
                {
                    "a": ["2"],
                    "b": ["4"],
                    "filename": ["PET/sub-01_ses-A_sfx.nii.gz"],
                }
            )
        )

    assert image.scan_info.all_fields() == {}


def test_scans_info_df_missing_filename_sub_ses_prefix():
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    subject = dataset.add_subject("sub-01", None)
    session = subject.add_session("ses-A", None)
    image = session._add_image(
        DataType.PET,
        FileExtension.NII_GZ,
        entities=Entities.from_dict({}),
        suffix="sfx",
        scan_info=None,
    )
    assert image.parent_session is session

    with pytest.raises(
        BIDSException,
        match=escape(
            "expected valid data type as first folder of filename PET/sub-1_ses-A_sfx.nii.gz in dataframe"
        ),
    ):
        session.populate_image_scans_info_from_df(
            DataFrame(
                {
                    "a": ["2"],
                    "b": ["4"],
                    # Note: sub-01 vs sub-1
                    "filename": ["PET/sub-1_ses-A_sfx.nii.gz"],
                }
            )
        )

    assert image.scan_info.all_fields() == {}


def test_skipped_invalid_datatype_or_no_file_extension(fakefs: FakeFilesystem):
    image_paths = [
        "sub-1/ses-A/pèt/sub-1_ses-A_task-rest_sfx.nii.gz",
        "sub-1/ses-A/anat/sub-1_ses-A_task-rest_sfx",
    ]

    bids_path = Path("/tmp/bids_test")

    _setup_dataset_description(fakefs, bids_path)

    for path in image_paths:
        fakefs.create_file(bids_path / path)

    global checked_unhandled_entries
    checked_unhandled_entries = False

    def unhandled_entries(paths: list[str]):
        assert sorted(paths) == sorted(
            [
                "sub-1/ses-A/pèt",
                "sub-1/ses-A/anat/sub-1_ses-A_task-rest_sfx",
            ]
        )

        global checked_unhandled_entries
        checked_unhandled_entries = True

    dataset = BIDSDataset.populate_from_dir(
        bids_path,
        subjects_info=False,
        sessions_info=False,
        image_scans_info=False,
        _report_unhandled_entries=unhandled_entries,
    )
    assert checked_unhandled_entries

    assert list(dataset.all_images()) == []


def test_non_directory_data_type(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test")

    _setup_dataset_description(fakefs, bids_path)

    # Note the fact it's created as a file instead of a directory
    fakefs.create_file(bids_path / "sub-1/ses-A/anat")

    with pytest.raises(
        BIDSException,
        match=escape(
            "got exception while adding subject sub-1 and populating its sessions: "
            "got exception while adding session ses-A and populating its images: "
            "Found data type entry anat that was not a directory"
        ),
    ):
        BIDSDataset.populate_from_dir(
            bids_path,
            subjects_info=False,
            sessions_info=False,
            image_scans_info=False,
        )


def test_missing_image_prefix(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test")

    _setup_dataset_description(fakefs, bids_path)

    fakefs.create_file(bids_path / "sub-1/ses-A/anat/task-rest_sfx.nii.gz")

    with pytest.raises(
        BIDSException,
        match=escape(
            "got exception while adding subject sub-1 and populating its sessions: "
            "got exception while adding session ses-A and populating its images: "
            "expected anat/task-rest_sfx.nii.gz filename to start with sub-1_ses-A_ due to its placement in the BIDS directory hierarchy"
        ),
    ):
        BIDSDataset.populate_from_dir(
            bids_path,
            subjects_info=False,
            sessions_info=False,
            image_scans_info=False,
        )


def test_missing_image_prefix_no_session(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test")

    _setup_dataset_description(fakefs, bids_path)

    fakefs.create_file(bids_path / "sub-1/anat/task-rest_sfx.nii.gz")

    with pytest.raises(
        BIDSException,
        match=escape(
            "got exception while adding subject sub-1 and populating its sessions: "
            "got exception while adding session without ID/dedicated folder and populating its images: "
            "expected anat/task-rest_sfx.nii.gz filename to start with sub-1_ due to its placement in the BIDS directory hierarchy"
        ),
    ):
        BIDSDataset.populate_from_dir(
            bids_path,
            subjects_info=False,
            sessions_info=False,
            image_scans_info=False,
        )


def test_invalid_image_filename(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test")

    _setup_dataset_description(fakefs, bids_path)

    fakefs.create_file(bids_path / "sub-1/anat/sub-1_tàsk-rest_sfx.nii.gz")

    with pytest.raises(
        BIDSException,
        match=escape(
            "got exception while adding subject sub-1 and populating its sessions: "
            "got exception while adding session without ID/dedicated folder and populating its images: "
            "Found invalid image filename sub-1_tàsk-rest_sfx.nii.gz in folder anat: "
            "found invalid entities for image filename tàsk-rest_sfx.nii.gz: "
            "BIDS label tàsk must be all [a-zA-Z0-9] characters"
        ),
    ):
        BIDSDataset.populate_from_dir(
            bids_path,
            subjects_info=False,
            sessions_info=False,
            image_scans_info=False,
        )
