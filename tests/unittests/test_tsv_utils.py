from pathlib import Path
from re import escape

import pytest
from pandas import DataFrame
from pandas.testing import assert_frame_equal
from pyfakefs.fake_filesystem import FakeFilesystem

from clinicaio._tsv_utils import _read_tsv_as_df, _write_rows_to_tsv
from clinicaio.types import BIDSException


# Rename the pyfakefs fixture so it's clearer what it actually is
@pytest.fixture
def fakefs(fs):
    yield fs


def test_fakefs(fakefs: FakeFilesystem):
    assert type(fakefs) == FakeFilesystem


def test_read_tsv_no_tab_separator(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/foo.tsv")

    fakefs.create_file(file_path=tsv_path, contents="a,b\n1,2")

    df = _read_tsv_as_df(tsv_path)
    cols = list(df.columns)
    assert len(cols) == 1
    assert cols[0] == "a,b"

    assert_frame_equal(df, DataFrame({"a,b": ["1,2"]}))


def test_read_tsv_tab_separator(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/foo.tsv")

    fakefs.create_file(file_path=tsv_path, contents="a\tb\nkkk\tppp")

    df = _read_tsv_as_df(tsv_path)
    cols = list(df.columns)
    assert len(cols) == 2
    assert cols == ["a", "b"]

    assert_frame_equal(df, DataFrame({"a": ["kkk"], "b": ["ppp"]}))


# We want to make sure that the DataFrame allows mixed-type cells so that
# None is allowed (as a general "n/a" value regardless of the column data type)
# and such that column data type autodetection is not so much of an issue: the
# cells should not be interpreted at this point as being of a specific type
# (e.g. 111 being an int).
def test_read_tsv_object_format(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/foo.tsv")

    fakefs.create_file(file_path=tsv_path, contents="a\tb\n111\tppp\nkkk\t222")

    df = _read_tsv_as_df(tsv_path)
    cols = list(df.columns)
    assert len(cols) == 2
    assert cols == ["a", "b"]
    assert list(df.dtypes) == [object, object]

    assert_frame_equal(df, DataFrame({"a": ["111", "kkk"], "b": ["ppp", "222"]}))


def test_read_tsv_na_none(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/foo.tsv")

    fakefs.create_file(
        file_path=tsv_path, contents="a\tb\n111\tppp\nn/a\t333\nkkk\t222"
    )

    df = _read_tsv_as_df(tsv_path)
    cols = list(df.columns)
    assert len(cols) == 2
    assert cols == ["a", "b"]
    assert list(df.dtypes) == [object, object]

    assert_frame_equal(
        df, DataFrame({"a": ["111", None, "kkk"], "b": ["ppp", "333", "222"]})
    )


def test_read_tsv_non_existent_file(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/doesnotexist.tsv")

    with pytest.raises(
        BIDSException, match=escape(f"Could not read TSV file {tsv_path}:")
    ):
        df = _read_tsv_as_df(tsv_path)


def test_write_tsv_no_rows_no_file(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/foobar.tsv")

    _write_rows_to_tsv(tsv_path=tsv_path, first_column_name="aaa", rows=[])

    assert not fakefs.exists(tsv_path)


def test_write_tsv_file_already_exists(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/foobar.tsv")

    fakefs.create_file(file_path=tsv_path)

    with pytest.raises(
        FileExistsError,
        match=escape("File exists: '/tmp/foobar.tsv'"),
    ):
        _write_rows_to_tsv(
            tsv_path=tsv_path, first_column_name="aaa", rows=[{"aaa": "bbb"}]
        )


def test_write_tsv_none_to_na(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/foobar.tsv")

    _write_rows_to_tsv(
        tsv_path=tsv_path,
        first_column_name="aaa",
        rows=[
            {"aaa": "bbb", "colb": None},
            {"aaa": "ccc", "colb": "cella"},
        ],
    )

    assert fakefs.get_object(tsv_path).contents == "aaa\tcolb\nbbb\tn/a\nccc\tcella\n"


def test_write_tsv_first_column_reordering(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/foobar.tsv")

    _write_rows_to_tsv(
        tsv_path=tsv_path,
        first_column_name="aaa",
        rows=[
            {"colb": None, "aaa": "bbb", "ddd": None},
            {"colb": "cellb", "ddd": "val", "aaa": "ddd"},
            {"colb": "cella", "aaa": "ccc", "ddd": None},
        ],
    )

    expected_tsv = "aaa\tcolb\tddd\nbbb\tn/a\tn/a\nddd\tcellb\tval\nccc\tcella\tn/a\n"
    assert fakefs.get_object(tsv_path).contents == expected_tsv


def test_write_tsv_partial_columns_each_row(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/foobar.tsv")

    _write_rows_to_tsv(
        tsv_path=tsv_path,
        first_column_name="aaa",
        rows=[
            {"aaa": "1", "bbb": "b1"},
            {"aaa": "2", "ccc": "c2"},
            {"aaa": "3", "ddd": "d3", "bbb": "b3"},
        ],
    )

    expected_tsv = (
        "aaa\tbbb\tccc\tddd\n1\tb1\tn/a\tn/a\n2\tn/a\tc2\tn/a\n3\tb3\tn/a\td3\n"
    )
    assert fakefs.get_object(tsv_path).contents == expected_tsv


def test_write_tsv_missing_first_column_for_row(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/foobar.tsv")

    with pytest.raises(
        ValueError,
        match="one of the provided rows did not have the required column aaa",
    ):
        _write_rows_to_tsv(
            tsv_path=tsv_path,
            first_column_name="aaa",
            rows=[
                {"aaa": "1", "bbb": "b1"},
                # Missing first column here
                {"ccc": "c2"},
                {"aaa": "3", "ddd": "d3", "bbb": "b3"},
            ],
        )

    assert not fakefs.exists(tsv_path)


def test_write_tsv_missing_first_column_for_all_rows(fakefs: FakeFilesystem):
    tsv_path = Path("/tmp/foobar.tsv")

    with pytest.raises(
        ValueError,
        match="one of the provided rows did not have the required column aaa",
    ):
        _write_rows_to_tsv(
            tsv_path=tsv_path,
            first_column_name="aaa",
            rows=[
                # All of the rows are missing the first column
                {"bbb": "b1"},
                {"ccc": "c2"},
                {"ddd": "d3", "bbb": "b3"},
            ],
        )

    assert not fakefs.exists(tsv_path)
