import os
from pathlib import Path
from re import escape

import pytest
from _utils import _get_dataset_description
from pyfakefs.fake_filesystem import FakeFilesystem

from clinicaio.dataset import BIDSDataset
from clinicaio.entities import Entities
from clinicaio.image import Image
from clinicaio.types import BIDSException, DataType, FileExtension


@pytest.fixture
def fakefs(fs: FakeFilesystem):
    yield fs


def test_parse_no_extension():
    assert Image._parse_filename_components("task-rest_sfx") is None


def test_parse_no_entities_or_suffix():
    with pytest.raises(
        BIDSException,
        match=escape(f"found image filename .nii.gz without any entity or suffix"),
    ):
        Image._parse_filename_components(".nii.gz")


@pytest.mark.parametrize(
    ["file_ext"],
    [
        ("jsOn",),
        ("niigz",),
        ("gz",),
        # != tsv
        ("csv",),
        ("",),
        # Note the extra "." when concatenated below
        (".nii",),
        (".nii.gz",),
    ],
)
def test_parse_invalid_file_extension(file_ext: str):
    filename = f"task-rest_sfx.{file_ext}"
    with pytest.raises(
        BIDSException,
        match=escape(
            f"Found unknown file extension {file_ext} for filename {filename}"
        ),
    ):
        Image._parse_filename_components(filename)


def test_parse_entities_no_suffix():
    assert Image._parse_filename_components("task-rest.nii.gz") == (
        Entities.from_dict({"task": "rest"}),
        None,
        FileExtension.NII_GZ,
    )


def test_parse_suffix_no_entities():
    assert Image._parse_filename_components("rest.nii.gz") == (
        Entities.from_dict({}),
        "rest",
        FileExtension.NII_GZ,
    )


def test_parse_entities_suffix():
    assert Image._parse_filename_components("trc-18FFDG_task-rest_sfx.nii.gz") == (
        Entities.from_dict({"trc": "18FFDG", "task": "rest"}),
        "sfx",
        FileExtension.NII_GZ,
    )


@pytest.mark.parametrize(
    ["filename"],
    [
        ("trc-18FFDG_pet_task-rest_sfx.nii.gz",),
        ("pet_trc-18FFDG_task-rest_sfx.nii.gz",),
        ("trc-18FFDG_task-rest_pet_sfx.nii.gz",),
    ],
)
def test_parse_missing_key_value_separator(filename: str):
    with pytest.raises(
        BIDSException,
        match=escape(
            f"found invalid entities for image filename {filename}: found entities list "
        )
        + ".+"
        + escape(" that had an element without a - separator"),
    ):
        Image._parse_filename_components(filename)


def test_parse_invalid_suffix():
    filename = "fooé.nii.gz"
    with pytest.raises(
        BIDSException,
        match=escape(f"found invalid suffix label for image filename {filename}"),
    ):
        Image._parse_filename_components(filename)


def test_json_sidecar(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test")

    dataset = BIDSDataset(bids_path, _get_dataset_description())
    subject = dataset.add_subject("sub-01", None)
    session = subject.add_session("ses-A", None)
    image = session.write_image(
        DataType.PET,
        FileExtension.NII_GZ,
        entities={"task": "rest"},
        suffix="sfx",
        scan_info=None,
    )
    assert fakefs.exists(bids_path / "sub-01/ses-A/pet")

    with pytest.raises(OSError, match="No such file or directory"):
        image.json_sidecar

    sidecar_path = bids_path / "sub-01/ses-A/pet/sub-01_ses-A_task-rest_sfx.json"
    sidecar_file = fakefs.create_file(sidecar_path, contents='{3: "3"}')
    with pytest.raises(
        BIDSException,
        match=escape(
            "could not parse JSON sidecar file: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)"
        ),
    ):
        image.json_sidecar

    sidecar_file.set_contents('["foo", "bar", 3]')
    with pytest.raises(
        BIDSException,
        match=escape(
            f"expected JSON sidecar {sidecar_path} to contain an object as root node"
        ),
    ):
        image.json_sidecar

    os.remove(sidecar_path)
    assert not fakefs.exists(sidecar_path)
    assert not fakefs.has_open_file(sidecar_file)

    fakefs.create_file(
        sidecar_path, contents='{"a": "b", "c": 3, "e": ["a", {"f": "g"}]}'
    )
    sidecar = image.json_sidecar
    assert sidecar == {"a": "b", "c": 3, "e": ["a", {"f": "g"}]}

    # Make sure it actually is cached
    cached_sidecar = image.json_sidecar
    assert sidecar is cached_sidecar
