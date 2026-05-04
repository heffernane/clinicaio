from typing import Iterable, Any, OrderedDict
from pathlib import Path
import math

from .types import BIDSException

import pandas as pd

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
		df = pd.read_csv(tsv_path, sep='\t', dtype=object)
		#df = df.replace("n/a", None, inplace=True)
		df.replace(math.nan, None, inplace=True)
		
		return df
	except Exception as e:
		raise BIDSException(f"Could not read TSV file {tsv_path}: {e}")
	
def _write_rows_to_tsv(tsv_path: Path, first_column_name: str, rows: Iterable[dict[str, Any]]):
	"""
	Writes the given row to the given TSV file, making sure to move the ``first_column_name`` as first column.

	Raises
	------
	BIDSException:
		if the ``first_column_name`` is not provided for one of the rows, or if the TSV file already exists.
	"""

	# The ID column in BIDS TSV files is usually required to be the first one. In practice it's
	# not always the case when we read them, but let's enforce it when writing them.
	def dict_with_first_column(values: dict[str, Any]) -> OrderedDict[str, Any]:
		ordered_dict = OrderedDict(values)
		try:
			ordered_dict.move_to_end(first_column_name, last=False)
		except KeyError:
			raise BIDSException(f"expected required column {first_column_name} when writing TSV file {tsv_path}, but only found columns {values.keys()}")

		return ordered_dict

	# NOTE: Pandas handles correctly the case where different rows do not all have the same available columns: 
	# >>> pd.DataFrame([
	# ... namedtuple("A", ["a", "b"])(a=1, b=2)._asdict(),
	# ... namedtuple("B", ["b", "c"])(b=3, c=4)._asdict(),
	# ... ])
	#    a    b  c
	# 0  1.0  2  NaN
	# 1  NaN  3  4.0
	df = pd.DataFrame(
		data=(dict_with_first_column(row) for row in rows),
	)

	if df.empty:
		return

	# https://bids-specification.readthedocs.io/en/stable/common-principles.html#tabular-files
	# "Missing and non-applicable values MUST be coded as n/a"
	# https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.isna.html
	try:
		df.to_csv(tsv_path, mode="x", sep="\t", na_rep="n/a", index=False)
	except FileExistsError:
		raise BIDSException(f"BIDS TSV file {tsv_path} can't be written as it already exists")