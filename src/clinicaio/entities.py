"""The entities key/value pairs that describe a given image in a dataset."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Optional, TypeAlias

from .types import Label


# not for sub- and ses- entities
class EntityKey(Label):
    def __hash__(self) -> int:
        return self.value.__hash__()


@dataclass
class EntityValue:
    _value: Label

    def __init__(self, value: str) -> None:
        self._value = Label(value)

    def __str__(self) -> str:
        return self._value.value.__str__()


@dataclass
class Entities:
    _entities: dict[EntityKey, EntityValue]

    def __init__(self, entities: dict[EntityKey, EntityValue]) -> None:
        self._entities = entities

    @classmethod
    def from_dict(cls, entities: dict[str | EntityKey, str | EntityValue]) -> Entities:
        """
        Creates entities from its dict form.

        Parameters
        ----------
        entities :
                the entities made of key/value pairs. Either one can be the fully validated class or a string,
                in which case they will be validated by this function.

        Raises
        ------
        ValueError
                if a key or value was invalid.

        Returns
        -------
        The created entities
        """
        return Entities(
            {
                (key if isinstance(key, EntityKey) else EntityKey(key)): (
                    value if isinstance(value, EntityValue) else EntityValue(value)
                )
                for key, value in entities.items()
            }
        )

    @classmethod
    def from_str_list(cls, entities: list[str]) -> Entities:
        """
        Creates entities from its list form.

        Parameters
        ----------
        entities :
                List of the form ``["<key1>-<value1>", ....., "<keyN>-<valueN>"]``

        Raises
        ------
        ValueError
                if one of the list elements did not have a ``-`` separator, or a key or value was invalid.
        TypeError
                if one of the list elements wasn't a str

        Returns
        -------
        The created entities
        """

        if not all(isinstance(entity, str) for entity in entities):
            raise TypeError("found non str entity in list[str] entities parameter")

        try:
            values: dict[EntityKey, EntityValue] = {
                EntityKey(key): EntityValue(value)
                for [key, value] in (
                    entity.split("-", maxsplit=1) for entity in entities
                )
            }
        except ValueError as e:
            raise ValueError(
                f"found entities list {entities} that had an element without a - separator"
            ) from e

        return Entities(values)

    @classmethod
    def from_str(cls, entities: str) -> Entities:
        """
        Creates entities from its string form.

        Parameters
        ----------
        entities :
                String of the form ``"<key1>-<value1>_..._<keyN>-<valueN>"``

        Raises
        ------
        ValueError
                if one of the list elements did not have a ``-`` separator, or a key or value was invalid.

        Returns
        -------
        The created entities
        """
        return Entities.from_str_list(entities.split("_"))

    @classmethod
    def from_any(cls, entities: EntitiesLike) -> Entities:
        """
        Convenience constructor.

        Raises
        ------
        ValueError
                if the entities were invalid.
        TypeError
                if the passed entities argument is not of any allowed type

        See also
        --------
        :py:func:`Entities.from_str`
        :py:func:`Entities.from_str_list`
        :py:func:`Entities.from_dict`
        """

        if entities is None:
            return Entities({})
        elif isinstance(entities, str):
            return Entities.from_str(entities)
        elif isinstance(entities, list):
            return Entities.from_str_list(entities)
        elif isinstance(entities, Entities):
            return entities
        elif isinstance(entities, dict):
            return Entities.from_dict(entities)
        else:
            raise TypeError(
                f"invalid input type {type(entities)} for entities {entities}"
            )

    def __str__(self) -> str:
        """Returns the string form of the entity, i.e. ``"<key1>-<value1>_..._<keyN>-<valueN>"``"""
        return "_".join(f"{key}-{value}" for key, value in self)

    def contains_entity(self, key: EntityKey, value: EntityValue) -> bool:
        """Returns whether the entities contain the given entity given by key/value pair"""
        actual_value = self._entities.get(key)
        return (actual_value is not None) and (actual_value == value)

    def contains_all(self, queried_entities: Entities) -> bool:
        """
        Returns whether the queried entities are all contained in the entities.
        There may be more entities available than there are queried ones.
        """
        for queried_key, queried_value in queried_entities:
            if not self.contains_entity(queried_key, queried_value):
                return False

        return True

    def get_value(self, key: EntityKey) -> Optional[EntityValue]:
        """
        Retrieves the value corresponding to the given key for the given entities, if present.
        """

        return self._entities.get(key)

    def __iter__(self) -> Iterator[tuple[EntityKey, EntityValue]]:
        """
        Retrieves all the entities as key/value pairs.
        """

        return iter(self._entities.items())

    def __len__(self) -> int:
        """
        Retrieves the number of key/value entity pairs.        
        """

        return len(self._entities)

    def __repr__(self) -> str:
        dict_content = ", ".join(f'"{key}": "{value}"' for key, value in self)
        return f"Entities({{{dict_content}}})"


EntitiesLike: TypeAlias = Optional[
    Entities | dict[str | EntityKey, str | EntityValue] | list[str] | str
]
"""
- ``{ "trc": "11CPIB", "run": "1"}``
- ``"trc-11CPIB_run-1"``
- ``["trc-11CPIB", "run-1"]``
"""
