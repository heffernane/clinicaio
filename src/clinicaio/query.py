from __future__ import annotations

from .entities import *
from .types import *
from .dataset import *

from typing import Optional, Iterable

@dataclass
class ImageQuery:
	participants: set[ParticipantId]
	sessions: set[SessionId]
	data_type: Optional[DataType]
	entities: Entities
	suffix: Optional[Suffix]

	# FIXME: builder pattern?
	def __init__(
		self,
		participants: set[str | ParticipantId] | list[str | ParticipantId] = [],
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

		self.participants = set(type_or_type_from_val(id, ParticipantId) for id in participants)
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
		
    
	def query(
		self,
		dataset: BIDSDataset
	) -> Iterable[ImageQueryResult]:
		filtered_participants = dataset.all_participants() if len(self.participants) == 0 else (dataset.participant_by_id(id) for id in self.participants)
		
		for participant in filtered_participants:
			if participant is None:
				continue

			filtered_sessions = participant.all_sessions() if len(self.sessions) == 0 else (participant.session_by_id(id) for id in self.sessions)

			for session in filtered_sessions:
				if session is None:
					continue
				
				image_per_data_type = session.all_images() if self.data_type is None else ((self.data_type, image) for image in session.images_by_data_type(self.data_type))
				
				for data_type, image in image_per_data_type:
					if (self.suffix is not None) and (image.suffix != self.suffix):
						continue

					if len(self.entities) > 0 and (not image.entities.contains_all(self.entities)):
						continue
					
					yield ImageQueryResult(participant=participant, session=session, data_type=data_type, image=image)

@dataclass
class ImageQueryResult:
	participant: Participant
	session: Session
	data_type: DataType
	image: Image

