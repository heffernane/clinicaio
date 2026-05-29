from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticError

from .entities import Entities
from .types import BIDSException, DataType, FileExtension, Suffix

if TYPE_CHECKING:
    from .session import Session


@dataclass
class Image:
    parent_session: Session = field(repr=False, compare=False)
    data_type: DataType

    nifti_extension: FileExtension
    entities: Entities
    scan_info: ImageScanInfo
    suffix: Optional[Suffix] = None

    @cached_property
    def json_sidecar(self) -> dict[str, Any]:
        import json

        sidecar_path = self.get_image_companion_file_path(FileExtension.JSON)
        with open(sidecar_path, mode="r") as f:
            json_dict = json.load(f)
            if not isinstance(json_dict, dict):
                raise BIDSException(
                    f"expected JSON sidecar {sidecar_path} to contain an object as root node"
                )

        return json_dict

    @staticmethod
    def _parse_filename_components(
        filename_after_sub_ses: str,
    ) -> Optional[tuple[Entities, Optional[Suffix], FileExtension]]:
        """
        A given BIDS image filename is of the form ``sub-<label_ses-<label>_<rest>``,
        where ``<rest>`` is ``<entities>[_<suffix>].<extension>``.
        This function's role is to parse the ``<rest>`` part into its components.
        It returns ``None`` if there is no file extension, or a :py:class:`~clinicaio.types.BIDSException` if
        the passed string is invalid.
        """
        try:
            [before_ext, file_ext] = filename_after_sub_ses.split(".", maxsplit=1)
        except ValueError:
            # no "." in string so can't decompose list in assignment
            return None

        entities_and_suffix = before_ext
        if len(entities_and_suffix) == 0:
            raise BIDSException(
                f"found image filename {filename_after_sub_ses} without any entity or suffix"
            )

        try:
            extension = FileExtension(file_ext)
        except ValueError:
            # If this happens for legitimate files, you may need to add the file extension to the enumeration
            raise BIDSException(
                f"Found unknown file extension {file_ext} for filename {filename_after_sub_ses}"
            )

        entities = entities_and_suffix.split("_")
        suffix = None
        if "-" not in entities[-1]:
            try:
                suffix = TypeAdapter(Suffix).validate_python(entities[-1])
            except PydanticError as e:
                raise BIDSException._from_pydantic(
                    f"found invalid suffix label for image filename {filename_after_sub_ses}",
                    e,
                )

            entities = entities[:-1]

        try:
            entities = Entities.from_str_list(entities)
        except BIDSException as e:
            raise BIDSException(
                f"found invalid entities for image filename {filename_after_sub_ses}: {e}"
            )

        return (entities, suffix, extension)

    def _get_image_base_full_path(
        self,
    ) -> Path:
        entities = "" if len(self.entities) == 0 else f"{self.entities}"
        suffix = "" if self.suffix is None else f"{self.suffix}"

        return (
            self.parent_session._get_full_path()
            / f"{self.data_type}"
            / (
                self.parent_session._sub_ses_prefix
                + "_".join(s for s in [entities, suffix] if len(s) != 0)
            )
        )

    def get_nifti_image_path(self) -> Path:
        """Returns the full path to this image's NIFTI file"""
        return self.get_image_companion_file_path(self.nifti_extension)

    def get_image_companion_file_path(self, extension: FileExtension) -> Path:
        """
        BIDS is a format centered around organizing NIFTI image files, but NIFTI does not include
        all the information that one might want from a brain image or its acquisition process
        (equipment parameters, etc.). As such each NIFTI image file has zero or more "companion" files
        (or "sidecar" in BIDS-parlance for the JSON ones) that have the same file name as the main NIFTI
        ones apart from their file extension.

        This method returns the path of such an image's companion file given its file extension.

        .. code-block::

                sub-OAS30542
                └── ses-M126
                    └── dwi
                        ├── sub-OAS30542_ses-M126_run-01_dwi.bval
                        ├── sub-OAS30542_ses-M126_run-01_dwi.bvec
                        ├── sub-OAS30542_ses-M126_run-01_dwi.json
                        └── sub-OAS30542_ses-M126_run-01_dwi.nii.gz

        """
        return self._get_image_base_full_path().with_suffix(f".{extension}")


# sidecar file .json
# class ImageInfo:
# ...
# sidecar_dict: dict[str, Any]
# pass


@dataclass
class ImageScanInfo:
    """
    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#scans-file>`__
    """

    # TODO: proper typing for fields defined in BIDS specification
    other_fields: dict[str, Any]

    def all_fields(self) -> dict[str, Any]:
        return self.other_fields

    def is_empty(self) -> bool:
        return len(self.other_fields) == 0
