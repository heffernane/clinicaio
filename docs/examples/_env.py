import os
from pathlib import Path

test_bids_read_path = Path(os.path.dirname(__file__)) / "../../tests/data-notebooks"
test_bids_write_path = None
# test_bids_write_path=Path("/tmp/bids_test")
if test_bids_write_path is None:
    raise Exception(
        "you must fill-in this write path in _env.py so you can inspect the written BIDS dataset on-disk"
    )
