from re import escape

import pytest
from packaging.version import Version

from clinicaio.dataset_description import BIDSDatasetType
from clinicaio.types import (
    BIDSException,
    DataType,
    FileExtension,
    Label,
    SessionId,
    SubjectId,
    Suffix,
)


def test_ids_missing_prefix():
    with pytest.raises(BIDSException, match="BIDS subject ID 001 must start with sub-"):
        SubjectId("001")
    with pytest.raises(
        BIDSException, match="BIDS session ID M000 must start with ses-"
    ):
        SessionId("M000")


def test_ids_prefix_with_empty_label():
    with pytest.raises(
        BIDSException,
        match=escape(
            "BIDS subject id sub- had invalid label (in sub-<label>): BIDS label can't be empty"
        ),
    ):
        SubjectId("sub-")
    with pytest.raises(
        BIDSException,
        match=escape(
            "BIDS session id ses- had invalid label (in ses-<label>): BIDS label can't be empty"
        ),
    ):
        SessionId("ses-")


def test_ids_to_str():
    assert str(SubjectId("sub-123")) == "sub-123"
    assert str(SessionId("ses-123")) == "ses-123"


def test_ids_non_alnum_chars():
    with pytest.raises(
        BIDSException,
        match=escape(
            "BIDS subject id sub-é had invalid label (in sub-<label>): BIDS label é must be all [a-zA-Z0-9] characters"
        ),
    ):
        SubjectId("sub-é")
    with pytest.raises(
        BIDSException,
        match=escape(
            "BIDS session id ses-é had invalid label (in ses-<label>): BIDS label é must be all [a-zA-Z0-9] characters"
        ),
    ):
        SessionId("ses-é")


def test_ids_hash_eq():
    sub1 = SubjectId("sub-01")
    sub2 = SubjectId("sub-02")
    sub1_same = SubjectId("sub-01")
    # The label part of sub-<label> is not treated particularily with regards
    # to fully integer labels.
    sub1_same_but_different = SubjectId("sub-1")

    assert sub1.__hash__() == sub1_same.__hash__()
    assert sub1 == sub1_same
    assert sub1.__hash__() != sub2.__hash__()
    assert sub1.__hash__() != sub1_same_but_different.__hash__()
    assert sub1 != sub1_same_but_different
    # In case __ne__() is broken
    assert not (sub1 == sub2)
    assert sub1 != sub2

    ses1 = SessionId("ses-01")
    ses2 = SessionId("ses-02")
    ses1_same = SessionId("ses-01")
    # The label part of ses-<label> is not treated particularily with regards
    # to fully integer labels.
    ses1_same_but_different = SessionId("ses-1")

    assert ses1.__hash__() == ses1_same.__hash__()
    assert ses1 == ses1_same
    assert ses1.__hash__() != ses2.__hash__()
    assert ses1.__hash__() != ses1_same_but_different.__hash__()
    assert ses1 != ses1_same_but_different
    # In case __ne__() is broken
    assert not (ses1 == ses2)
    assert ses1 != ses2


def test_enum_to_str():
    # We test this notably because while StrEnum has the correct behavior
    # when we inherit from it, class Foo(str, Enum) does not (in some
    # Python versions). str(A.FOO) outputs A.FOO in Python 3.10 but f"{A.FOO}" outputs foo
    # (as f"..." goes through __format__() which seems to have a different implementation)
    assert str(BIDSDatasetType.RAW) == "raw"
    assert str(DataType.PHENOTYPE) == "phenotype"
    assert str(FileExtension.NII_GZ) == "nii.gz"
    assert f"{BIDSDatasetType.RAW}" == "raw"
    assert f"{DataType.PHENOTYPE}" == "phenotype"
    assert f"{FileExtension.NII_GZ}" == "nii.gz"


def test_wrappers_to_str():
    assert str(Suffix("sfx")) == "sfx"
    assert str(Version("1.10.0")) == "1.10.0"
    assert str(Label("txt")) == "txt"
