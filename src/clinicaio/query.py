from __future__ import annotations

from .entities import *
from .types import *
from .dataset import *

from typing import Optional

@dataclass
class ImageQuery:
	subjects: set[SubjectId]
	sessions: set[SessionId]
	data_type: Optional[DataType]
	entities: Entities
	suffix: Optional[Suffix]

	# FIXME: builder pattern?
	def __init__(
		self,
		subjects: set[str | SubjectId] | list[str | SubjectId] = [],
		sessions: set[str | SessionId] | list[str | SessionId] = [],
		# FIXME: allow multiple data types at once?
		data_type: Optional[DataType] = None,
		# { "trc": "11CPIB", "run": 1}
		# or "trc-11CPIB_run-1"
		# or ["trc-11CPIB", "run-1"]
		entities: Entities | dict[str | EntityKey, str | EntityValue] | OrderedDict[str | EntityKey, str | EntityValue] | list[str] | str = {},
		# +/- modality
		suffix: Optional[str | Suffix] = None,
	):
		type_or_type_from_val = lambda v, typ: v if isinstance(v, typ) else typ(v)

		self.subjects = set(type_or_type_from_val(id, SubjectId) for id in subjects)
		self.sessions = set(type_or_type_from_val(id, SessionId) for id in sessions)
		self.data_type = data_type

		if isinstance(entities, str):
			self.entities = Entities.from_str(entities)
		elif isinstance(entities, list):
			if not all(isinstance(entity, str) for entity in entities):
				raise BIDSException("found non str entity in list[str] entities parameter for image query")
			
			self.entities = Entities.from_str_list(entities)
		elif isinstance(entities, Entities):
			self.entities = entities
		elif isinstance(entities, OrderedDict) or isinstance(entities, dict):
			self.entities = Entities(OrderedDict(
				(type_or_type_from_val(key, EntityKey), type_or_type_from_val(value, EntityValue))
				for key, value in entities.items()
			))
		else:
			raise BIDSException(f"invalid type {type(entities)} for ImageQuery entities {entities}")
		
		self.suffix = None if suffix is None else type_or_type_from_val(suffix, Suffix)