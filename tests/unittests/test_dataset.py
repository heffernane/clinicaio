from clinicaio.dataset import *
#from dataset import *
import pytest
from re import escape
from io import StringIO

new_desc = lambda json_str: BIDSDatasetDescription._load_from_data(StringIO(json_str))
def test_desc_invalid_json():
    with pytest.raises(BIDSException, match="could not read or parse BIDS JSON description file: "):
        new_desc("!!!!")

def test_desc_invalid_json_object():
    with pytest.raises(BIDSException, match=escape("BIDS JSON description is invalid (not a JSON object)")):
        new_desc("3")
    with pytest.raises(BIDSException, match=escape("BIDS JSON description is invalid (not a JSON object)")):
        new_desc("[]")

def test_desc_missing_fields():
    with pytest.raises(BIDSException, match="missing mandatory field in BIDS JSON description file: 'Name'"):
        new_desc('{"BIDSVersion": "1.10.0","DatasetType": "raw"}')
    with pytest.raises(BIDSException, match="missing mandatory field in BIDS JSON description file: 'BIDSVersion'"):
        new_desc('{"Name": "TEST","DatasetType": "raw"}')