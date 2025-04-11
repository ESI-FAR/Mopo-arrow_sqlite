from datetime import datetime
import json
from typing import Callable

import numpy as np
import pandas as pd
import pytest

from arrow_expts.schema.models import TimePattern
from arrow_expts.spine.dbmap import (
    _atoi,
    _formatter,
    _low_res_datetime,
    _normalise_freq,
    _to_dateoffset,
    make_records,
)

from .conftest import JSONDIR


def test_filter_frequencies():
    assert _normalise_freq("5 years") == "5 Y"
    assert _normalise_freq("5 year") == "5 Y"
    assert _normalise_freq("3s") == "3s"
    assert _normalise_freq("60") == "60min"


def test_low_res_datetime():
    target = pd.date_range(start="2001-01-01", freq="7D", periods=5)
    low_res = _low_res_datetime(start="2001-01-01", freq="1W", periods=5)

    assert low_res.dtype == "datetime64[s]"
    assert target.freq == low_res.freq
    for date_target, date_low_res in zip(target, low_res):
        assert date_target == date_low_res

    res = _low_res_datetime(start="0001-01-01", freq="1s", periods=1)
    assert res[0] == pd.Timestamp("0001-01-01")


@pytest.mark.parametrize("part", ["durations", "numbers", "strings"])
def test_arrays(part: str):
    data = json.loads((JSONDIR / f"array.{part}.json").read_text())
    fmt = _formatter(data.get("value_type", "float"))
    index_name = data.get("index_name", "i")
    expect = [fmt(index_name, i) for i in data["data"]]
    assert expect == make_records(data, {}, [])


def fmt_durations(val: str | int):
    return _to_dateoffset(_normalise_freq(val))


@pytest.mark.parametrize(
    "type_,value,fmt",
    [
        ("date_time", "2019-06-01T22:15:00+01:00", datetime.fromisoformat),
        ("duration", "1h", fmt_durations),
        ("duration", 60, fmt_durations),
        ("duration", "1 hour", fmt_durations),
    ],
)
def test_values(type_: str, value, fmt: Callable):
    res = make_records({"type": type_, "data": value}, {}, [])
    assert res == [{"value": fmt(value)}]


def test_time_pattern():
    data = json.loads((JSONDIR / "time-pattern.json").read_text())
    index_name = data.get("index_name", "default0")
    expect = [{index_name: TimePattern(k), "value": v} for k, v in data["data"].items()]
    res = make_records(data, {}, [])
    assert res == expect


@pytest.mark.parametrize(
    "part, interval",
    [
        ("dict", "30 min"),
        ("one-column-array-custom-indices", "30 min"),
        ("one-column-array", "1 h"),
        ("two-column-array", "30 min"),
        ("two-column-array-named-indices", "30 min"),
    ],
)
def test_time_series(part: str, interval: str):
    data = json.loads((JSONDIR / f"time-series.{part}.json").read_text())
    res = make_records(data, {}, [])

    # index column name matches
    index_name = data.get("index_name", "default0")
    assert index_name in res[0]
    assert isinstance(res[0][index_name], datetime)
    assert res[1][index_name] - res[0][index_name] == pd.Timedelta(interval)
