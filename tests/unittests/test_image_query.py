from re import escape

import pytest

from clinicaio.entities import Entities, EntityKey, EntityValue
from clinicaio.image_query import ImageQuery
from clinicaio.types import BIDSException, DataType, SessionId, SubjectId, Suffix

# For convenience the ImageQuery constructor allows a variety of types for
# its arguments, in a Python fashion. These tests ensure that each supported
# input types are well supported.

# Subjects query filter
def test_subject_str_to_id():
    query = ImageQuery(subjects=["sub-1"])
    assert(type(query.subjects) == set)
    assert(type(query.subjects) != list)
    assert(len(query.subjects) == 1)
    assert(type(list(query.subjects)[0]) == SubjectId)
    assert(type(list(query.subjects)[0]) != str)

def test_direct_subject_id_class():
    query = ImageQuery(subjects=[SubjectId("sub-1")])
    assert(type(query.subjects) == set)
    assert(type(query.subjects) != list)
    assert(len(query.subjects) == 1)
    assert(type(list(query.subjects)[0]) == SubjectId)
    assert(type(list(query.subjects)[0]) != str)

def test_mixed_subject_str_and_id_class():
    query = ImageQuery(subjects=[SubjectId("sub-1"), "sub-2", SubjectId("sub-3"), "sub-4", "sub-5"])
    assert(type(query.subjects) == set)
    assert(type(query.subjects) != list)
    assert(len(query.subjects) == 5)
    i = 0
    for subject_id in query.subjects:
        assert(type(subject_id) == SubjectId)
        assert(type(subject_id) != str)
        i += 1
    assert(i == len(query.subjects))

    assert(sorted(map(lambda id: f"{id}", query.subjects)) == ["sub-1", "sub-2", "sub-3", "sub-4", "sub-5"])

def test_mixed_subject_str_and_id_class_in_set():
    # Note the use of a set here instead of a list
    query = ImageQuery(subjects={SubjectId("sub-1"), "sub-2", SubjectId("sub-3"), "sub-4", "sub-5"})
    assert(type(query.subjects) == set)
    assert(type(query.subjects) != list)
    assert(len(query.subjects) == 5)
    i = 0
    for subject_id in query.subjects:
        assert(type(subject_id) == SubjectId)
        assert(type(subject_id) != str)
        i += 1
    assert(i == len(query.subjects))

    assert(sorted(map(lambda id: f"{id}", query.subjects)) == ["sub-1", "sub-2", "sub-3", "sub-4", "sub-5"])

def test_duplicated_subject_ids():
    query = ImageQuery(subjects=[SubjectId("sub-1"), "sub-2", SubjectId("sub-2"), "sub-4", "sub-2"])
    assert(type(query.subjects) == set)
    assert(type(query.subjects) != list)
    assert(len(query.subjects) == 3)
    i = 0
    for subject_id in query.subjects:
        assert(type(subject_id) == SubjectId)
        assert(type(subject_id) != str)
        i += 1
    assert(i == len(query.subjects))

    assert(sorted(map(lambda id: f"{id}", query.subjects)) == ["sub-1", "sub-2", "sub-4"])


# Sessions query filter
def test_session_str_to_id():
    query = ImageQuery(sessions=["ses-1"])
    assert(type(query.sessions) == set)
    assert(type(query.sessions) != list)
    assert(len(query.sessions) == 1)
    assert(type(list(query.sessions)[0]) == SessionId)
    assert(type(list(query.sessions)[0]) != str)

def test_direct_session_id_class():
    query = ImageQuery(sessions=[SessionId("ses-1")])
    assert(type(query.sessions) == set)
    assert(type(query.sessions) != list)
    assert(len(query.sessions) == 1)
    assert(type(list(query.sessions)[0]) == SessionId)
    assert(type(list(query.sessions)[0]) != str)

def test_mixed_session_str_and_id_class():
    query = ImageQuery(sessions=[SessionId("ses-1"), "ses-2", SessionId("ses-3"), "ses-4", "ses-5"])
    assert(type(query.sessions) == set)
    assert(type(query.sessions) != list)
    assert(len(query.sessions) == 5)
    i = 0
    for session_id in query.sessions:
        assert(type(session_id) == SessionId)
        assert(type(session_id) != str)
        i += 1
    assert(i == len(query.sessions))

    assert(sorted(map(lambda id: f"{id}", query.sessions)) == ["ses-1", "ses-2", "ses-3", "ses-4", "ses-5"])

