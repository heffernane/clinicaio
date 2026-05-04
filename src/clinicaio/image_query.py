from __future__ import annotations

__all__ = ["ImageQuery"]

from typing import Iterable, Optional
from dataclasses import dataclass

from .entities import Entities, EntityKey, EntityValue
from .types import BIDSException, SubjectId, SessionId, DataType, Suffix

@dataclass
class ImageQuery:
	"""
	Creates an image query filtering data structure for later use with
	:py:func:`clinicaio.dataset.BIDSDataset.query_images`,
	:py:func:`clinicaio.dataset.BIDSDataset.query_images_nifti_paths`
	or :py:func:`clinicaio.dataset.BIDSDataset.query_images_companions_paths` for example.

	Parameters
	----------
	subjects : set[str | SubjectId] | list[str | SubjectId], default=[]
		The subjects (by their IDs) to specifically keep. If empty, includes all of them.
	session : set[str | SessionId] | list[str | SessionId], default=[]
		The subjects (by their IDs) to specifically keep. If empty, includes all of them.
	data_type : Optional[DataType], default=None
		The data type of the image. If ``None``, all of them are kept.
	entities : Entities | dict[str | EntityKey, str | EntityValue] | list[str] | str, default={}
		The entities to specifically look for in the images. For convenience it can also
		be specified either in a dictionary form, or a list of ``"<key>-<value>"``, or
		as a fully-formed BIDS entities string ``"<key1>-<value1>_..._<keyN>-<valueN>"``.
	suffix : Optional[str | Suffix], default=None
		The suffix to specifically look for in the images. If ``None``, all of them are kept.

	Examples
	--------

	.. code-block:: python

		ImageQuery(subjects=["sub-ADNI027S0074"])
		ImageQuery(subjects={"sub-ADNI027S0074"})
		ImageQuery(data_type=DataType.PET)
		ImageQuery(entities={"trc": "11CPIB", "task": "rest"})
		ImageQuery(entities=["trc-11CPIB", "task-rest"])
		ImageQuery(entities="trc-11CPIB_task-rest")
		ImageQuery(suffix="T1w")

	Or as a more exhaustive example:

	.. code-block:: python

		image_query = ImageQuery(
			subjects=["sub-ADNI027S0074"], 
			sessions=["ses-M000"], 
			data_type=DataType.PET,
			entities={"trc": "18FFDG", "rec": "coregiso8"},
			suffix="pet",
		)
		images = dataset.query_images(image_query)
	"""

	subjects: set[SubjectId] 
	sessions: set[SessionId]
	data_type: Optional[DataType]
	entities: Entities
	suffix: Optional[Suffix]

	def __init__(
		self,
		*,
		subjects: Iterable[str | SubjectId] = [],
		sessions: Iterable[str | SessionId] = [],
		# FIXME: allow multiple data types at once?
		data_type: Optional[DataType] = None,
		# { "trc": "11CPIB", "run": "1"}
		# or "trc-11CPIB_run-1"
		# or ["trc-11CPIB", "run-1"]
		entities: Entities | dict[str | EntityKey, str | EntityValue] | list[str] | str = {},
		# +/- modality
		suffix: Optional[str | Suffix] = None,
	):
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