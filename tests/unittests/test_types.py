from re import escape
from typing import Any

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


@pytest.mark.parametrize(
    ["id_class", "value"],
    [
        (SubjectId, "sub-123"),
        (SessionId, "ses-123"),
    ]
)
def test_ids_to_str(id_class: type, value: str):
    assert str(id_class(value)) == value


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


@pytest.mark.parametrize(
    ["id_class", "prefix"],
    [
        (SubjectId, "sub-"),
        (SessionId, "ses-"),
    ]
)
def test_ids_hash_eq(id_class: type, prefix: str):
    id1 = id_class(f"{prefix}01")
    id2 = id_class(f"{prefix}02")
    id1_same = id_class(f"{prefix}01")
    # The label part of <prefix><label> is not treated particularily with regards
    # to fully integer labels.
    id1_same_but_different = id_class(f"{prefix}1")

    assert id1.__hash__() == id1_same.__hash__()
    assert id1 == id1_same
    assert id1.__hash__() != id2.__hash__()
    assert id1.__hash__() != id1_same_but_different.__hash__()
    assert id1 != id1_same_but_different
    # In case __ne__() is broken
    assert not (id1 == id2)
    assert id1 != id2


@pytest.mark.parametrize(
    ["enum_value", "string_value"],
    [
        (BIDSDatasetType.RAW, "raw"),
        (DataType.PHENOTYPE, "phenotype"),
        (FileExtension.NII_GZ, "nii.gz"),
    ]
)
def test_enum_to_str(enum_value: Any, string_value: str):
    # We test this notably because while StrEnum has the correct behavior
    # when we inherit from it, class Foo(str, Enum) does not (in some
    # Python versions). str(A.FOO) outputs A.FOO in Python 3.10 but f"{A.FOO}" outputs foo
    # (as f"..." goes through __format__() which seems to have a different implementation)
    assert str(enum_value) == string_value
    assert f"{enum_value}" == string_value


@pytest.mark.parametrize(
    ["wrapper_type", "string"],
    [
        (Suffix, "sfx"),
        (Version, "1.10.0"),
        (Label, "txt")
    ]
)
def test_wrappers_to_str(wrapper_type: type, string: str):
    assert str(wrapper_type(string)) == string