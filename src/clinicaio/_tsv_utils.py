import math
from pathlib import Path
from typing import Any, Iterable, OrderedDict

import pandas as pd

from .types import BIDSException

__all__ = [
    "_read_tsv_as_df",
    "_write_rows_to_tsv",
]


def _read_tsv_as_df(tsv_path: Path) -> pd.DataFrame:
    """
    Reads the given TSV file as a pandas DataFrame, with all columns
    being objects and NaN (n/a, etc.) being replaced with None.
    """

    try:
        df = pd.read_csv(tsv_path, sep="\t", dtype=object)
        df.replace(math.nan, None, inplace=True)

        return df
    except Exception as e:
        raise BIDSException(f"Could not read TSV file {tsv_path}: {e}")


def _write_rows_to_tsv(
    tsv_path: Path, first_column_name: str, rows: Iterable[dict[str, Any]]
) -> None:
    """
    Writes the given row to the given TSV file, making sure to move the ``first_column_name`` as first column.

    Raises
    ------
    BIDSException:
            if the ``first_column_name`` is not provided for one of the rows, or if the TSV file already exists.
    """

    # NOTE: Pandas handles correctly the case where different rows do not all have the same available columns:
    # >>> pd.DataFrame([
    # ... namedtuple("A", ["a", "b"])(a=1, b=2)._asdict(),
    # ... namedtuple("B", ["b", "c"])(b=3, c=4)._asdict(),
    # ... ])
    #    a    b  c
    # 0  1.0  2  NaN
    # 1  NaN  3  4.0
    df = pd.DataFrame(
        data=rows,
    )

    if df.empty:
        return

    first_column_by_name = df.get(first_column_name)
    if first_column_by_name is None or first_column_by_name.isna().any():
        raise BIDSException(
            f"one of the provided rows did not have the required column {first_column_name}"
        )

    cols = list(df.columns)
    try:
        first_col_idx = cols.index(first_column_name)
    except ValueError:
        # Unreachable due to previous check
        assert False, (
            "one of the rows is already supposed to have the first column name"
        )

    # The ID column in BIDS TSV files is usually required to be the first one. In practice it's
    # not always the case when we read them, but let's enforce it when writing them.
    if first_col_idx != 0:
        col_name = cols.pop(first_col_idx)
        assert col_name == first_column_name
        cols.insert(0, first_column_name)
        df = df.reindex(columns=cols)

    # https://bids-specification.readthedocs.io/en/stable/common-principles.html#tabular-files
    # "Missing and non-applicable values MUST be coded as n/a"
    # https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.isna.html
    try:
        df.to_csv(tsv_path, mode="x", sep="\t", na_rep="n/a", index=False)
    except FileExistsError:
        raise BIDSException(
            f"BIDS TSV file {tsv_path} can't be written as it already exists"
        )
