"""Dataset images querying functionality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Optional

from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticError

from .entities import Entities, EntitiesLike
from .types import BIDSException, DataType, SessionId, SubjectId


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
            Together with the ``subjects``, it forms a cartesian-product for filtering, meaning
            that subjects and sessions are filtered independently, not pair-wise.
    sub_ses :
            The subject/session pairs to keep. This is a cross-product, meaning that only a
            given subject/session pair matching one of the exact provided ones will match.
            It must not be specified at the same time as ``subjects`` or ``sessions``.
    data_type :
            The data type of the image. If ``None``, all of them are kept.
    entities :
            The entities to specifically look for in the images. For convenience it can also
            be specified either in a dictionary form, or a list of ``"<key>-<value>"``, or
            as a fully-formed BIDS entities string ``"<key1>-<value1>_..._<keyN>-<valueN>"``.
    suffix :
            The suffix to specifically look for in the images. If ``None``, all of them are kept.
            This is a wildcard pattern using the syntax supported by :py:func:`fnmatch.fnmatchcase`.

    Raises
    ------
    ValueError
        if both ``query.sub_ses`` and either ``query.subjects``or ``query.sessions`` are specified
        at the same time: the former operates on a cross-product basis, while the later two operate
        on a cartesian-product when combined, so it does not make much sense to have both at the same time

    Examples
    --------

    * :doc:`/examples/assorted_queries`

    .. code-block:: python

            ImageQuery(subjects=["sub-ADNI027S0074"])
            ImageQuery(subjects={"sub-ADNI027S0074"})
            ImageQuery(sub_ses={"sub-ADNI027S0074": {"ses-A"}})
            ImageQuery(sub_ses={"sub-ADNI027S0074": {"ses-A", "ses-B"}})
            ImageQuery(sub_ses=[("sub-ADNI027S0074", "ses-A"), ("sub-AIBL1234", "ses-B")])
            ImageQuery(data_type=DataType.PET)
            ImageQuery(data_type="pet")
            ImageQuery(entities={"trc": "11CPIB", "task": "rest"})
            ImageQuery(entities=["trc-11CPIB", "task-rest"])
            ImageQuery(entities="trc-11CPIB_task-rest")
            ImageQuery(suffix="T1w")

    Or as a more exhaustive example:

    .. code-block:: python

            image_query = ImageQuery(
                    subjects={"sub-ADNI027S0074"},
                    sessions={"ses-M000"},
                    data_type=DataType.PET,
                    entities={"trc": "18FFDG", "rec": "coregiso8"},
                    suffix="pet",
            )
            images = dataset.query_images(image_query)

    Cartesian vs cross-product of subjects/sessions:

    .. code-block:: python

        ImageQuery(subjects={"sub-A", "sub-B"}, sessions={"ses-1", "ses-3"}
        # will match the images marked as X:
        #      1  2  3  < ses-*
        #    A X     X
        #    B X     X
        #    C
        # ^sub-*

        ImageQuery(sub_ses={"sub-A": {"ses-1"}, "sub-B": {"ses-3"}})
        ImageQuery(sub_ses=[("sub-A", "ses-1"), ("sub-B", "ses-3")]
        # will match the images marked as X:
        #      1  2  3  < ses-*
        #    A X
        #    B       X
        #    C
        # ^sub-*
    """

    subjects: set[SubjectId]
    sessions: set[SessionId]
    sub_ses: dict[SubjectId, set[SessionId]]
    data_type: Optional[DataType]
    entities: Entities
    suffix: Optional[str]

    def __init__(
        self,
        *,
        subjects: Optional[Iterable[SubjectId]] = None,
        sessions: Optional[Iterable[SessionId]] = None,
        sub_ses: Optional[
            list[tuple[SubjectId, SessionId]] | dict[SubjectId, set[SessionId]]
        ] = None,
        data_type: Optional[DataType | str] = None,
        # { "trc": "11CPIB", "run": "1"}
        # or "trc-11CPIB_run-1"
        # or ["trc-11CPIB", "run-1"]
        entities: EntitiesLike = None,
        # +/- modality
        suffix: Optional[str] = None,
    ):
        def validate_value(value_type: Any, value: Any, err_prefix: str) -> Any:
            try:
                return TypeAdapter(value_type).validate_python(value)
            except PydanticError as e:
                raise BIDSException._from_pydantic(f"{err_prefix} ({value})", e)

        self.subjects = (
            set()
            if subjects is None
            else set(
                validate_value(SubjectId, id, "invalid subject ID") for id in subjects
            )
        )
        self.sessions = (
            set()
            if sessions is None
            else set(
                validate_value(SessionId, id, "invalid session ID") for id in sessions
            )
        )

        if sub_ses is None:
            sub_ses = {}

        # Keep the original one around so that the error message makes sense later.
        orig_sub_ses = sub_ses

        if isinstance(sub_ses, list):
            d: dict[SubjectId, set[SessionId]] = {}

            for subject, session in sub_ses:
                d.setdefault(subject, set()).add(session)

            sub_ses = d
        self.sub_ses = validate_value(
            dict[SubjectId, set[SessionId]], sub_ses, "invalid subject/session pair(s)"
        )
        if any(len(sessions) == 0 for sessions in self.sub_ses.values()):
            raise ValueError(
                f"Found a subject without an associated session in its pair, in {orig_sub_ses}"
            )

        if not ((data_type is None) or (isinstance(data_type, (DataType, str)))):
            raise TypeError(f"invalid type {type(data_type)} for data_type argument")
        if isinstance(data_type, str):
            data_type = DataType(data_type)
        self.data_type = data_type

        self.entities = Entities.from_any(entities)

        self.suffix = suffix

        if len(self.sub_ses) > 0 and (
            (len(self.subjects) > 0) or (len(self.sessions) > 0)
        ):
            raise ValueError(
                "querying for both cross-product subjects-sessions pairs and cartesian-product of subjects and sessions does not make sense"
            )
