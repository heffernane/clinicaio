from clinicaio.dataset import *

import shutil

# IN _env.py:
#
# from pathlib import Path
# test_bids_read_path=Path("/path/to/BIDS_out")
from _env import test_bids_write_path

bids_path = test_bids_write_path

shutil.rmtree(bids_path, ignore_errors=True)

dataset=BIDSDataset(
    bids_path,
    description=BIDSDatasetDescription(
        name="Test BID clinicaio", 
        version=BIDSVersion("1.10.0"),
        dataset_type=BIDSDatasetType.RAW,
    ),
)

subject1 = dataset.add_subject(
    id=SubjectId("sub-0001"),
    info=SubjectInfo(other_fields={
        "subj1": 345,
        "subj2": "texte",
        "subj3": None,
    }),
)

session1 = subject1.add_session(
    id=SessionId("ses-N1"),
    info=SessionInfo(
        acquisition_time="2026-04-22T01:02:03Z",
        pathology=None,
        other_fields={
            "foo": 37,
            "bar": 3929,
            "baz": "texte",
        },
    ),
)
session2 = subject1.add_session(
    id=SessionId("ses-N2"),
    info=SessionInfo(
        acquisition_time="2026-04-20T11:12:13Z",
        pathology=None,
        other_fields={
            "foo": 37,
            "bar": 3929,
            "baz": "texte",
        },
    ),
)

dataset.write_dataset()
with dataset.write_root_file("README", write_binary=False) as readme:
    print("README content",file=readme)

with session1.write_images() as images_writer:
    image1 = images_writer.write_image(
        data_type=DataType.ANAT,
        nifti_extension=FileExtension.NII_GZ,
        entities=Entities.from_str("trc-18FFDG_task-rest"),
        suffix=Suffix("T1w"),
        scan_info=ImageScanInfo(other_fields={
            "abc": 123,
            "cdf": "img scan text",
        }),
    )
    f = open(image1.get_nifti_image_path(), "x")
    print("PLACEHOLDER NIFTI", file=f)

    f = open(image1.get_image_companion_file_path(FileExtension.JSON), "x")
    json.dump(obj={
        "name": "test",
        "size": 3092,
    }, fp=f)