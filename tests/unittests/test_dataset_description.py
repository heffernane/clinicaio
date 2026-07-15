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
    return BIDSDatasetDescription._load_from_data(json_str)


def test_desc_valid_json():
    new_desc('{"Name": "TEST NAME", "BIDSVersion": "1.10.0", "DatasetType": "raw"}')


def test_extra_json_field():
    desc1 = new_desc(
        '{"Name": "TEST NAME", "BIDSVersion": "1.10.0", "DatasetType": "raw", "CAPSVersion": "1.0.0"}'
    )
    desc2 = new_desc(
        '{"Name": "TEST NAME", "BIDSVersion": "1.10.0", "DatasetType": "raw"}'
    )

    assert desc1 == desc2
    with pytest.raises(AttributeError):
        desc1.caps_version  # type: ignore


def test_desc_invalid_json():
    with pytest.raises(
        BIDSException,
        match="could not validate BIDS dataset description from JSON !!!!: Invalid JSON:",
    ):
        new_desc("!!!!")


@pytest.mark.parametrize(
    "json_desc",
    [
        "3",
        "[]",
    ],
)
def test_desc_invalid_json_object(json_desc: str):
    with pytest.raises(
        BIDSException,
        match=escape(
            f"could not validate BIDS dataset description from JSON {json_desc}: Input should be an object"
        ),
    ):
        new_desc(json_desc)


@pytest.mark.parametrize(
    ["json_text", "missing_field"],
    [
        ('{"BIDSVersion": "1.10.0","DatasetType": "raw"}', "Name"),
        ('{"Name": "TEST","DatasetType": "raw"}', "BIDSVersion"),
        # The dataset type field itself is not required as it has a default value
    ],
)
def test_desc_missing_fields(json_text: str, missing_field: str):
    with pytest.raises(
        BIDSException,
        match=f'could not validate BIDS dataset description from JSON {json_text}: field "{missing_field}": Field required',
    ):
        new_desc(json_text)


def test_invalid_dataset_type():
    json_text = '{"Name": "TEST BIDS", "BIDSVersion": "1.10.0", "DatasetType": "rauwe"}'

    with pytest.raises(
        BIDSException,
        match=escape(
            f"could not validate BIDS dataset description from JSON {json_text}: field \"DatasetType\": Input should be 'raw', 'derivative' or 'study'"
        ),
    ):
        new_desc(json_text)


def test_default_dataset_type():
    desc = new_desc('{"Name": "TEST", "BIDSVersion": "1.10.0"}')
    assert desc.dataset_type == BIDSDatasetType.RAW


def test_non_str_name():
    json_text = '{"Name": 3, "BIDSVersion": "1.10.0", "DatasetType": "raw"}'

    with pytest.raises(
        BIDSException,
        match=escape(
            f'could not validate BIDS dataset description from JSON {json_text}: field "Name": Input should be a valid string'
        ),
    ):
        new_desc(json_text)


def test_non_str_version():
    json_text = '{"Name": "3", "BIDSVersion": 1.10, "DatasetType": "raw"}'

    with pytest.raises(
        TypeError,
        match=escape(
            f"could not validate BIDS dataset description from JSON {json_text}: 'float' object is not iterable"
        ),
    ):
        new_desc(json_text)


def test_init():
    desc = BIDSDatasetDescription.new(
        BIDSDatasetType.DERIVATIVE, name="TEST DT NAME", bids_version="1.10.3"
    )
    assert desc.name == "TEST DT NAME"
    assert desc.dataset_type == BIDSDatasetType.DERIVATIVE
    assert str(desc.bids_version) == "1.10.3"
    assert desc.bids_version.major == 1
    assert desc.bids_version.minor == 10
    assert desc.bids_version.micro == 3

    with pytest.raises(
        BIDSException,
        match=escape(
            "could not create new dataset description: field \"bids_version\": Value error, Invalid version: '1.10.'"
        ),
    ):
        BIDSDatasetDescription.new(
            BIDSDatasetType.DERIVATIVE, name="TEST DT NAME", bids_version="1.10."
        )


def test_load_from_folder(fakefs: FakeFilesystem):
    bids_dir = Path("/tmp/BIDS_test")

    fakefs.create_file(
        bids_dir / "dataset_description.json",
        contents='{"Name": "TEST BIDS desc", "BIDSVersion": "1.10.7", "DatasetType": "study"}',
    )

    dataset_desc = BIDSDatasetDescription._load_from_folder(bids_dir)
    assert dataset_desc.name == "TEST BIDS desc"
    assert str(dataset_desc.bids_version) == "1.10.7"
    assert dataset_desc.dataset_type == BIDSDatasetType.STUDY


def test_write_to_folder_already_exists(fakefs: FakeFilesystem):
    bids_dir = Path("/tmp/BIDS_test")

    fakefs.create_file(bids_dir / "dataset_description.json")

    desc = BIDSDatasetDescription.new(
        BIDSDatasetType.DERIVATIVE, name="TEST DT NAME", bids_version="1.10.7"
    )
    with pytest.raises(
        FileExistsError,
        match=escape(
            f"File exists: PosixPath('/tmp/BIDS_test/dataset_description.json')"
        ),
    ):
        desc._write_to_folder(bids_dir)


def test_write_to_folder_non_existing_parent(fakefs: FakeFilesystem):
    bids_dir = Path("/tmp/BIDS_test")

    desc = BIDSDatasetDescription.new(
        BIDSDatasetType.DERIVATIVE, name="TEST DT NAME", bids_version="1.10.7"
    )
    with pytest.raises(
        FileNotFoundError,
        match=escape("No such file or directory"),
    ):
        desc._write_to_folder(bids_dir)


def test_write_to_folder(fakefs: FakeFilesystem):
    bids_dir = Path("/tmp/BIDS_test")

    fakefs.create_dir(bids_dir)

    desc = BIDSDatasetDescription.new(
        BIDSDatasetType.DERIVATIVE, name="TEST DT NAME", bids_version="1.10.7"
    )
    desc._write_to_folder(bids_dir)

    json_file = fakefs.get_object(bids_dir / "dataset_description.json")
    assert (
        json_file.contents
        == '{"Name":"TEST DT NAME","BIDSVersion":"1.10.7","DatasetType":"derivative"}'
    )
