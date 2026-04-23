from __future__ import annotations

from typing import OrderedDict
from collections.abc import Iterator
from dataclasses import dataclass

from .types import Label

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
	_entities: OrderedDict[EntityKey, EntityValue]

	def __init__(self, entities: OrderedDict[EntityKey, EntityValue]):
		self._entities = entities

	@classmethod
	def from_str_list(cls, entities: list[str]) -> Entities:
		return Entities(OrderedDict(
			(EntityKey(key), EntityValue(value)) for [key, value] in (entity.split("-", maxsplit=1) for entity in entities)
		))

	@classmethod
	def from_str(cls, entities: str) -> Entities:
		return Entities.from_str_list(entities.split("_"))

	def __str__(self):
		return "_".join(f"{key}-{value}" for key, value in self)
	
	def contains_entity(self, key: EntityKey, value: EntityValue) -> bool:
		actual_value = self._entities.get(key)
		return (actual_value is not None) and (actual_value == value)
	
	def contains_all(self, queried_entities: Entities) -> bool:
		for queried_key, queried_value in queried_entities:
			if not self.contains_entity(queried_key, queried_value):
				return False
			
		return True
	
	def __iter__(self) -> Iterator[tuple[EntityKey, EntityValue]]:
		return iter(self._entities.items())

	def __len__(self) -> int:
		return len(self._entities)