"""
The `Brain Imaging Data Structure (BIDS) <https://bids-specification.readthedocs.io/en/stable/>`__
format defines a way to organize and describe brain imaging data, which themselves are in NIFTI format.
Concretely BIDS defines a standard way to organize and name folders and image files as well as defining
tabular (TSV) and JSON metadata that supplements them.

This library provides support for querying and traversing such BIDS datasets, as well as writing them.

Organization
------------

A :py:class:`~clinicaio.dataset.BIDSDataset` is first organized by :py:class:`~clinicaio.dataset.Subject`
(also referred to as participant). Each subject has participated in one or more
:py:class:`~clinicaio.dataset.Session` where brain images were made. Each :py:class:`~clinicaio.dataset.Image`
of the session can then be used to access its NIFTI image path (:py:meth:`~clinicaio.dataset.Image.get_nifti_image_path`)
or one of its companion files' path (:py:meth:`~clinicaio.dataset.Image.get_image_companion_file_path`) which are
files that provide extra information on the image that are not included in the NIFTI image file itself, based
on their file extension. This is notably the case when converting DICOM to NIFTI, as the former provides a wider set of
metadata than the later (at the cost of complexity).

Reading
-------

Use :py:func:`clinicaio.dataset.BIDSDataset.populate_from_dir` to read an existing BIDS dataset directory.

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
instead of manually filtering from the various ``.all_*()`` methods as it provides far greater performance due
to internal data structures.

Writing
-------

This library's writing side is made to write datasets from scratch, not to edit existing ones. As such, you
must first create a new dataset with :py:func:`~clinicaio.dataset.BIDSDataset` then you need to create the
various subjects and sessions with :py:meth:`~clinicaio.dataset.BIDSDataset.add_subject` and
:py:meth:`~clinicaio.dataset.Subject.add_session` respectively. Once this is done the dataset can be written
using :py:meth:`~clinicaio.dataset.BIDSDataset.write_to_folder` and :py:meth:`~clinicaio.dataset.BIDSDataset.write_root_file`
on the dataset. The images themselves need to be added using :py:meth:`~clinicaio.dataset.Session.write_images` then
:py:meth:`~clinicaio.dataset.ImagesWriter.write_image`: it will return the image object, which you should use to
get its NIFTI path (and companion files paths if applicable) and actually write those files yourself, otherwise
the BIDS will not be valid.
"""
