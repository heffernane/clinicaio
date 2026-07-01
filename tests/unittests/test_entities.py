import itertools
from re import escape

import pytest

from clinicaio.entities import Entities, EntityKey, EntityValue
from clinicaio.types import BIDSException


def test_from_str():
    entities = Entities.from_str("trc-18FFDG_task-rest")
    assert len(entities) == 2
    assert entities.contains_entity(EntityKey("task"), EntityValue("rest"))
    assert not entities.contains_entity(EntityKey("task"), EntityValue("restt"))
    assert entities.contains_entity(EntityKey("trc"), EntityValue("18FFDG"))
    assert not entities.contains_entity(EntityKey("trc"), EntityValue("1"))
    assert not entities.contains_entity(EntityKey("trc"), EntityValue("CPIB"))
    assert not entities.contains_entity(EntityKey("task"), EntityValue("18FFDG"))

    # NOTE: the order of the entities must be kept from insertion/creation order.
    assert str(entities) == "trc-18FFDG_task-rest"


def test_from_str_list():
    entities_list = ["trc-18FFDG", "task-rest"]
    entities = Entities.from_str_list(entities_list)
    assert len(entities) == 2
    assert entities.contains_entity(EntityKey("task"), EntityValue("rest"))
    assert not entities.contains_entity(EntityKey("task"), EntityValue("restt"))
    assert entities.contains_entity(EntityKey("trc"), EntityValue("18FFDG"))
    assert not entities.contains_entity(EntityKey("trc"), EntityValue("1"))
    assert not entities.contains_entity(EntityKey("trc"), EntityValue("CPIB"))
    assert not entities.contains_entity(EntityKey("task"), EntityValue("18FFDG"))


def test_from_invalid_str_list():
    with pytest.raises(
        BIDSException,
        match=escape("found non str entity in list[str] entities parameter"),
    ):
        Entities.from_str_list(["task-rest", 3])  # type: ignore


def test_from_str_list_no_separator():
    str_list = ["task", "rest"]

    with pytest.raises(
        BIDSException,
        match=escape(
            f"found entities list {str_list} that had an element without a - separator"
        ),
    ):
        Entities.from_str_list(str_list)


def test_from_str_dict():
    entities = Entities.from_dict({"aaa": "1", "bbb": "2", "ccc": "3"})
    assert len(entities) == 3

    assert str(entities) == "aaa-1_bbb-2_ccc-3"


def test_from_classes_dict():
    entities = Entities.from_dict(
        {
            EntityKey("aaa"): EntityValue("1"),
            EntityKey("bbb"): EntityValue("2"),
            EntityKey("ccc"): EntityValue("3"),
        }
    )
    assert len(entities) == 3

    assert str(entities) == "aaa-1_bbb-2_ccc-3"


def test_from_mixed_dict():
    entities = Entities.from_dict(
        {
            "aaa": EntityValue("1"),
            EntityKey("bbb"): "2",
            EntityKey("ccc"): EntityValue("3"),
            "ddd": "4",
        }
    )
    assert len(entities) == 4

    assert str(entities) == "aaa-1_bbb-2_ccc-3_ddd-4"


def test_contains_all():
    entities = Entities.from_dict({"aa": "11", "bb": "22", "cc": "33"})

    assert entities.contains_all(Entities.from_dict({"cc": "33", "aa": "11"}))
    entities = Entities.from_dict({"bb": "22", "cc": "33"})
    assert not entities.contains_all(Entities.from_dict({"cc": "33", "aa": "11"}))


def test_get_value():
    entities = Entities.from_dict({"aa": "11", "bb": "22", "cc": "33"})

    assert entities.get_value(EntityKey("dd")) is None
    assert str(entities.get_value(EntityKey("cc"))) == "33"


def test_repr():
    assert (
        repr(Entities.from_str("aa-11_bb-22_cc-33"))
        == 'Entities({"aa": "11", "bb": "22", "cc": "33"})'
    )


def test_from_any_none():
    assert len(Entities.from_any(None)) == 0
    assert str(Entities.from_any(None)) == ""


def test_from_any():
    for (ctr_a, input_a), (ctr_b, input_b) in itertools.pairwise(
        [
            (lambda v: v, Entities.from_dict({"aa": "11", "bb": "22"})),
            (Entities.from_str, "aa-11_bb-22"),
            (Entities.from_str_list, ["aa-11", "bb-22"]),
            (Entities.from_dict, {"aa": "11", "bb": "22"}),
        ]
    ):
        a: Entities = ctr_a(input_a)  # type: ignore
        b: Entities = ctr_b(input_b)  # type: ignore
        assert isinstance(a, Entities)
        assert isinstance(b, Entities)
        assert a == b
        assert str(a) == str(b)

        c: Entities = Entities.from_any(input_a)  # type: ignore
        assert c == a
        d: Entities = Entities.from_any(input_b)  # type: ignore
        assert d == b


def test_from_any_invalid_type():
    with pytest.raises(
        BIDSException, match=escape(f"invalid input type <class 'int'> for entities 3")
    ):
        Entities.from_any(3)  # type: ignore
