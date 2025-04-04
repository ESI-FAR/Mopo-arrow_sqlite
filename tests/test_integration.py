import json

import pytest

from arrow_expts.schema.models import Array
from arrow_expts.schema.reencode import series_to_col, to_df, to_tables

from .conftest import JSONDIR


@pytest.mark.parametrize("fname,arr", [("array.numbers.json", [2.3, 23.0, 5.0])])
def test_json_to_tbl(fname, arr):
    input_json = JSONDIR / fname
    data = json.loads(input_json.read_text())

    exp = Array(name="i", values=arr)
    df = to_df(data)

    assert series_to_col(df[exp.name]) == exp
    assert to_tables(df) == [exp]
