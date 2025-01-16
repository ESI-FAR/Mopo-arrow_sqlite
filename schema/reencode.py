#!/usr/bin/env python
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pandas[performance]>=2",
#   "pyarrow>=17",
#   "pydantic>=2",
# ]
# ///

"""Reencode old map type JSON to new table/tables type JSON

"""

from datetime import datetime, timedelta
import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
from pydantic import RootModel

from rich.pretty import pprint

from dbmap import make_records
from models import Array, ArrayIndex, DEArray, DEIndex, REArray, REIndex, RLIndex, Table


def to_df(json_doc: dict):
    data = make_records(json_doc, {}, [], idx_name="metric")
    tbl = pa.Table.from_pylist(data)
    df = tbl.to_pandas(types_mapper=pd.ArrowDtype)
    return df


class _sentinel:
    pass


def rl_encode(arr: ArrayIndex) -> RLIndex:
    last = _sentinel()
    values = []
    run_len = []
    for val in arr.values:
        if val != last:
            values.append(val)
            run_len.append(1)
        else:
            run_len[-1] += 1
    return RLIndex(name=arr.name, values=values, run_len=run_len)


def re_encode(arr: ArrayIndex) -> REIndex:
    last = arr.values[0]  # _sentinel()
    values = [last]
    run_end = []
    for idx, val in enumerate(arr.values[1:], start=1):
        if val != last:
            last = val
            values.append(val)
            run_end.append(idx)
    run_end.append(len(arr.values))
    return REIndex(name=arr.name, values=values, run_end=run_end)


def de_encode(arr: ArrayIndex) -> DEIndex:
    # not using list(set(...)) to preserve order
    values = list(dict.fromkeys(arr.values))
    indices = list(map(values.index, arr.values))
    return DEIndex(name=arr.name, values=values, indices=indices)


def series_to_col(col: pd.Series) -> ArrayIndex | DEIndex | Array | DEArray:
    match col.name, col.dtype.type:
        case "value", t if issubclass(t, bool | str) or t == object:
            print(f"idx_type: {t}, value: {col.iloc[:3]}")
            col = col.astype("category")
            arr = DEArray(
                name=col.name,
                values=col.cat.categories,
                indices=col.cat.codes,
            )
        case "value", t if issubclass(t, int | float):
            arr = Array(name=col.name, values=col.values)
        case _, t if issubclass(t, str) or t == object:
            print(f"type: {t}, value: {col.iloc[:3]}")
            col = col.astype("category")
            arr = DEIndex(
                name=col.name,
                values=col.cat.categories,
                indices=col.cat.codes,
            )
        case _, t if issubclass(t, int | str | datetime | timedelta) or t == object:
            arr = ArrayIndex(name=col.name, values=col.values)
        case _, _:
            print(f"unknown type {t}")
            arr = ArrayIndex(name=col.name, values=col.values)
    return arr


def to_tables(df: pd.DataFrame) -> Table:
    if df.empty:
        return []
    return [series_to_col(df[colname]) for colname in df.columns]


if __name__ == "__main__":
    from argparse import ArgumentParser

    parser = ArgumentParser(__doc__)
    parser.add_argument("old_json")
    parser.add_argument("new_json")
    opts = parser.parse_args()

    df = to_df(json.loads(Path(opts.old_json).read_text()))
    tbls = to_tables(df)
    # NOTE: using pydantic is optional here, we can also write our own
    # JSON serialisation if we want, probably all we need is `asdict(...)`.
    Path(opts.new_json).write_text(RootModel[Table](tbls).model_dump_json())
