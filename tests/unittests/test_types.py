from clinicaio.types import *

import pytest
from re import escape

def test_ids():
    with pytest.raises(BIDSException, match="BIDS subject ID 001 must start with sub-"):
        SubjectId("001")
    with pytest.raises(BIDSException, match="BIDS session ID M000 must start with ses-"):
        SessionId("M000")
    
    with pytest.raises(BIDSException, match="BIDS label can't be empty"):
        SubjectId("sub-")
    with pytest.raises(BIDSException, match="BIDS label can't be empty"):
        SessionId("ses-")

    assert(SubjectId("sub-123").__str__() == "sub-123")
    assert(SessionId("ses-123").__str__() == "ses-123")

    with pytest.raises(BIDSException, match=escape("BIDS subject id sub-é had invalid label (in sub-<label>): BIDS label é must be all [a-zA-Z0-9] characters")):
        SubjectId("sub-é")
    with pytest.raises(BIDSException, match=escape("BIDS session id ses-é had invalid label (in ses-<label>): BIDS label é must be all [a-zA-Z0-9] characters")):
        SessionId("ses-é")


def test_enum_to_str():
    # We test this notably because while StrEnum has the correct behavior
    # when we inherit from it, class Foo(str, Enum) does not (in some
    # Python versions)
    assert(BIDSDatasetType.RAW.__str__() == "raw")
    assert(DataType.PHENOTYPE.__str__() == "phenotype")
    assert(FileExtension.NII_GZ.__str__() == "nii.gz")

def test_wrappers_to_str():
    assert(Suffix("sfx").__str__() == "sfx")
    assert(BIDSVersion("1.10.0").__str__() == "1.10.0")
    assert(Label("txt").__str__() == "txt")