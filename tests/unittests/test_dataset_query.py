from pathlib import Path
from re import escape

import pytest
from _utils import _get_dataset_description, _setup_dataset_description
from pyfakefs.fake_filesystem import FakeFilesystem

from clinicaio.dataset import BIDSDataset
from clinicaio.image_query import ImageQuery
from clinicaio.types import (
    BIDSDataType,
    BIDSException,
    FileExtension,
    SessionId,
    SubjectId,
)


@pytest.fixture
def fakefs(fs):
    yield fs


all_paths = frozenset(
    [
        "sub-1/ses-A/anat/sub-1_ses-A_trc-18FFDG_task-rest_desc-foobar_sfx.nii.gz",
        "sub-1/ses-A/anat/sub-1_ses-A_trc-18FFDG_task-rest_desc-foobar.nii.gz",
        "sub-1/ses-A/anat/sub-1_ses-A_trc-11CPIB_task-rest_desc-foobar.nii.gz",
        "sub-1/ses-A/anat/sub-1_ses-A_trc-18FFDG_task-rest.nii",
        "sub-1/ses-A/anat/sub-1_ses-A_task-rest_desc-foobar_sfx.nii.gz",
        "sub-1/ses-A/anat/sub-1_ses-A_sfx.nii.gz",
        "sub-1/ses-A/pet/sub-1_ses-A_trc-18FFDG_task-rest_desc-foobar_sfx.nii.gz",
        "sub-1/ses-A/pet/sub-1_ses-A_trc-18FFDG_task-rest_desc-foobar.nii.gz",
        "sub-1/ses-A/pet/sub-1_ses-A_trc-11CPIB_task-rest_desc-foobar.nii.gz",
        "sub-1/ses-A/pet/sub-1_ses-A_trc-18FFDG_task-rest.nii",
        "sub-1/ses-A/pet/sub-1_ses-A_task-rest_desc-foobar_sfx.nii.gz",
        "sub-1/ses-A/pet/sub-1_ses-A_sfx.nii.gz",
        "sub-1/ses-B/anat/sub-1_ses-B_trc-18FFDG_task-rest_desc-foobar_sfx.nii.gz",
        "sub-1/ses-B/anat/sub-1_ses-B_trc-18FFDG_task-rest_desc-foobar.nii.gz",
        "sub-1/ses-B/anat/sub-1_ses-B_trc-11CPIB_task-rest_desc-foobar.nii.gz",
        "sub-1/ses-B/anat/sub-1_ses-B_trc-18FFDG_task-rest.nii",
        "sub-1/ses-B/anat/sub-1_ses-B_task-rest_desc-foobar_sfx.nii.gz",
        "sub-1/ses-B/anat/sub-1_ses-B_sfx.nii.gz",
        "sub-1/ses-B/pet/sub-1_ses-B_trc-18FFDG_task-rest_desc-foobar_sfx.nii.gz",
        "sub-1/ses-B/pet/sub-1_ses-B_trc-18FFDG_task-rest_desc-foobar.nii.gz",
        "sub-1/ses-B/pet/sub-1_ses-B_trc-11CPIB_task-rest_desc-foobar.nii.gz",
        "sub-1/ses-B/pet/sub-1_ses-B_trc-18FFDG_task-rest.nii",
        "sub-1/ses-B/pet/sub-1_ses-B_task-rest_desc-foobar_sfx.nii.gz",
        "sub-1/ses-B/pet/sub-1_ses-B_sfx.nii.gz",
        "sub-2/ses-A/anat/sub-2_ses-A_trc-18FFDG_task-rest_desc-foobar_sfx.nii.gz",
        "sub-2/ses-A/anat/sub-2_ses-A_trc-18FFDG_task-rest_desc-foobar.nii.gz",
        "sub-2/ses-A/anat/sub-2_ses-A_trc-11CPIB_task-rest_desc-foobar.nii.gz",
        "sub-2/ses-A/anat/sub-2_ses-A_trc-18FFDG_task-rest.nii",
        "sub-2/ses-A/anat/sub-2_ses-A_task-rest_desc-foobar_sfx.nii.gz",
        "sub-2/ses-A/anat/sub-2_ses-A_sfx.nii.gz",
        "sub-2/ses-A/pet/sub-2_ses-A_trc-18FFDG_task-rest_desc-foobar_sfx.nii.gz",
        "sub-2/ses-A/pet/sub-2_ses-A_trc-18FFDG_task-rest_desc-foobar.nii.gz",
        "sub-2/ses-A/pet/sub-2_ses-A_trc-11CPIB_task-rest_desc-foobar.nii.gz",
        "sub-2/ses-A/pet/sub-2_ses-A_trc-18FFDG_task-rest.nii",
        "sub-2/ses-A/pet/sub-2_ses-A_task-rest_desc-foobar_sfx.nii.gz",
        "sub-2/ses-A/pet/sub-2_ses-A_sfx.nii.gz",
        "sub-2/ses-B/anat/sub-2_ses-B_trc-18FFDG_task-rest_desc-foobar_sfx.nii.gz",
        "sub-2/ses-B/anat/sub-2_ses-B_trc-18FFDG_task-rest_desc-foobar.nii.gz",
        "sub-2/ses-B/anat/sub-2_ses-B_trc-11CPIB_task-rest_desc-foobar.nii.gz",
        "sub-2/ses-B/anat/sub-2_ses-B_trc-18FFDG_task-rest.nii",
        "sub-2/ses-B/anat/sub-2_ses-B_task-rest_desc-foobar_sfx.nii.gz",
        "sub-2/ses-B/anat/sub-2_ses-B_sfx.nii.gz",
        "sub-2/ses-B/pet/sub-2_ses-B_trc-18FFDG_task-rest_desc-foobar_sfx.nii.gz",
        "sub-2/ses-B/pet/sub-2_ses-B_trc-18FFDG_task-rest_desc-foobar.nii.gz",
        "sub-2/ses-B/pet/sub-2_ses-B_trc-11CPIB_task-rest_desc-foobar.nii.gz",
        "sub-2/ses-B/pet/sub-2_ses-B_trc-18FFDG_task-rest.nii",
        "sub-2/ses-B/pet/sub-2_ses-B_task-rest_desc-foobar_sfx.nii.gz",
        "sub-2/ses-B/pet/sub-2_ses-B_sfx.nii.gz",
    ]
)


