from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Iterable, Optional

from pandas import DataFrame

from ._tsv_utils import _read_tsv_as_df, _write_rows_to_tsv
from .entities import Entities, EntitiesLike
from .image import Image, ImageScanInfo
from .types import BIDSException, DataType, FileExtension, SessionId, Suffix


@dataclass
class Session:
    parent_subject: subject.Subject = field(repr=False, compare=False)

    id: SessionId
    info: SessionInfo
    _images: dict[DataType, list[Image]] = field(default_factory=lambda: {})

    def _get_full_path(self) -> Path:
        return self.parent_subject._get_full_path() / f"{self.id}"

    def images_by_data_type(self, data_type: str | DataType) -> Iterable[Image]:
        return self._images.get(DataType(data_type)) or []

    def all_images(self) -> Iterable[Image]:
        """Returns all the images that are part of this session"""
        for images in self._images.values():
            yield from images

    def images_count(self, data_type: Optional[DataType] = None) -> int:
        """
        Parameters
        ----------
        data_type : Optional[DataType], default=None
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

    def _write_to_folder(self):
        session_path = self._get_full_path()
        try:
            os.mkdir(session_path)
        except FileExistsError:
            raise BIDSException(
                f"BIDS session folder {session_path} can't be written as it already exists"
            )
        except FileNotFoundError:
            raise BIDSException(
                f"BIDS session folder {session_path} can't be written as one of its parent folders is missing"
            )

    def _add_image(
        self,
        data_type: DataType,
        nifti_extension: FileExtension,
        entities: Entities,
        suffix: Optional[Suffix],
        scan_info: Optional[ImageScanInfo],
    ) -> Image:
        if not nifti_extension.is_nifti():
            raise BIDSException(
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

    def write_images(self) -> ImagesWriter:
        """
        Start the images writing process for this session. This must happen after calling :py:meth:`BIDSDataset.write_to_folder <clinicaio.dataset.BIDSDataset.write_to_folder>`.

        See also
        --------
        * :py:class:`ImagesWriter`
        """
        return ImagesWriter(session=self)

    @cached_property
    def _scans_tsv_file_name(self) -> str:
        return f"{self.parent_subject.id}_{self.id}_scans.tsv"

    def populate_image_scans_info_from_df(self, scans_tsv_df: DataFrame):
        """
        Populates the images informations from the given dataframe.
        The dataframe must have a ``filename`` column which corresponds to
        the relative path of the image file relative to its parent session/this session,
        e.g. ``<data type>/sub-..._ses-..._<.....>.nii.gz``. The corresponding
        Image must already be present in this session. The other columns
        will be used as informations for the image at hand: they will not be
        merged with the existing ones, instead they'll be replaced entirely.

        Warnings
        --------
        You should only ever use this function if it is more convenient enough
        for your use case when you are writing a new BIDS dataset. Filling-in
        the information directly from :py:meth:`ImagesWriter.write_image` should be favored.
        """
        if "filename" not in scans_tsv_df.columns:
            raise BIDSException(f"dataframe did not have required filename column")

        sub_ses_prefix = f"{self.parent_subject.id}_{self.id}_"

        infos: list[dict[str, Any]] = scans_tsv_df.to_dict(orient="records")  # type: ignore
        for info in infos:
            image_filename = info.pop("filename", None)
            if image_filename is None:
                continue
            try:
                data_type, image_basename = str(image_filename).split(
                    sep="/", maxsplit=1
                )
            except ValueError:
                raise BIDSException(
                    f"expected image/scan filename of format <data_type>/<...> for {image_filename} in dataframe"
                )

            try:
                data_type = DataType(data_type)
            except ValueError:
                raise BIDSException(
                    f"expected valid data type as first folder of filename {image_filename} in dataframe"
                )

            if not image_basename.startswith(sub_ses_prefix):
                raise BIDSException(
                    f"expected image basename {image_basename} of filename {image_filename} in dataframe to have prefix {sub_ses_prefix}"
                )

            after_sub_ses = image_basename.removeprefix(sub_ses_prefix)
            try:
                filename_components = Image._parse_filename_components(after_sub_ses)
            except BIDSException as e:
                raise BIDSException(
                    f"found invalid image filename {image_filename} in dataframe: {e}"
                )

            if filename_components is None:
                raise BIDSException(
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
                raise BIDSException(
                    f"could not find image for filename {image_filename} in dataframe"
                )

            image.scan_info = ImageScanInfo(
                other_fields={} if all(v is None for v in info) else info
            )

    # read the session's _scans.tsv and fill out scan info for all images
    def _populate_image_scans_info_from_tsv(self):
        scans_tsv_path = self._get_full_path() / self._scans_tsv_file_name
        if not os.path.exists(scans_tsv_path):
            return

        scans_tsv_df = _read_tsv_as_df(scans_tsv_path)
        try:
            self.populate_image_scans_info_from_df(scans_tsv_df)
        except BIDSException as e:
            raise BIDSException(
                f"could not populate images scans info from TSV file {scans_tsv_path}: {e}"
            )

    def _populate_images_from_folder(self, *, image_scans_info: bool) -> list[str]:
        unhandled_entries: list[str] = []

        # Populate the session's images, per-datatype
        for child in os.scandir(self._get_full_path()):
            if child.name == self._scans_tsv_file_name:
                continue

            try:
                data_type = DataType(child.name)
            except ValueError:
                unhandled_entries.append(child.path)
                continue

            if not child.is_dir():
                raise BIDSException(
                    f"Found data type entry {data_type} that was not a directory"
                )

            for child_image in os.scandir(child.path):
                sub_ses_prefix = f"{self.parent_subject.id}_{self.id}_"
                if not child_image.name.startswith(sub_ses_prefix):
                    raise BIDSException(
                        f"expected {data_type}/{child_image.name} "
                        f"filename to start with {sub_ses_prefix} due to its placement in the BIDS directory hierarchy"
                    )

                after_sub_ses = child_image.name.removeprefix(sub_ses_prefix)

                try:
                    filename_components = Image._parse_filename_components(
                        after_sub_ses
                    )
                except BIDSException as e:
                    raise BIDSException(
                        f"Found invalid image filename {child_image.name} in folder {data_type}: {e}"
                    )

                # For now we just exclude any file without a file extension, without raising
                # an error.
                if filename_components is None:
                    unhandled_entries.append(child_image.path)
                    continue
                entities, suffix, extension = filename_components

                # All the usual filename validation is done for non-NIFTI files, so that
                # we do not end up in a situation where the companion files (.json, etc.)
                # are inaccessible due to invalid naming. We do not store those companion
                # files however: we just validate the paths, but only actually accessing
                # such companion files by their paths will tell whether a particular one exists.
                if not extension.is_nifti():
                    continue

                self._add_image(
                    data_type=data_type,
                    nifti_extension=extension,
                    entities=entities,
                    suffix=suffix,
                    scan_info=None,
                )

        if image_scans_info:
            self._populate_image_scans_info_from_tsv()

        return unhandled_entries


@dataclass
class ImagesWriter:
    """
    Automatic image scan info writer.

    The goal of this class is to automatically write the session's ``*_scans.tsv`` file with all the information
    provided in each image's scan_info. This is necessary due to the tabular nature of the file, and the missing
    guarantee that all images will provide the same columns.

    Examples
    --------

    `Jupyter BIDS writing example <demo_BIDS_write_images.ipynb>`__

    TODO: use nbsphinx or myst-nb to display the notebook **inline** here instead of copy pasting or moving it
    """

    session: Session

    def write_image(
        self,
        data_type: DataType,
        nifti_extension: FileExtension,
        entities: EntitiesLike,
        suffix: Optional[Suffix | str],
        scan_info: Optional[ImageScanInfo],
    ) -> Image:
        if suffix is not None:
            suffix = suffix if isinstance(suffix, Suffix) else Suffix(suffix)

        image = self.session._add_image(
            data_type, nifti_extension, Entities.from_any(entities), suffix, scan_info
        )

        session_path = self.session._get_full_path()

        data_type_folder_path = session_path / f"{data_type}"
        try:
            os.mkdir(data_type_folder_path)
        except FileExistsError:
            pass
        except FileNotFoundError:
            raise BIDSException(
                f"one of the parent folders of {data_type_folder_path} does not exist. Make sure to create the subject and session folders first."
            )

        return image

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Do not write the scans.tsv if an error occurred
        if all(v is None for v in [exc_type, exc, tb]):
            session_path = self.session._get_full_path()
            scans_tsv_path = session_path / self.session._scans_tsv_file_name

            rows = (
                image.scan_info.all_fields()
                | {
                    "filename": str(
                        image.get_nifti_image_path().relative_to(session_path)
                    )
                }
                for image in self.session.all_images()
                if not image.scan_info.is_empty()
            )

            # We need to write the scans.tsv at the very end of the ImagesWriter "with ...: " scope because all the images
            # may not have the same fields, so the TSV header must be the union of all of them done once we know all
            # the images to write
            _write_rows_to_tsv(
                scans_tsv_path,
                first_column_name="filename",
                rows=rows,
            )


# Populated from sub-<label>/sub-<label>_sessions.tsv
@dataclass
class SessionInfo:
    """
    `BIDS specification <https://bids-specification.readthedocs.io/en/stable/modality-agnostic-files/data-summary-files.html#sessions-file>`__
    """

    # TODO: actual date type (handle BIDS units)
    acquisition_time: Optional[str]
    pathology: Optional[str]
    other_fields: dict[str, Any]

    def all_fields(self) -> dict[str, Any]:
        return self.other_fields | {
            "acq_time": self.acquisition_time,
            "pathology": self.pathology,
        }

    # It's preferable to avoid having two None-like SessionInfo: the real None stored in
    # session.info, and a SessionInfo with all None and {} fields. As such, just always
    # store a non optional SessionInfo in session.info, and check here if any field is actually
    # set. This is notably necessary to avoid having code that relies on the info being None
    # when there are some TSV files that have a row with all n/a values (except for the ID column)
    def is_empty(self) -> bool:
        return len(self.other_fields) == 0 and all(
            v is None for v in [self.acquisition_time, self.pathology]
        )


from . import subject
