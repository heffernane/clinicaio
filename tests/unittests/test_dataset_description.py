from io import StringIO
from pathlib import Path
from re import escape

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem

from clinicaio.dataset_description import BIDSDatasetDescription, BIDSDatasetType
from clinicaio.types import BIDSException

@pytest.fixture
def fakefs(fs: FakeFilesystem):
    yield fs


def new_desc(json_str: str) -> BIDSDatasetDescription:
    return BIDSDatasetDescription._load_from_data(StringIO(json_str))

def test_desc_valid_json():
    new_desc('{"Name": "TEST NAME", "BIDSVersion": "1.10.0", "DatasetType": "raw"}')

def test_desc_invalid_json():
    with pytest.raises(
        BIDSException, match="could not read or parse BIDS JSON description file: "
    ):
        new_desc("!!!!")


def test_desc_invalid_json_object():
    with pytest.raises(
        BIDSException,
        match=escape("BIDS JSON description is invalid (not a JSON object)"),
    ):
        new_desc("3")
    with pytest.raises(
        BIDSException,
        match=escape("BIDS JSON description is invalid (not a JSON object)"),
    ):
        new_desc("[]")


def test_desc_missing_fields():
    with pytest.raises(
        BIDSException,
        match="missing mandatory field in BIDS JSON description file: 'Name'",
    ):
        new_desc('{"BIDSVersion": "1.10.0","DatasetType": "raw"}')
    with pytest.raises(
        BIDSException,
        match="missing mandatory field in BIDS JSON description file: 'BIDSVersion'",
    ):
        new_desc('{"Name": "TEST","DatasetType": "raw"}')


def test_default_dataset_type():
    desc = new_desc('{"Name": "TEST", "BIDSVersion": "1.10.0"}')
    assert desc.dataset_type == BIDSDatasetType.RAW

def test_non_str_name():
    with pytest.raises(BIDSException, match=escape("invalid type for Name field in BIDS JSON description file: 3")):
        new_desc('{"Name": 3, "BIDSVersion": "1.10.0", "DatasetType": "raw"}')

def test_non_str_version():
    with pytest.raises(BIDSException, match=escape("invalid type for BIDSVersion field in BIDS JSON description file: 1.1")):
        new_desc('{"Name": "3", "BIDSVersion": 1.10, "DatasetType": "raw"}')

def test_init():
    desc = BIDSDatasetDescription(BIDSDatasetType.DERIVATIVE, name="TEST DT NAME", version="1.10.3")
    assert desc.name == "TEST DT NAME"
    assert desc.dataset_type == BIDSDatasetType.DERIVATIVE
    assert str(desc.version) == "1.10.3"
    assert desc.version.major == 1
    assert desc.version.minor == 10
    assert desc.version.micro == 3

    with pytest.raises(BIDSException, match=escape("invalid BIDS version 1.10.: Invalid version: '1.10.'")):
       BIDSDatasetDescription(BIDSDatasetType.DERIVATIVE, name="TEST DT NAME", version="1.10.")

def test_load_from_folder(fakefs: FakeFilesystem):
    bids_dir = Path("/tmp/BIDS_test")

    fakefs.create_file(
        bids_dir / "dataset_description.json",
        contents='{"Name": "TEST BIDS desc", "BIDSVersion": "1.10.7", "DatasetType": "study"}',
    )

    dataset_desc = BIDSDatasetDescription._load_from_folder(bids_dir)
    assert dataset_desc.name == "TEST BIDS desc"
    assert str(dataset_desc.version) == "1.10.7"
    assert dataset_desc.dataset_type == BIDSDatasetType.STUDY

def test_write_to_folder_already_exists(fakefs: FakeFilesystem):
    bids_dir = Path("/tmp/BIDS_test")

    fakefs.create_file(bids_dir / "dataset_description.json")

    desc = BIDSDatasetDescription(BIDSDatasetType.DERIVATIVE, name="TEST DT NAME", version="1.10.7")
    with pytest.raises(BIDSException, match=escape(f"can't write dataset description JSON to folder {bids_dir} as it already exists there")):
        desc._write_to_folder(bids_dir)

def test_write_to_folder_non_existing_parent(fakefs: FakeFilesystem):
    bids_dir = Path("/tmp/BIDS_test")

    desc = BIDSDatasetDescription(BIDSDatasetType.DERIVATIVE, name="TEST DT NAME", version="1.10.7")
    with pytest.raises(BIDSException, match=escape(f"can't read dataset description JSON from non-existing folder {bids_dir}")):
        desc._write_to_folder(bids_dir)


def test_write_to_folder(fakefs: FakeFilesystem):
    bids_dir = Path("/tmp/BIDS_test")

    fakefs.create_dir(bids_dir)

    desc = BIDSDatasetDescription(BIDSDatasetType.DERIVATIVE, name="TEST DT NAME", version="1.10.7")
    desc._write_to_folder(bids_dir)

    json_file = fakefs.get_object(bids_dir / "dataset_description.json")
    assert json_file.contents == '{"Name": "TEST DT NAME", "BIDSVersion": "1.10.7", "DatasetType": "derivative"}'