# NOTE: for the purpose of this module, the whole dataset and filesystem are assumed
# to be written once as part of this fixture, but to never be touched again after.
@pytest.fixture(scope="module")
def dataset(fs_module: FakeFilesystem):
    bids_path = Path("/tmp/bids_test_all_queries")

    _setup_dataset_description(fs_module, bids_path)

    for sub in ["sub-1", "sub-2"]:
        for ses in ["ses-A", "ses-B"]:
            for data_type in ["anat", "pet"]:
                dir_path = bids_path / sub / ses / data_type

                # all entities and suffix
                fs_module.create_file(
                    dir_path
                    / f"{sub}_{ses}_trc-18FFDG_task-rest_desc-foobar_sfx.nii.gz"
                )
                # all entities but no suffix
                fs_module.create_file(
                    dir_path / f"{sub}_{ses}_trc-18FFDG_task-rest_desc-foobar.nii.gz"
                )
                # all entities but one changed, without suffix
                fs_module.create_file(
                    dir_path / f"{sub}_{ses}_trc-11CPIB_task-rest_desc-foobar.nii.gz"
                )
                # One less entity, no suffix, different file extension
                fs_module.create_file(
                    dir_path / f"{sub}_{ses}_trc-18FFDG_task-rest.nii"
                )
                # less entities, keep suffix
                fs_module.create_file(
                    dir_path / f"{sub}_{ses}_task-rest_desc-foobar_sfx.nii.gz"
                )
                # no entities, keep suffix
                fs_module.create_file(dir_path / f"{sub}_{ses}_sfx.nii.gz")

    yield BIDSDataset.populate_from_dir(
        bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
    )


