"""
The `Brain Imaging Data Structure (BIDS) <https://bids-specification.readthedocs.io/en/stable/>`__
format defines a way to organize and describe brain imaging data, which themselves are in NIFTI format.
Concretely BIDS defines a standard way to organize and name folders and image files as well as defining
tabular (TSV) and JSON metadata that supplements them.

The current targeted BIDS version is 1.11.1

This library provides support for querying and traversing such BIDS datasets, as well as writing them.
However editing existing BIDS datasets is not supported as-is.

Here is a sample folder structure with proper filenaming matching the BIDS specification:

.. code-block:: text

    .
    ├── dataset_description.json
    ├── participants.tsv
    ├── README
    ├── sub-AIBL993
    │   ├── ses-M00
    │   │   ├── anat
    │   │   │   ├── sub-AIBL993_ses-M00_T1w.json
    │   │   │   └── sub-AIBL993_ses-M00_T1w.nii.gz
    │   │   └── sub-AIBL993_ses-M00_scans.tsv
    │   ├── ses-M18
    │   │   ├── anat
    │   │   │   ├── sub-AIBL993_ses-M18_T1w.json
    │   │   │   └── sub-AIBL993_ses-M18_T1w.nii.gz
    │   │   ├── pet
    │   │   │   ├── sub-AIBL993_ses-M18_task-rest_acq-pib_pet.json
    │   │   │   └── sub-AIBL993_ses-M18_task-rest_acq-pib_pet.nii.gz
    │   │   └── sub-AIBL993_ses-M18_scans.tsv
    │   └── sub-AIBL993_sessions.tsv

Organization
------------

A :py:class:`~clinicaio.dataset.BIDSDataset` is first organized by :py:class:`~clinicaio.subject.Subject`
(also referred to as participant). Each subject has participated in one or more
:py:class:`~clinicaio.session.Session` where brain images were acquired. Each :py:class:`~clinicaio.image.Image`
of the session can then be used to access its NIFTI image path (:py:meth:`~clinicaio.image.Image.get_nifti_image_path`)
or one of its companion files' path (:py:meth:`~clinicaio.image.Image.get_image_companion_path`) which are
files that provide extra information on the image that are not included in the NIFTI image file itself.
These companion files are notably produced when converting DICOM to NIFTI, as the former provides a wider set of
metadata than the later.

Reading
-------

Use :py:func:`~clinicaio.dataset.BIDSDataset.populate_from_dir` to read an existing BIDS dataset directory:
it will walk the entire BIDS folder hierarchy to build a tree of Python data-structures/classes representing each
subject/session/image that were found, allowing subsequent queries and generally traversing the dataset. Note that
this library supports extracting the subject/session/images information that are available in TSV files: you should
only enable them individually if you need the data, since reading those TSV files takes a substantial time compared
to reading the rest of the BIDS dataset.

Querying
--------

Images can be queried from a dataset by building an :py:class:`~clinicaio.image_query.ImageQuery` and using
:py:meth:`~clinicaio.dataset.BIDSDataset.query_images`, :py:meth:`~clinicaio.dataset.BIDSDataset.query_images_nifti_paths`
or :py:meth:`~clinicaio.dataset.BIDSDataset.query_images_companions_paths` on the dataset. This works well for
the case where you want to find images based on the subject and/or session they are part of, and/or the
data type/entities/suffix they have.

However for queries that aren't so image-focused you may need to traverse the BIDS dataset manually, which offers
greater flexibility in terms of queries (e.g. finding all sessions that have both a T1 and a PET image for
the same session). You will want to use the various specific methods (e.g. :py:meth:`~clinicaio.dataset.BIDSDataset.subject_by_id`)
instead of manually iterating through the various ``.all_*()`` methods until you find what you're looking for:
for example :py:meth:`~clinicaio.dataset.BIDSDataset.subject_by_id` will be ``O(1)`` while manually iterating with
a ``for`` loop will be ``O(n)``.

Examples
--------

* :doc:`/examples/assorted_queries`

Writing
-------

This library's writing side is made to write datasets from scratch, not to edit existing ones. As such, you
must first create a new dataset with :py:func:`~clinicaio.dataset.BIDSDataset` then you need to create the
various subjects and sessions with :py:meth:`~clinicaio.dataset.BIDSDataset.add_subject` and
:py:meth:`~clinicaio.subject.Subject.add_session` respectively. The images themselves need to be added using
:py:meth:`~clinicaio.session.Session.write_image`: it will return the image object, which you should use to
get its NIFTI path (and companion files paths if applicable) and actually write those files yourself, otherwise
the BIDS will not be valid. Once this is done the dataset can be written using
:py:meth:`~clinicaio.dataset.BIDSDataset.write_to_folder` and :py:meth:`~clinicaio.dataset.BIDSDataset.write_root_file`
on the dataset.

Examples
--------

* :doc:`/examples/demo_BIDS_write_images`

Re-exports
----------

This library re-exports all classes that you would ever have to refer to manually, meaning they are
accessible as e.g. ``from clinicaio import BIDSDataset, ImageQuery`` directly instead of ``from clinicaio.dataset import BIDSDataset; from clinicaio.image_query import ImageQuery``.

Installation
------------

ClinicaIO can be installed from PyPI as ``clinicaio``. For example with poetry: ``poetry add clinicaio``.

"""

from .dataset import BIDSDataset
from .dataset_description import BIDSDatasetDescription, BIDSDatasetType
from .entities import Entities
from .image import Image, ImageScanInfo
from .image_query import ImageQuery
from .session import Session, SessionInfo
from .subject import Subject, SubjectInfo
from .types import BIDSException, DataType, FileExtension
