from re import escape
from typing import Any

import pytest
from packaging.version import Version
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticError

from clinicaio.dataset_description import BIDSDatasetType
from clinicaio.types import (
    BIDSDataType,
    BIDSException,
    FileExtension,
    Label,
    SessionId,
    SubjectId,
    Suffix,
)


@pytest.mark.parametrize(
    ["id_type", "id", "err_msg"],
    [
        (SubjectId, "001", "bids: String should match pattern '^sub-[a-zA-Z0-9]+$'"),
        (SessionId, "M000", "bids: String should match pattern '^ses-[a-zA-Z0-9]+$'"),
    ],
)
def test_ids_missing_prefix(id_type: type, id: str, err_msg: str):
    with pytest.raises(BIDSException, match=escape(err_msg)):
        try:
            TypeAdapter(id_type).validate_python(id)
        except PydanticError as e:
            raise BIDSException._from_pydantic("bids", e)


@pytest.mark.parametrize(
    ["id_type", "id", "err_msg"],
    [
        (SubjectId, "sub-", "bids: String should match pattern '^sub-[a-zA-Z0-9]+$'"),
        (SessionId, "ses-", "bids: String should match pattern '^ses-[a-zA-Z0-9]+$'"),
    ],
)
def test_ids_prefix_with_empty_label(id_type: type, id: str, err_msg: str):
    with pytest.raises(
        BIDSException,
        match=escape(err_msg),
    ):
        try:
            TypeAdapter(id_type).validate_python(id)
        except PydanticError as e:
            raise BIDSException._from_pydantic("bids", e)


@pytest.mark.parametrize(
    ["id_type", "id", "err_msg"],
    [
        (SubjectId, "sub-é", "bids: String should match pattern '^sub-[a-zA-Z0-9]+$'"),
        (SessionId, "ses-é", "bids: String should match pattern '^ses-[a-zA-Z0-9]+$'"),
    ],
)
def test_ids_non_alnum_chars(id_type: type, id: str, err_msg: str):
    with pytest.raises(
        BIDSException,
        match=escape(err_msg),
    ):
        try:
            TypeAdapter(id_type).validate_python(id)
        except PydanticError as e:
            raise BIDSException._from_pydantic("bids", e)


@pytest.mark.parametrize(
    ["id_class", "prefix"],
    [
        (SubjectId, "sub-"),
        (SessionId, "ses-"),
    ],
)
def test_ids_hash_eq(id_class: type, prefix: str):
    id1 = TypeAdapter(id_class).validate_python(f"{prefix}01")
    id2 = TypeAdapter(id_class).validate_python(f"{prefix}02")
    id1_same = TypeAdapter(id_class).validate_python(f"{prefix}01")
    # The label part of <prefix><label> is not treated particularly with regards
    # to fully integer labels.
    id1_same_but_different = TypeAdapter(id_class).validate_python(f"{prefix}1")

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
        (BIDSDataType.PHENOTYPE, "phenotype"),
        (FileExtension.NII_GZ, "nii.gz"),
    ],
)
def test_enum_to_str(enum_value: Any, string_value: str):
    # We test this notably because while StrEnum has the correct behavior
    # when we inherit from it, class Foo(str, Enum) does not (in some
    # Python versions). str(A.FOO) outputs A.FOO in Python 3.10 but f"{A.FOO}" outputs foo
    # (as f"..." goes through __format__() which seems to have a different implementation)
    assert str(enum_value) == string_value
    assert f"{enum_value}" == string_value


def test_version_to_str():
    assert str(Version("1.10.0")) == "1.10.0"


@pytest.mark.parametrize(
    ["wrapper_type", "string"],
    [
        (Suffix, "sfx"),
        (SubjectId, "sub-123"),
        (SessionId, "ses-123"),
    ],
)
def test_wrappers_to_str(wrapper_type: type, string: str):
    assert TypeAdapter(wrapper_type).validate_python(string) == string


def test_file_extension_is_nifti():
    assert FileExtension.NII.is_nifti()
    assert FileExtension.NII_GZ.is_nifti()
    assert len([ext for ext in iter(FileExtension) if ext.is_nifti()]) == 2
    assert not FileExtension.JSON.is_nifti()


@pytest.mark.parametrize(
    ["enum_type"],
    [
        (BIDSDataType,),
        (FileExtension,),
    ],
)
def test_enum_repr(enum_type: Any):
    for v in iter(enum_type):
        assert repr(v) == f"'{v}'"


def test_empty_label():
    with pytest.raises(ValueError, match=escape("BIDS label can't be empty")):
        Label("")


def test_label_alpha_non_ascii():
    with pytest.raises(
        ValueError, match=escape("BIDS label aéa must be all [a-zA-Z0-9] characters")
    ):
        Label("aéa")


def test_label_non_alnum():
    with pytest.raises(
        ValueError,
        match=escape("BIDS label bbb33^-aa must be all [a-zA-Z0-9] characters"),
    ):
        Label("bbb33^-aa")
