from dataclasses import astuple
import json

import numpy as np
import pandas as pd
import pytest

from arrow_expts.schema.models import Array
from arrow_expts.schema.reencode import series_to_col, to_df, to_tables

from .conftest import JSONDIR


def np_eq(i, j):
    if isinstance(cmp := (i == j), (np.ndarray, pd.Series, pd.DataFrame)):
        return cmp.all()
    else:
        return cmp


@pytest.mark.parametrize("part", ["numbers"])
def test_series_to_col(part):
    input_json = JSONDIR / f"array.{part}.json"
    data = json.loads(input_json.read_text())

    exp = Array(name=data.get("index_name", "i"), values=data["data"])
    df = to_df(data)

    res = series_to_col(df[exp.name])
    for i, j in zip(astuple(res), astuple(exp)):
        assert np_eq(i, j)

    tbl = to_tables(df)
    assert len(tbl) == 1
    assert isinstance(tbl[0], Array)


@pytest.mark.parametrize("part", ["numbers"])
def test_to_tables(part):
    input_json = JSONDIR / f"array.{part}.json"
    data = json.loads(input_json.read_text())

    exp = Array(name=data.get("index_name", "i"), values=data["data"])
    df = to_df(data)

    res = series_to_col(df[exp.name])
    for i, j in zip(astuple(res), astuple(exp)):
        assert np_eq(i, j)

    tbl = to_tables(df)
    assert len(tbl) == 1
    assert isinstance(tbl[0], Array)
