from re import escape
from typing import Any

import pytest

from clinicaio.entities import Entities, EntityKey, EntityValue
from clinicaio.image_query import ImageQuery
from clinicaio.types import BIDSException, DataType, SessionId, SubjectId

# For convenience the ImageQuery constructor allows a variety of types for
# its arguments, in a Python fashion. These tests ensure that each supported
# input types are well supported.


# Subjects query filter
def test_subject_str_to_id():
    query = ImageQuery(subjects=["sub-1"])
    assert type(query.subjects) == set
    assert type(query.subjects) != list
    assert len(query.subjects) == 1

    assert type(list(query.subjects)[0]) == str


def test_direct_subject_id_class():
    query = ImageQuery(subjects=["sub-1"])
    assert type(query.subjects) == set
    assert type(query.subjects) != list
    assert len(query.subjects) == 1
    assert type(list(query.subjects)[0]) == str


def test_mixed_subject_str_and_id_class():
    query = ImageQuery(subjects=["sub-1", "sub-2", "sub-3", "sub-4", "sub-5"])
    assert type(query.subjects) == set
    assert type(query.subjects) != list
    assert len(query.subjects) == 5
    i = 0
    for subject_id in query.subjects:
        assert type(subject_id) == str
        i += 1
    assert i == len(query.subjects)

    assert sorted(list(query.subjects)) == [
        "sub-1",
        "sub-2",
        "sub-3",
        "sub-4",
        "sub-5",
    ]


def test_mixed_subject_str_and_id_class_in_set():
    # Note the use of a set here instead of a list
    query = ImageQuery(subjects={"sub-1", "sub-2", "sub-3", "sub-4", "sub-5"})
    assert type(query.subjects) == set
    assert type(query.subjects) != list
    assert len(query.subjects) == 5
    i = 0
    for subject_id in query.subjects:
        assert type(subject_id) == str
        i += 1
    assert i == len(query.subjects)

    assert sorted(list(query.subjects)) == [
        "sub-1",
        "sub-2",
        "sub-3",
        "sub-4",
        "sub-5",
    ]


def test_duplicated_subject_ids():
    query = ImageQuery(subjects=["sub-1", "sub-2", "sub-2", "sub-4", "sub-2"])
    assert type(query.subjects) == set
    assert type(query.subjects) != list
    assert len(query.subjects) == 3
    i = 0
    for subject_id in query.subjects:
        assert type(subject_id) == str
        i += 1
    assert i == len(query.subjects)

    assert sorted(list(query.subjects)) == [
        "sub-1",
        "sub-2",
        "sub-4",
    ]


# Sessions query filter
def test_session_str_to_id():
    query = ImageQuery(sessions=["ses-1"])
    assert type(query.sessions) == set
    assert type(query.sessions) != list
    assert len(query.sessions) == 1
    assert type(list(query.sessions)[0]) == str


def test_direct_session_id_class():
    query = ImageQuery(sessions=["ses-1"])
    assert type(query.sessions) == set
    assert type(query.sessions) != list
    assert len(query.sessions) == 1
    assert type(list(query.sessions)[0]) == str


def test_mixed_session_str_and_id_class():
    query = ImageQuery(sessions=["ses-1", "ses-2", "ses-3", "ses-4", "ses-5"])
    assert type(query.sessions) == set
    assert type(query.sessions) != list
    assert len(query.sessions) == 5
    i = 0
    for session_id in query.sessions:
        assert type(session_id) == str
        i += 1
    assert i == len(query.sessions)

    assert sorted(list(query.sessions)) == [
        "ses-1",
        "ses-2",
        "ses-3",
        "ses-4",
        "ses-5",
    ]


