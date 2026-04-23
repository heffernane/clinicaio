from clinicaio.dataset import *

import shutil

# IN _env.py:
#
# from pathlib import Path
# test_bids_read_path=Path("/path/to/BIDS_out")
from ._env import test_bids_write_path

assert(False, "code not working or done yet here")

bids_path = test_bids_write_path

shutil.rmtree(bids_path, ignore_errors=True)

session1 = Session(
    id=SessionId("ses-N1"),
    info=SessionInfo(
        acquisition_time="2026-04-22T01:02:03Z",
        pathology=None,
        other_fields={
            "foo": 37,
            "bar": 3929,
            "baz": "texte",
        }
    )
)
session2 = Session(
    id=SessionId("ses-N2"),
    info=SessionInfo(
        acquisition_time="2026-04-20T11:12:13Z",
        pathology=None,
        other_fields={
            "foo": 37,
            "bar": 3929,
            "baz": "texte",
        }
    )
)

subject1 = Subject(
    sessions={session.id: session for session in [session1, session2]},
    id=SubjectId("sub-0001"),
    info=SubjectInfo(other_fields={
        "subj1": 345,
        "subj2": "texte",
        "subj3": None,
    })
)

dataset=BIDSDataset(
    bids_path,
    description=BIDSDatasetDescription(
        name="Test BID clinicaio", 
        version=BIDSVersion("1.10.0"),
        dataset_type=BIDSDatasetType.RAW,
    ),
    subjects={subject.id: subject for subject in [subject1]},
)


dataset.write_dataset()
with dataset.write_root_file("README", write_binary=False) as readme:
    print("README content",file=readme)

with session1.write_images(dataset, subject1) as images_writer:
    image1 = Image(
        nifti_extension=FileExtension.NII_GZ,
        entities=Entities.from_str("trc-18FFDG_task-rest"),
        suffix=Suffix("T1w"),
        scan_info=ImageScanInfo()
    )

"""
    with images_writer.write_image(DataType.ANAT, image1) as img:

open(, mode="x")
    """