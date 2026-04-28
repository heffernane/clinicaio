from __future__ import annotations

from typing import Optional
from dataclasses import dataclass

from .entities import Entities, EntityKey, EntityValue
from .types import BIDSException
from .dataset import SubjectId, SessionId, DataType, Suffix

__all__ = ["ImageQuery"]

@dataclass
class ImageQuery:
	"""
	Creates an image query filtering structure for later use with
	:py:func:`clinicaio.dataset.BIDSDataset.query_images` or :py:func:`clinicaio.dataset.BIDSDataset.query_nifti_images_paths` for example.

	Parameters
	----------

	subjects : set[str | SubjectId] | list[str | SubjectId], default=[]
		The list of subjects to specifically keep. If empty, includes all of them.
	session : set[str | SessionId] | list[str | SessionId], default=[]
		The list of subjects to specifically keep. If empty, includes all of them.
	"""

	subjects: set[SubjectId]
	sessions: set[SessionId]
	data_type: Optional[DataType]
	entities: Entities
	suffix: Optional[Suffix]

	def __init__(
		self,
		subjects: set[str | SubjectId] | list[str | SubjectId] = [],
		sessions: set[str | SessionId] | list[str | SessionId] = [],
		# FIXME: allow multiple data types at once?
		data_type: Optional[DataType] = None,
		# { "trc": "11CPIB", "run": 1}
		# or "trc-11CPIB_run-1"
		# or ["trc-11CPIB", "run-1"]
		entities: Entities | dict[str | EntityKey, str | EntityValue] | list[str] | str = {},
		# +/- modality
		suffix: Optional[str | Suffix] = None,
	):
		"""
		Creates an image query filtering structure for later use with
		::clinicaio.BIDSDataset.query_images:: or ::clinicaio.BIDSDataset.query_nifti_images_paths:: for example.

		Parameters
		----------

		subjects : set[str | SubjectId] | list[str | SubjectId], default=[]
			The list of subjects to specifically keep. If empty, includes all of them.
		session : set[str | SessionId] | list[str | SessionId], default=[]
			The list of subjects to specifically keep. If empty, includes all of them.
		"""

		type_or_type_from_val = lambda v, typ: v if isinstance(v, typ) else typ(v)

		self.subjects = set(type_or_type_from_val(id, SubjectId) for id in subjects)
		self.sessions = set(type_or_type_from_val(id, SessionId) for id in sessions)
		if not ((data_type is None) or (type(data_type) == DataType)):
			raise BIDSException(f"invalid type {type(data_type)} for data_type argument")
		
		self.data_type = data_type

		if isinstance(entities, str):
			self.entities = Entities.from_str(entities)
		elif isinstance(entities, list):
			if not all(isinstance(entity, str) for entity in entities):
				raise BIDSException("found non str entity in list[str] entities parameter for image query")
			
			self.entities = Entities.from_str_list(entities)
		elif isinstance(entities, Entities):
			self.entities = entities
		elif isinstance(entities, dict):
			self.entities = Entities({
				type_or_type_from_val(key, EntityKey): type_or_type_from_val(value, EntityValue)
				for key, value in entities.items()
			})
		else:
			raise BIDSException(f"invalid type {type(entities)} for ImageQuery entities {entities}")
		
		self.suffix = None if suffix is None else type_or_type_from_val(suffix, Suffix)