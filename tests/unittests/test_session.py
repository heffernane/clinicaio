from pathlib import Path
from re import escape

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from clinicaio.dataset import BIDSDataset
from clinicaio.types import BIDSException


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