def test_mixed_session_str_and_id_class_in_set():
    # Note the use of a set here instead of a list
    query = ImageQuery(sessions={"ses-1", "ses-2", "ses-3", "ses-4", "ses-5"})
    assert type(query.sessions) == set
    assert type(query.sessions) != list
    assert len(query.sessions) == 5
    i = 0
    for session_id in query.sessions:
        assert type(session_id) == str
        i += 1
    assert i == len(query.sessions)

    assert sorted(list(query.sessions)) == [
        "ses-1",
        "ses-2",
        "ses-3",
        "ses-4",
        "ses-5",
    ]


def test_duplicated_session_ids():
    query = ImageQuery(sessions=["ses-1", "ses-2", "ses-2", "ses-4", "ses-2"])
    assert type(query.sessions) == set
    assert type(query.sessions) != list
    assert len(query.sessions) == 3
    i = 0
    for session_id in query.sessions:
        assert type(session_id) == str
        i += 1
    assert i == len(query.sessions)

    assert sorted(list(query.sessions)) == [
        "ses-1",
        "ses-2",
        "ses-4",
    ]


# Data type query filter
def test_data_type():
    assert ImageQuery(data_type=None).data_type is None
    assert ImageQuery(data_type=DataType.PET).data_type == DataType.PET
    assert ImageQuery(data_type=DataType("pet")).data_type == DataType.PET
    assert ImageQuery(data_type="pet").data_type == DataType.PET

    with pytest.raises(
        TypeError, match=escape("invalid type <class 'int'> for data_type argument")
    ):
        ImageQuery(data_type=3)  # type: ignore


# Entities query filter
def test_entities_class():
    entities = Entities.from_str("trc-18FFDG_task-rest")
    query = ImageQuery(entities=entities)
    assert len(entities) == 2
    assert len(query.entities) == len(entities)
    assert query.entities.contains_all(entities)
    assert query.entities == entities


def test_entities_str():
    s = "trc-18FFDG_task-rest"
    query = ImageQuery(entities=s)
    entities = Entities.from_str(s)
    assert len(entities) == 2
    assert len(query.entities) == len(entities)
    assert query.entities.contains_all(entities)
    assert query.entities == entities


def test_entities_str_list():
    entities_list = ["trc-18FFDG", "task-rest"]
    query = ImageQuery(entities=entities_list)
    entities = Entities.from_str_list(entities_list)
    assert len(entities) == 2
    assert len(query.entities) == len(entities)
    assert query.entities.contains_all(entities)
    assert query.entities == entities


def test_entities_invalid_str_list():
    with pytest.raises(
        TypeError,
        match=escape("found non str entity in list[str] entities parameter"),
    ):
        ImageQuery(entities=["task-rest", 3])  # type: ignore


def test_entities_str_dict():
    entities = Entities.from_str("aaa-1_bbb-2_ccc-3")
    query = ImageQuery(entities={"aaa": "1", "bbb": "2", "ccc": "3"})
    assert len(entities) == 3
    assert len(query.entities) == len(entities)
    assert query.entities.contains_all(entities)
    assert query.entities == entities


def test_entities_classes_dict():
    entities = Entities.from_str("aaa-1_bbb-2_ccc-3")
    query = ImageQuery(
        entities={
            EntityKey("aaa"): EntityValue("1"),
            EntityKey("bbb"): EntityValue("2"),
            EntityKey("ccc"): EntityValue("3"),
        }
    )
    assert len(entities) == 3
    assert len(query.entities) == len(entities)
    assert query.entities.contains_all(entities)
    assert query.entities == entities


def test_entities_mixed_dict():
    s = "aaa-1_bbb-2_ccc-3_ddd-4"
    entities = Entities.from_str(s)
    query = ImageQuery(
        entities={
            "aaa": EntityValue("1"),
            EntityKey("bbb"): "2",
            EntityKey("ccc"): EntityValue("3"),
            "ddd": "4",
        }
    )
    assert len(entities) == 4
    assert len(query.entities) == len(entities)
    assert query.entities.contains_all(entities)
    assert query.entities == entities

    assert str(entities) == s


def test_entities_invalid_type():
    with pytest.raises(
        TypeError, match=escape("invalid input type <class 'int'> for entities 3")
    ):
        ImageQuery(entities=3)  # type: ignore


