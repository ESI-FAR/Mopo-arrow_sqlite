from dataclasses import astuple
import json

import numpy as np
import pytest

from arrow_expts.schema.models import Array
from arrow_expts.schema.reencode import series_to_col, to_df, to_tables

from .conftest import JSONDIR


def np_eq(i, j):
    if isinstance(cmp := (i == j), np.ndarray):
        return cmp.all()
    else:
        return cmp


@pytest.mark.parametrize("fname,arr", [("array.numbers.json", [2.3, 23.0, 5.0])])
def test_json_to_tbl(fname, arr):
    input_json = JSONDIR / fname
    data = json.loads(input_json.read_text())

    exp = Array(name="i", values=arr)
    df = to_df(data)

    res = series_to_col(df[exp.name])
    for i, j in zip(astuple(res), astuple(exp)):
        assert np_eq(i, j)

    tbl = to_tables(df)
    assert len(tbl) == 1
    assert isinstance(tbl[0], Array)
