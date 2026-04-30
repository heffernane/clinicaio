from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from .types import BIDSException, Label

# not for sub- and ses- entities
# todo: enum?
class EntityKey(Label):
	def __hash__(self):
		return self.value.__hash__()

@dataclass
class EntityValue:
	#value: Index | Label
	_value: Label

	def __init__(self, value: str):
		self._value = Label(value)

	def __str__(self):
		return self._value.value.__str__()

@dataclass
class Entities:
	_entities: dict[EntityKey, EntityValue]

	def __init__(self, entities: dict[EntityKey, EntityValue]):
		self._entities = entities

	@classmethod
	def from_str_list(cls, entities: list[str]) -> Entities:
		"""
		Creates entities from its list form.
		
		Parameters
		----------
		entities : list[str]
			List of the form ``["<key1>-<value1>", ....., "<keyN>-<valueN>"]``
		
		Raises
		------
		BIDSException
			if one of the list elements did not have a ``-`` separator, or a key or value was invalid.

		Returns
		-------
		The created entities
		"""

		try:
			values = {
				EntityKey(key): EntityValue(value)
				for [key, value] in (entity.split("-", maxsplit=1) for entity in entities)
			}	
		except ValueError:
			raise BIDSException(f"found entities list {entities} that had an element without a - separator")

		return Entities(values)

	@classmethod
	def from_str(cls, entities: str) -> Entities:
		"""
		Creates entities from its string form.
		
		Parameters
		----------
		entities : str
			String of the form ``"<key1>-<value1>_..._<keyN>-<valueN>"``
		
		Raises
		------
		BIDSException
			if one of the list elements did not have a ``-`` separator, or a key or value was invalid.

		Returns
		-------
		The created entities
		"""
		return Entities.from_str_list(entities.split("_"))

	def __str__(self):
		"""Returns the string form of the entity, i.e. ``"<key1>-<value1>_..._<keyN>-<valueN>"`` """
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
	
	def __iter__(self) -> Iterator[tuple[EntityKey, EntityValue]]:
		return iter(self._entities.items())

	def __len__(self) -> int:
		return len(self._entities)
	
	def __repr__(self) -> str:
		dict_content = ", ".join(f"\"{key}\": \"{value}\"" for key, value in self)
		return f"Entities({{{dict_content}}})"