"""A session that a given subject has participated in."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Optional

from pandas import DataFrame
from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticError
from typing_extensions import NotRequired, TypedDict

from ._tsv_utils import _read_tsv_as_df, _write_rows_to_tsv
from .entities import Entities, EntitiesLike
from .image import Image, ImageScanInfo
from .types import BIDSException, DataType, FileExtension, SessionId, Suffix

if TYPE_CHECKING:
    from .subject import Subject


@dataclass
class Session:
    parent_subject: Subject = field(repr=False, compare=False)

    id: Optional[SessionId]
    info: SessionInfo
    """Non-empty only if enabled when reading the dataset with :py:meth:`BIDSDataset.populate_from_dir() <clinicaio.dataset.BIDSDataset.populate_from_dir>`."""

    _images: dict[DataType, list[Image]] = field(default_factory=lambda: {})

    def _get_full_path(self) -> Path:
        if self.id is None:
            return self.parent_subject._get_full_path()
        else:
            return self.parent_subject._get_full_path() / f"{self.id}"

    def images_by_data_type(self, data_type: str | DataType) -> Iterable[Image]:
        """
        Retrieves all this session's images that match the given data type.
        """

        return self._images.get(DataType(data_type)) or []

    def all_images(self) -> Iterable[Image]:
        """Returns all the images that are part of this session"""
        for images in self._images.values():
            yield from images

    def images_count(self, data_type: Optional[DataType] = None) -> int:
        """
        Parameters
        ----------
        data_type :
                The data type that the considered images should have to be counted, or ``None`` to count all images

        Returns
        -------
        The images count of this session, eventually only considering images that have a given data type.
        """
        if data_type is None:
            return sum(len(images) for images in self._images.values())
        else:
            images_for_data_type = self._images.get(data_type)
            return 0 if images_for_data_type is None else len(images_for_data_type)

    def _write_to_folder(self) -> None:
        session_path = self._get_full_path()
        os.makedirs(session_path, exist_ok=True)

        # *_scans.tsv writing
        rows = (
            image.scan_info
            | {"filename": str(image.get_nifti_image_path().relative_to(session_path))}
            for image in self.all_images()
            if len(image.scan_info) != 0
        )
        _write_rows_to_tsv(
            session_path / self._scans_tsv_file_name,
            first_column_name="filename",
            rows=rows,
        )

    def _add_image(
        self,
        data_type: DataType,
        nifti_extension: FileExtension,
        entities: Entities,
        *,
        suffix: Optional[Suffix],
        scan_info: Optional[ImageScanInfo],
    ) -> Image:
        if not nifti_extension.is_nifti():
            raise ValueError(
                f"provided non-NIFTI file extension {nifti_extension} when adding image to session"
            )

        image = Image(
            parent_session=self,
            data_type=data_type,
            nifti_extension=nifti_extension,
            entities=entities,
            suffix=suffix,
            scan_info=ImageScanInfo({}) if scan_info is None else scan_info,
        )

        if data_type not in self._images:
            self._images[data_type] = []

        self._images[data_type].append(image)

        return image

    def write_image(
        self,
        data_type: DataType | str,
        nifti_extension: FileExtension | str,
        *,
        entities: EntitiesLike,
        suffix: Optional[Suffix] = None,
        scan_info: Optional[ImageScanInfo] = None,
    ) -> Image:
        """
        Adds to the session the image created with the given properties, and creates
        its parent folders.

        Returns
        -------
        The created image.
            You can now use its methods to obtain the path to the NIFTI image or one of its
            companion files, which you can use to write them. You must at least create the NIFTI image itself
            or the BIDS will be invalid.

        See also
        --------
        * :py:meth:`Image.get_nifti_image_path() <clinicaio.image.Image.get_nifti_image_path>`
        * :py:meth:`Image.get_image_companion_path() <clinicaio.image.Image.get_image_companion_path>`
        """

        if suffix is not None:
            try:
                TypeAdapter(Suffix).validate_python(suffix)
            except PydanticError as e:
                raise BIDSException._from_pydantic("invalid suffix", e)

        if isinstance(data_type, str):
            data_type = DataType(data_type)
        if isinstance(nifti_extension, str):
            nifti_extension = FileExtension(nifti_extension)

        image = self._add_image(
            data_type,
            nifti_extension,
            Entities.from_any(entities),
            suffix=suffix,
            scan_info=scan_info,
        )

        data_type_folder_path = self._get_full_path() / f"{data_type}"
        os.makedirs(data_type_folder_path, exist_ok=True)

        return image

    @cached_property
    def _sub_ses_prefix(self) -> str:
        ses_id = "" if self.id is None else f"_{self.id}"

        return f"{self.parent_subject.id}{ses_id}_"

    @cached_property
    def _scans_tsv_file_name(self) -> str:
        return f"{self._sub_ses_prefix}scans.tsv"

    def populate_image_scans_info_from_df(self, scans_tsv_df: DataFrame) -> None:
        """
        Populates the images information from the given dataframe.
        The dataframe must have a ``filename`` column which corresponds to
        the relative path of the image file relative to its parent session/this session,
        e.g. ``<data type>/sub-..._ses-..._<.....>.nii.gz``. The corresponding
        Image must already be present in this session. The other columns
        will be used as information for the image at hand: they will not be
        merged with the information from the existing images, instead they'll be replaced entirely.

        Warnings
        --------
        You should only ever use this function if it is more convenient
        for your use case when you are writing a new BIDS dataset. Filling-in
        the information directly from :py:meth:`Session.write_image() <clinicaio.session.Session.write_image>` should be favored.
        """
        if "filename" not in scans_tsv_df.columns:
            raise ValueError(
                "the dataframe did not have the required 'filename' column"
            )

        infos: list[dict[str, Any]] = scans_tsv_df.to_dict(orient="records")  # type: ignore
        for info in infos:
            image_filename = info.pop("filename", None)
            if image_filename is None:
                continue
            try:
                # Note: the split happens from the end to allow having a datatype with slashes
                data_type, image_basename = str(image_filename).rsplit(
                    sep="/", maxsplit=1
                )
            except ValueError as e:
                raise ValueError(
                    f"expected image/scan filename of format <data_type>/<...> for {image_filename} in dataframe"
                ) from e

            try:
                data_type = DataType(data_type)
            except ValueError as e:
                raise ValueError(
                    f"expected valid data type as first folder of filename {image_filename} in dataframe"
                ) from e

            if not image_basename.startswith(self._sub_ses_prefix):
                raise ValueError(
                    f"expected image basename {image_basename} of filename {image_filename} in dataframe to have prefix {self._sub_ses_prefix}"
                )

            after_sub_ses = image_basename.removeprefix(self._sub_ses_prefix)
            try:
                filename_components = Image._parse_filename_components(after_sub_ses)
            except Exception as e:
                raise ValueError(
                    f"found invalid image filename {image_filename} in dataframe: {e}"
                ) from e

            if filename_components is None:
                raise ValueError(
                    f"found image filename {image_filename} in dataframe without any file extension"
                )
            entities, suffix, extension = filename_components

            if not extension.is_nifti():
                continue

            image = None
            for img_by_data_type in self.images_by_data_type(data_type):
                if (
                    img_by_data_type.nifti_extension == extension
                    and img_by_data_type.entities == entities
                    and img_by_data_type.suffix == suffix
                ):
                    image = img_by_data_type
                    break

            if image is None:
                raise ValueError(
                    f"could not find image for filename {image_filename} in dataframe"
                )

            image.scan_info = TypeAdapter(ImageScanInfo).validate_python(info)

    # read the session's _scans.tsv and fill out scan info for all images
    def _populate_image_scans_info_from_tsv(self) -> None:
        scans_tsv_path = self._get_full_path() / self._scans_tsv_file_name
        if not os.path.exists(scans_tsv_path):
            return

        scans_tsv_df = _read_tsv_as_df(scans_tsv_path)
        try:
            self.populate_image_scans_info_from_df(scans_tsv_df)
        except Exception as e:
            raise BIDSException(
                f"could not populate images scans info from TSV file {scans_tsv_path}: {e}"
            ) from e

    def _populate_images_from_folder(self, *, image_scans_info: bool) -> set[str]:
        unhandled_entries: set[str] = set()

        # Populate the session's images, per-datatype
        for child in os.scandir(self._get_full_path()):
            if child.name == self._scans_tsv_file_name:
                continue

            try:
                data_type = DataType(child.name)
            except ValueError:
                unhandled_entries.add(child.path)
                continue

            if not child.is_dir():
                raise ValueError(
                    f"Found data type entry {data_type} that was not a directory"
                )

            maybe_duplicated_images: list[Image] = []

            for child_image in os.scandir(child.path):
                if not child_image.name.startswith(self._sub_ses_prefix):
                    raise ValueError(
                        f"expected {data_type}/{child_image.name} "
                        f"filename to start with {self._sub_ses_prefix} due to its placement in the BIDS directory hierarchy"
                    )

                after_sub_ses = child_image.name.removeprefix(self._sub_ses_prefix)

                try:
                    filename_components = Image._parse_filename_components(
                        after_sub_ses
                    )
                except Exception as e:
                    raise ValueError(
                        f"Found invalid image filename {child_image.name} in folder {data_type}: {e}"
                    ) from e

                # For now we just exclude any file without a file extension, without raising
                # an error.
                if filename_components is None:
                    unhandled_entries.add(child_image.path)
                    continue
                entities, suffix, extension = filename_components

                # All the usual filename validation is done for non-NIFTI files, so that
                # we do not end up in a situation where the companion files (.json, etc.)
                # are inaccessible due to invalid naming. We do not store those companion
                # files however: we just validate the paths, but only actually accessing
                # such companion files by their paths will tell whether a particular one exists.
                if not extension.is_nifti():
                    continue

                image = self._add_image(
                    data_type=data_type,
                    nifti_extension=extension,
                    entities=entities,
                    suffix=suffix,
                    scan_info=None,
                )
                # https://bids-specification.readthedocs.io/en/stable/common-principles.html#uniqueness-of-data-files
                # "If multiple extensions are permissible (for example, .nii and .nii.gz), there MUST only be one such
                # file with the same entities, datatype and suffix"
                #
                # Since .nii are much rarer than .nii.gz, let's trigger this check only when we encounter the former
                if image.nifti_extension == FileExtension.NII:
                    maybe_duplicated_images.append(image)

            for dup_image in maybe_duplicated_images:

                def is_duplicated_image(img: Image) -> bool:
                    # At this point we already know they have the same subject/session/datatype, and they have different file
                    # extensions if the
                    return (
                        (img is not dup_image)
                        and (img.suffix == dup_image.suffix)
                        and (img.entities == dup_image.entities)
                    )

                other_same_images = list(
                    filter(is_duplicated_image, self._images[data_type])
                )

                if len(other_same_images) > 0:
                    paths = [
                        str(image.get_nifti_image_path()) for image in other_same_images
                    ]

                    raise ValueError(
                        f"found image {str(dup_image.get_nifti_image_path())} that only had file extension as difference from {paths} (i.e. .nii vs .nii.gz with same subject+session+datatype+entities+suffix)"
                    )

        if image_scans_info:
            self._populate_image_scans_info_from_tsv()

        return unhandled_entries


# Populated from sub-<label>/sub-<label>_sessions.tsv
# FIXME: https://github.com/python/mypy/issues/18176
class SessionInfo(TypedDict, extra_items=Any):  # type: ignore
    """
    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#sessions-file>`__
    """

    # TODO: actual date type (handle BIDS units)
    acq_time: NotRequired[str]
    pathology: NotRequired[str]