@pytest.mark.parametrize(
    ["query", "image_paths", "paths_count"],
    [
        (ImageQuery(), all_paths, len(all_paths)),
        (
            ImageQuery(subjects=["sub-1", "sub-2"], sessions=["ses-A", "ses-B"]),
            all_paths,
            len(all_paths),
        ),
        # A subject or session that does not exist at all should not cause any issue
        (
            ImageQuery(
                subjects=["sub-1", "sub-2", "sub-3"], sessions=["ses-A", "ses-B"]
            ),
            all_paths,
            len(all_paths),
        ),
        (
            ImageQuery(
                subjects=["sub-1", "sub-2"], sessions=["ses-A", "ses-B", "ses-C"]
            ),
            all_paths,
            len(all_paths),
        ),
        (
            ImageQuery(subjects=["sub-1"]),
            {path for path in all_paths if path.startswith("sub-1")},
            len(all_paths) / 2,
        ),
        (
            ImageQuery(sessions=["ses-A"]),
            {path for path in all_paths if "ses-A" in path},
            len(all_paths) / 2,
        ),
        (
            ImageQuery(data_type=BIDSDataType.ANAT),
            {path for path in all_paths if "anat" in path},
            len(all_paths) / 2,
        ),
        # This also checks that matching by entity is done for the entire key/value pair, not just the key
        (
            ImageQuery(entities={"trc": "18FFDG"}),
            {path for path in all_paths if "trc-18FFDG" in path},
            len(all_paths) / 2,
        ),
        (
            ImageQuery(suffix="sfx"),
            {path for path in all_paths if "_sfx" in path},
            len(all_paths) / 2,
        ),
        # Note that that this includes images that do not have the entire same set of entities, but that have the
        # same given subset of entities (which is why it's tested specifically)
        (
            ImageQuery(entities={"task": "rest", "trc": "18FFDG"}),
            {
                path
                for path in all_paths
                if "task-rest" in path and "trc-18FFDG" in path
            },
            len(all_paths) / 2,
        ),
        # The most specific query that can be done with this API
        (
            ImageQuery(
                subjects=["sub-1"],
                sessions=["ses-A"],
                data_type=BIDSDataType.PET,
                entities={"trc": "18FFDG", "task": "rest", "desc": "foobar"},
                suffix="sfx",
            ),
            {
                "sub-1/ses-A/pet/sub-1_ses-A_trc-18FFDG_task-rest_desc-foobar_sfx.nii.gz",
            },
            1,
        ),
        # Different order for the entities: the order of the provided entities for the query do not matter,
        # however the image's entities themselves *are* ordered (with the corresponding BIDS rules),
        # so the output path should not change when the queried entities order changes.
        (
            ImageQuery(
                subjects=["sub-1"],
                sessions=["ses-A"],
                data_type=BIDSDataType.PET,
                entities={
                    "desc": "foobar",
                    "task": "rest",
                    "trc": "18FFDG",
                },
                suffix="sfx",
            ),
            {
                "sub-1/ses-A/pet/sub-1_ses-A_trc-18FFDG_task-rest_desc-foobar_sfx.nii.gz",
            },
            1,
        ),
        # Entities (and other filename components) are case sensitive
        # https://bids-specification.readthedocs.io/en/stable/common-principles.html#case-collision-intolerance
        (
            ImageQuery(
                subjects=["sub-1"],
                sessions=["ses-A"],
                data_type=BIDSDataType.PET,
                # capital entity value
                entities={
                    "desc": "foobar",
                    "task": "REST",
                    "trc": "18FFDG",
                },
                suffix="sfx",
            ),
            set(),
            0,
        ),
        (
            ImageQuery(
                subjects=["sub-1"],
                sessions=["ses-A"],
                data_type=BIDSDataType.PET,
                entities={
                    "desc": "foobar",
                    "task": "rest",
                    "trc": "18FFDG",
                },
                # capital suffix
                suffix="SFX",
            ),
            set(),
            0,
        ),
        (
            ImageQuery(
                subjects=["sub-1"],
                # non-capital session ID/label
                sessions=["ses-a"],
                data_type=BIDSDataType.PET,
                entities={
                    "desc": "foobar",
                    "task": "rest",
                    "trc": "18FFDG",
                },
                suffix="SFX",
            ),
            set(),
            0,
        ),
    ],
)
def test_query_images(
    dataset: BIDSDataset, query: ImageQuery, image_paths: set[str], paths_count: int
):
    assert len(image_paths) == paths_count

    queried_paths = [
        str(image.get_nifti_image_path().relative_to(dataset.bids_path))
        for image in dataset.query_images(query)
    ]
    assert queried_paths == [
        str(nifti_path.relative_to(dataset.bids_path))
        for nifti_path in dataset.query_images_nifti_paths(query)
    ]
    images_count = len(queried_paths)
    queried_paths = set(queried_paths)
    # The paths are compared as sets because the order that the images are yielded with does
    # not matter. However, it does matter that it does not yield several times the same images,
    # hence the length check.
    assert len(queried_paths) == images_count
    assert queried_paths == image_paths


