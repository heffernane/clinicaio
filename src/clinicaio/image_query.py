from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticError

from .entities import Entities, EntitiesLike
from .types import BIDSException, DataType, SessionId, SubjectId, Suffix


@dataclass
class ImageQuery:
    """
    Creates an image query filtering data structure for later use with
    :py:func:`clinicaio.dataset.BIDSDataset.query_images`,
    :py:func:`clinicaio.dataset.BIDSDataset.query_images_nifti_paths`
    or :py:func:`clinicaio.dataset.BIDSDataset.query_images_companions_paths` for example.

    Parameters
    ----------
    subjects :
            The subjects (by their IDs) to specifically keep. If empty, includes all of them.
    session :
            The subjects (by their IDs) to specifically keep. If empty, includes all of them.
    data_type :
            The data type of the image. If ``None``, all of them are kept.
    entities :
            The entities to specifically look for in the images. For convenience it can also
            be specified either in a dictionary form, or a list of ``"<key>-<value>"``, or
            as a fully-formed BIDS entities string ``"<key1>-<value1>_..._<keyN>-<valueN>"``.
    suffix :
            The suffix to specifically look for in the images. If ``None``, all of them are kept.
            This is a wildcard pattern using the syntax supported by :py:func:`fnmatch.fnmatchcase`.

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
    suffix: Optional[str]

    def __init__(
        self,
        *,
        subjects: Optional[Iterable[SubjectId]] = None,
        sessions: Optional[Iterable[SessionId]] = None,
        data_type: Optional[DataType] = None,
        # { "trc": "11CPIB", "run": "1"}
        # or "trc-11CPIB_run-1"
        # or ["trc-11CPIB", "run-1"]
        entities: EntitiesLike = None,
        # +/- modality
        suffix: Optional[str] = None,
    ):
        def validate_str(str_type: Any, s: str, err_prefix: str) -> Any:
            try:
                return TypeAdapter(str_type).validate_python(s)
            except PydanticError as e:
                raise BIDSException.from_pydantic(f"{err_prefix} ({s})", e)

        self.subjects = (
            set()
            if subjects is None
            else set(
                validate_str(SubjectId, id, "invalid subject ID") for id in subjects
            )
        )
        self.sessions = (
            set()
            if sessions is None
            else set(
                validate_str(SessionId, id, "invalid session ID") for id in sessions
            )
        )
        if not ((data_type is None) or (type(data_type) == DataType)):
            raise BIDSException(
                f"invalid type {type(data_type)} for data_type argument"
            )

        self.data_type = data_type

        self.entities = Entities.from_any(entities)

        self.suffix = suffix