# Suffix query filter
def test_suffix_none():
    assert ImageQuery(suffix=None).suffix is None


def test_suffix_class():
    suffix = "sfx"
    query = ImageQuery(suffix=suffix)
    assert query.suffix == suffix
    assert str(query.suffix) == suffix


def test_suffix_str():
    suffix = "sfx"
    query = ImageQuery(suffix=suffix)
    assert query.suffix == suffix
    assert str(query.suffix) == suffix


def test_suffix_wildcard():
    assert ImageQuery(suffix="magnitude*").suffix == "magnitude*"


@pytest.mark.parametrize(
    ["input_sub_ses", "validated_sub_ses"],
    [
        ([], {}),
        ({}, {}),
        ([("sub-1", "ses-A")], {"sub-1": {"ses-A"}}),
        (
            [("sub-1", "ses-A"), ("sub-2", "ses-A")],
            {"sub-1": {"ses-A"}, "sub-2": {"ses-A"}},
        ),
        (
            [
                ("sub-1", "ses-A"),
                ("sub-1", "ses-B"),
                ("sub-2", "ses-A"),
                ("sub-1", "ses-C"),
            ],
            {
                "sub-1": {"ses-A", "ses-B", "ses-C"},
                "sub-2": {"ses-A"},
            },
        ),
        # NOTE: it is debatable whether having duplicated subject/session pairs should be
        # treated as an error. For now it's not the case but it may make sense, it's just
        # that it's not fundamentally harmful to accept them and it may be
        # more convenient to accept them than having to make sure they're
        # not duplicated in the calling-code.
        ([("sub-1", "ses-A"), ("sub-1", "ses-A")], {"sub-1": {"ses-A"}}),
        # Just passthrough for dict[id, set[id]]
        (
            {
                "sub-1": {"ses-A", "ses-B", "ses-C"},
                "sub-2": {"ses-A"},
            },
            {
                "sub-1": {"ses-A", "ses-B", "ses-C"},
                "sub-2": {"ses-A"},
            },
        ),
    ],
)
def test_sub_ses_valid_forms(
    input_sub_ses: Any, validated_sub_ses: dict[SubjectId, set[SessionId]]
):
    assert ImageQuery(sub_ses=input_sub_ses).sub_ses == validated_sub_ses


@pytest.mark.parametrize(
    ["input_sub_ses", "err_msg"],
    [
        # Dict directly with session ID as value instead of set of session IDs (even if only one is provided)
        (
            {"sub-1": "ses-A"},
            "invalid subject/session pair(s) ({'sub-1': 'ses-A'}): field \"sub-1\": Input should be a valid set",
        ),
        # invalid subject ID in list-form
        (
            [("sub1", "ses-A")],
            "invalid subject/session pair(s) ({'sub1': {'ses-A'}}): field \"sub1\": String should match pattern '^sub-[a-zA-Z0-9]+$'",
        ),
        # invalid session ID in list-form
        (
            [("sub-1", "sesA")],
            "invalid subject/session pair(s) ({'sub-1': {'sesA'}}): field \"sub-1\": String should match pattern '^ses-[a-zA-Z0-9]+$'",
        ),
        # invalid subject ID in dict-form
        (
            {"sub1": {"ses-A"}},
            "invalid subject/session pair(s) ({'sub1': {'ses-A'}}): field \"sub1\": String should match pattern '^sub-[a-zA-Z0-9]+$'",
        ),
        # invalid session ID in dict-form
        (
            {"sub-1": {"sesA"}},
            "invalid subject/session pair(s) ({'sub-1': {'sesA'}}): field \"sub-1\": String should match pattern '^ses-[a-zA-Z0-9]+$'",
        ),
    ],
)
def test_invalid_sub_ses(input_sub_ses: Any, err_msg: str):
    with pytest.raises(BIDSException, match=escape(err_msg)):
        ImageQuery(sub_ses=input_sub_ses)