def test_query_suffix_wildcard(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test_suffix_wildcard")

    _setup_dataset_description(fakefs, bids_path)
    fakefs.create_file(
        bids_path
        / "sub-1/ses-A/anat/sub-1_ses-A_task-rest_trc-18FFDG_magnitude1.nii.gz"
    )
    fakefs.create_file(
        bids_path / "sub-1/ses-A/anat/sub-1_ses-A_task-rest_trc-11CPIB_magnitude2.nii"
    )
    fakefs.create_file(
        bids_path
        / "sub-1/ses-B/anat/sub-1_ses-B_task-rest_trc-18FFDG_magnitude3.nii.gz"
    )
    fakefs.create_file(
        bids_path
        / "sub-1/ses-B/anat/sub-1_ses-B_task-rest_trc-18FFDG_magnitude8238.nii"
    )
    fakefs.create_file(
        bids_path / "sub-1/ses-B/anat/sub-1_ses-B_task-rest_trc-18FFDG_magnitude.nii.gz"
    )
    # all those next ones are not supposed to be found by the image query
    fakefs.create_file(
        bids_path
        / "sub-1/ses-B/anat/sub-1_ses-B_task-rest_trc-18FFDG_Magnitude7.nii.gz"
    )
    fakefs.create_file(
        bids_path
        / "sub-1/ses-B/anat/sub-1_ses-B_task-rest_trc-18FFDG_Amagnitude7.nii.gz"
    )
    fakefs.create_file(
        bids_path / "sub-1/ses-B/anat/sub-1_ses-B_task-rest_trc-18FFDG_magnitud.nii.gz"
    )
    fakefs.create_file(
        bids_path / "sub-2/ses-A/anat/sub-2_ses-A_task-rest_trc-11CPIB_magnitude4.nii"
    )

    dataset = BIDSDataset.populate_from_dir(
        bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
    )

    expected_paths = [
        "sub-1/ses-A/anat/sub-1_ses-A_task-rest_trc-18FFDG_magnitude1.nii.gz",
        "sub-1/ses-A/anat/sub-1_ses-A_task-rest_trc-11CPIB_magnitude2.nii",
        "sub-1/ses-B/anat/sub-1_ses-B_task-rest_trc-18FFDG_magnitude3.nii.gz",
        "sub-1/ses-B/anat/sub-1_ses-B_task-rest_trc-18FFDG_magnitude8238.nii",
        "sub-1/ses-B/anat/sub-1_ses-B_task-rest_trc-18FFDG_magnitude.nii.gz",
    ]
    image_paths = dataset.query_images_nifti_paths(
        ImageQuery(subjects=["sub-1"], suffix="magnitude*")
    )
    assert sorted([str(path.relative_to(bids_path)) for path in image_paths]) == sorted(
        expected_paths
    )


def test_query_companion_files(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test_companion")

    _setup_dataset_description(fakefs, bids_path)

    # NIFTI+TSV+JSON
    fakefs.create_file(bids_path / "sub-1/ses-A/anat/sub-1_ses-A_task-rest_sfx1.nii.gz")
    fakefs.create_file(bids_path / "sub-1/ses-A/anat/sub-1_ses-A_task-rest_sfx1.tsv")
    fakefs.create_file(bids_path / "sub-1/ses-A/anat/sub-1_ses-A_task-rest_sfx1.json")
    # NIFTI+JSON but no TSV
    fakefs.create_file(bids_path / "sub-1/ses-A/anat/sub-1_ses-A_task-rest_sfx2.nii.gz")
    fakefs.create_file(bids_path / "sub-1/ses-A/anat/sub-1_ses-A_task-rest_sfx2.json")
    # NIFTI+TSV but no JSON. Also no session level folder
    fakefs.create_file(bids_path / "sub-2/anat/sub-2_task-rest_sfx1.nii.gz")
    fakefs.create_file(bids_path / "sub-2/anat/sub-2_task-rest_sfx1.tsv")
    # NIFTI+JSON but no TSV
    fakefs.create_file(bids_path / "sub-2/anat/sub-2_task-rest_sfx2.nii.gz")
    fakefs.create_file(bids_path / "sub-2/anat/sub-2_task-rest_sfx2.json")
    # Only NIFTI
    fakefs.create_file(bids_path / "sub-2/anat/sub-2_task-rest_sfx3.nii.gz")

    global checked_unhandled_entries
    checked_unhandled_entries = False

    def unhandled_entries(paths: list[str]):
        assert len(paths) == 0, repr(paths)
        global checked_unhandled_entries
        checked_unhandled_entries = True

    dataset = BIDSDataset.populate_from_dir(
        bids_path,
        subjects_info=False,
        sessions_info=False,
        image_scans_info=False,
        report_unhandled_entries=unhandled_entries,
    )
    assert checked_unhandled_entries

    assert len(list(dataset.all_images())) == 5
    assert sorted(
        dataset.query_images_companions_paths(
            ImageQuery(suffix="sfx*"),
            FileExtension.TSV,
            skip_missing=True,
        )
    ) == [
        bids_path / "sub-1/ses-A/anat/sub-1_ses-A_task-rest_sfx1.tsv",
        bids_path / "sub-2/anat/sub-2_task-rest_sfx1.tsv",
    ]

    assert sorted(
        dataset.query_images_companions_paths(
            ImageQuery(suffix="sfx*"),
            FileExtension.TSV,
            skip_missing=False,
        )
    ) == [
        bids_path / "sub-1/ses-A/anat/sub-1_ses-A_task-rest_sfx1.tsv",
        bids_path / "sub-1/ses-A/anat/sub-1_ses-A_task-rest_sfx2.tsv",
        bids_path / "sub-2/anat/sub-2_task-rest_sfx1.tsv",
        bids_path / "sub-2/anat/sub-2_task-rest_sfx2.tsv",
        bids_path / "sub-2/anat/sub-2_task-rest_sfx3.tsv",
    ]


def test_query_cross_versus_cartesian_product(fakefs: FakeFilesystem):
    bids_path = Path("/tmp/bids_test_product")

    _setup_dataset_description(fakefs, bids_path)

    """
    Depending on the case, either the cross-product of subject and session pairs is
    wanted (query.sub_ses is used):

     abc <== subjects
    1xx_
    2_x_
    3___
    ^
    sessions

    with query.sub_ses={a: {1}, b: {1, 2}}

    Or the cartesian-product (which can/could be expressed as a cross-product but it's inconvenient/inefficient)
    by defining both query.subjects and query.sessions:

     abc <== subjects
    1xx_
    2xx_
    3___
    ^
    sessions

    with query.subjects={a, b} and query.sessions={1, 2}

    But having both set at the same time does not make sense (hence the next test).
    """

    paths = []

    for sub in (f"sub-{c}" for c in "abc"):
        for ses in (f"ses-{n}" for n in [1, 2, 3]):
            path = bids_path / sub / ses / "anat" / f"{sub}_{ses}_sfx.nii.gz"
            fakefs.create_file(path)
            paths.append(path)

    assert len(paths) == 9

    dataset = BIDSDataset.populate_from_dir(
        bids_path, subjects_info=False, sessions_info=False, image_scans_info=False
    )

    assert sorted(
        dataset.query_images_nifti_paths(
            ImageQuery(sub_ses={"sub-a": {"ses-1"}, "sub-b": {"ses-1", "ses-2"}})
        )
    ) == [
        bids_path / "sub-a/ses-1/anat/sub-a_ses-1_sfx.nii.gz",
        bids_path / "sub-b/ses-1/anat/sub-b_ses-1_sfx.nii.gz",
        bids_path / "sub-b/ses-2/anat/sub-b_ses-2_sfx.nii.gz",
    ]

    assert sorted(
        dataset.query_images_nifti_paths(
            ImageQuery(subjects={"sub-a", "sub-b"}, sessions={"ses-1", "ses-2"})
        )
    ) == [
        bids_path / "sub-a/ses-1/anat/sub-a_ses-1_sfx.nii.gz",
        bids_path / "sub-a/ses-2/anat/sub-a_ses-2_sfx.nii.gz",
        bids_path / "sub-b/ses-1/anat/sub-b_ses-1_sfx.nii.gz",
        bids_path / "sub-b/ses-2/anat/sub-b_ses-2_sfx.nii.gz",
    ]


@pytest.mark.parametrize(
    ["sub_ses", "subjects", "sessions"],
    [
        ({"sub-A": {"ses-1", "ses-2"}, "sub-B": {"ses-1", "ses-2"}}, {"sub-1"}, set()),
        ({"sub-A": {"ses-1", "ses-2"}, "sub-B": {"ses-1", "ses-2"}}, set(), {"ses-1"}),
        (
            {"sub-A": {"ses-1", "ses-2"}, "sub-B": {"ses-1", "ses-2"}},
            {"sub-A"},
            {"ses-1"},
        ),
    ],
)
def test_query_cross_xor_cartesian_product(
    sub_ses: dict[SubjectId, set[SessionId]],
    subjects: set[SubjectId],
    sessions: set[SessionId],
):
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())

    with pytest.raises(
        ValueError,
        match="querying for both cross-product subjects-sessions pairs and cartesian-product of subjects and sessions does not make sense",
    ):
        # https://docs.python.org/3/reference/expressions.html#yield-expressions
        # The function does not start executing at all if it is a generator function
        # (i.e. there's a "yield" in the function body) until the first iteration/next() begins,
        # which is not intuitive -- hence the list(...) part
        list(
            dataset.query_images(
                ImageQuery(subjects=subjects, sessions=sessions, sub_ses=sub_ses)
            )
        )


def test_query_sub_ses_pair_no_sessions():
    dataset = BIDSDataset(Path("/does/not/exist"), _get_dataset_description())
    dataset.add_subject("sub-1")

    with pytest.raises(
        ValueError,
        match=escape(
            "Found a subject without an associated session in its pair, in {'sub-1': set()}"
        ),
    ):
        dataset.query_images(ImageQuery(sub_ses={"sub-1": set()}))