def test_mixed_session_str_and_id_class_in_set():
    # Note the use of a set here instead of a list
    query = ImageQuery(sessions={SessionId("ses-1"), "ses-2", SessionId("ses-3"), "ses-4", "ses-5"})
    assert(type(query.sessions) == set)
    assert(type(query.sessions) != list)
    assert(len(query.sessions) == 5)
    i = 0
    for session_id in query.sessions:
        assert(type(session_id) == SessionId)
        assert(type(session_id) != str)
        i += 1
    assert(i == len(query.sessions))

    assert(sorted(map(lambda id: f"{id}", query.sessions)) == ["ses-1", "ses-2", "ses-3", "ses-4", "ses-5"])

def test_duplicated_session_ids():
    query = ImageQuery(sessions=[SessionId("ses-1"), "ses-2", SessionId("ses-2"), "ses-4", "ses-2"])
    assert(type(query.sessions) == set)
    assert(type(query.sessions) != list)
    assert(len(query.sessions) == 3)
    i = 0
    for session_id in query.sessions:
        assert(type(session_id) == SessionId)
        assert(type(session_id) != str)
        i += 1
    assert(i == len(query.sessions))

    assert(sorted(map(lambda id: f"{id}", query.sessions)) == ["ses-1", "ses-2", "ses-4"])


# Data type query filter
def test_data_type():
    assert(ImageQuery(data_type=None).data_type is None)
    assert(ImageQuery(data_type=DataType.PET).data_type == DataType.PET)
    assert(ImageQuery(data_type=DataType("pet")).data_type == DataType.PET)

    with pytest.raises(BIDSException, match=escape("invalid type <class 'str'> for data_type argument")):
        ImageQuery(data_type="pet") # type: ignore


# Entities query filter
def test_entities_class():
    entities = Entities.from_str("trc-18FFDG_task-rest")
    query = ImageQuery(entities=entities)
    assert(len(entities) == 2)
    assert(len(query.entities) == len(entities))
    assert(query.entities.contains_all(entities))
    assert(query.entities == entities)

def test_entities_str():
    s = "trc-18FFDG_task-rest"
    query = ImageQuery(entities=s)
    entities = Entities.from_str(s)
    assert(len(entities) == 2)
    assert(len(query.entities) == len(entities))
    assert(query.entities.contains_all(entities))
    assert(query.entities == entities)

def test_entities_str_list():
    l = ["trc-18FFDG", "task-rest"]
    query = ImageQuery(entities=l)
    entities = Entities.from_str_list(l)
    assert(len(entities) == 2)
    assert(len(query.entities) == len(entities))
    assert(query.entities.contains_all(entities))
    assert(query.entities == entities)

def test_entities_invalid_str_list():
    with pytest.raises(BIDSException, match=escape("found non str entity in list[str] entities parameter for image query")):
        ImageQuery(entities=["task-rest", 3]) # type: ignore

def test_entities_str_dict():
    entities = Entities.from_str("aaa-1_bbb-2_ccc-3")
    query = ImageQuery(entities={"aaa": "1", "bbb": "2", "ccc": "3"})
    assert(len(entities) == 3)
    assert(len(query.entities) == len(entities))
    assert(query.entities.contains_all(entities))
    assert(query.entities == entities)

def test_entities_classes_dict():
    entities = Entities.from_str("aaa-1_bbb-2_ccc-3")
    query = ImageQuery(entities={
        EntityKey("aaa"): EntityValue("1"), 
        EntityKey("bbb"): EntityValue("2"), 
        EntityKey("ccc"): EntityValue("3"),
    })
    assert(len(entities) == 3)
    assert(len(query.entities) == len(entities))
    assert(query.entities.contains_all(entities))
    assert(query.entities == entities)

def test_entities_mixed_dict():
    s = "aaa-1_bbb-2_ccc-3_ddd-4"
    entities = Entities.from_str(s)
    query = ImageQuery(entities={
        "aaa": EntityValue("1"), 
        EntityKey("bbb"): "2", 
        EntityKey("ccc"): EntityValue("3"),
        "ddd": "4",
    })
    assert(len(entities) == 4)
    assert(len(query.entities) == len(entities))
    assert(query.entities.contains_all(entities))
    assert(query.entities == entities)

    assert(entities.__str__() == s)

def test_entities_invalid_type():
    with pytest.raises(BIDSException, match=escape("invalid type <class 'int'> for ImageQuery entities 3")):
        ImageQuery(entities=3) # type: ignore

# Suffix query filter
def test_suffix_none():
    assert(ImageQuery(suffix=None).suffix is None)

def test_suffix_class():
    s = "sfx"
    suffix = Suffix(s)
    query = ImageQuery(suffix=suffix)
    assert(query.suffix == suffix)
    assert(query.suffix.__str__() == s)

def test_suffix_str():
    s = "sfx"
    query = ImageQuery(suffix=s)
    suffix = Suffix(s)
    assert(query.suffix == suffix)
    assert(query.suffix.__str__() == s)