from pathlib import Path
from typing import Iterable

from pyfakefs.fake_filesystem import FakeFilesystem

from clinicaio.dataset_description import BIDSDatasetDescription, BIDSDatasetType


def _setup_dataset_description(fakefs: FakeFilesystem, bids_path: Path):
    fakefs.create_file(
        bids_path / "dataset_description.json",
        contents='{"Name": "TEST 123", "BIDSVersion": "1.11.0", "DatasetType": "derivative"}',
    )


def _get_dataset_description() -> BIDSDatasetDescription:
    return BIDSDatasetDescription.new(
        BIDSDatasetType.DERIVATIVE, name="TEST 123", bids_version="1.11.0"
    )


# Note: it may be convenient to have some lines that are directly strings instead of proper lists:
# in that case each element of the line will be a character of the string (i.e. "abc" vs ["a", "b", "c"])
def _make_tsv(lines: Iterable[Iterable[str]]) -> str:
    return "\n".join("\t".join(fields) for fields in lines)
