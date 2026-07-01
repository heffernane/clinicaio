"""The images that are part of a dataset subject's session."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticError
from typing_extensions import TypedDict

from .entities import Entities
from .types import BIDSException, DataType, FileExtension, Suffix

if TYPE_CHECKING:
    from .session import Session


@dataclass
class Image:
    """
    An image from a BIDS dataset. You can obtain one by :doc:`querying <../index>` from an existing dataset,
    or by :doc:`writing a new dataset <../index>` in which case you will likely want to create
    the NIFTI and eventually companion files, using :py:meth:`get_nifti_image_path()` and
    :py:meth:`get_image_companion_path()`.
    """

    parent_session: Session = field(repr=False, compare=False)
    data_type: DataType

    nifti_extension: FileExtension
    entities: Entities
    scan_info: ImageScanInfo
    """Non-empty only if enabled when reading the dataset with :py:meth:`BIDSDataset.populate_from_dir() <clinicaio.dataset.BIDSDataset.populate_from_dir>`."""

    extra_labels: set[str]
    # The unfortunate thing about supporting CAPS is that there is no consistency whatsoever with
    # regards to where the "extra" labels are placed. Here's some examples from Clinica's code:
    # sub-*_ses-*_T1w_target-{group_label}_transformation-forward_deformation.nii*"
    #             ^^^^
    #             extra label just after sub_ses prefix
    # f"*_trc-{acq_label.value}_pet_space-Ixi549Space{pvc_key_value}{suvr_key_value}{mask_key_value}{fwhm_key_value}_pet.nii*",
    #                           ^^^^
    #                           extra label somewhere between other entities key/value pairs
    #
    # So that means that for CAPS there is no nice way of handling it. For BIDS however the
    # filename can fully be re-created as it has only a canonical form.
    _caps_exact_filename_stem: Optional[str]

    suffix: Optional[Suffix] = None

    @cached_property
    def json_sidecar(self) -> dict[str, Any]:
        """
        Obtains the content of this image's JSON sidecar file, as defined in the BIDS specification.

        Raises
        ------
        OSError
            if the JSON sidecar does not exist
        ValueError
            if the JSON sidecar's content is invalid
        """

        import json

        sidecar_path = self.get_image_companion_path(FileExtension.JSON)
        with open(sidecar_path, mode="r") as f:
            try:
                json_dict = json.load(f)
            except json.JSONDecodeError:
                raise

            if not isinstance(json_dict, dict):
                raise ValueError(
                    f"expected JSON sidecar {sidecar_path} to contain an object as root node"
                )

        return json_dict

    @staticmethod
    def _parse_filename_components(
        filename_after_sub_ses: str,
    ) -> Optional[tuple[Entities, Optional[Suffix], FileExtension, set[str]]]:
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
            raise ValueError(
                f"found image filename {filename_after_sub_ses} without any entity or suffix"
            )

        try:
            extension = FileExtension(file_ext)
        except ValueError as e:
            # If this happens for legitimate files, you may need to add the file extension to the enumeration
            raise ValueError(
                f"Found unknown file extension {file_ext} for filename {filename_after_sub_ses}"
            ) from e

        entities_list = entities_and_suffix.split("_")
        suffix = None
        if "-" not in entities_list[-1]:
            try:
                suffix = TypeAdapter(Suffix).validate_python(entities_list.pop(-1))
            except PydanticError as e:
                raise BIDSException._from_pydantic(
                    f"found invalid suffix label for image filename {filename_after_sub_ses}",
                    e,
                )

        extra_labels: set[str] = set()
        # Note: the iteration is done in reversed order so that successive indices
        # are not invalidated when removing an item from the list: only the "later"
        # (as in e.g. i+1 until the end of the list) is invalidated, not the indices
        # "before".
        for i in reversed(range(len(entities_list))):
            entity = entities_list[i]
            if "-" not in entity:
                extra_labels.add(entities_list.pop(i))

        try:
            entities = Entities.from_str_list(entities_list)
        except Exception as e:
            raise ValueError(
                f"found invalid entities for image filename {filename_after_sub_ses}: {e}"
            ) from e

        return (entities, suffix, extension, extra_labels)

    def _get_image_base_full_path(
        self,
    ) -> Path:
        if self._caps_exact_filename_stem is None:
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
        else:
            return (
                self.parent_session._get_full_path()
                / f"{self.data_type}"
                / self._caps_exact_filename_stem
            )

    def get_nifti_image_path(self) -> Path:
        """Returns the full path to this image's NIFTI file"""
        return self.get_image_companion_path(self.nifti_extension)

    def get_image_companion_path(self, extension: FileExtension) -> Path:
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


# FIXME: https://github.com/python/mypy/issues/18176
class ImageScanInfo(TypedDict, extra_items=Any):  # type: ignore
    """
    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#scans-file>`__
    """
