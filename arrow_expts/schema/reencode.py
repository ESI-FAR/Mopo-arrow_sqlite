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
from typing import cast, overload

import pandas as pd
import pyarrow as pa
from pydantic import RootModel

from rich.pretty import pprint

from ..spine.dbmap import make_records
from .models import (
    Array,
    ArrayIndex,
    DictEncodedArray,
    DictEncodedIndex,
    RunEndArray,
    RunEndIndex,
    RunLengthArray,
    RunLengthIndex,
    Table,
)


def to_df(json_doc: dict):
    data = make_records(json_doc, {}, [], idx_name="metric")
    # NOTE: don't use pyarrow, difficult to support mixed types
    # tbl = pa.Table.from_pylist(data)
    # df = tbl.to_pandas(types_mapper=pd.ArrowDtype)
    df = pd.DataFrame.from_records(data)
    return df


class _sentinel:
    pass


SENTINEL = _sentinel()


@overload
def rl_encode(arr: Array) -> RunLengthArray: ...


@overload
def rl_encode(arr: ArrayIndex) -> RunLengthIndex: ...


def rl_encode(arr: ArrayIndex | Array) -> RunLengthIndex | RunLengthArray:
    last = SENTINEL
    values, run_len = [], []
    for val in arr.values:
        if val != last:
            values.append(val)
            run_len.append(1)
            last = val
        else:
            run_len[-1] += 1
    return RunLengthIndex(name=arr.name, values=values, run_len=run_len)


@overload
def re_encode(arr: Array) -> RunEndArray: ...


@overload
def re_encode(arr: ArrayIndex) -> RunEndIndex: ...


def re_encode(arr: ArrayIndex | Array) -> RunEndIndex | RunEndArray:
    last = SENTINEL
    values, run_end = [], []
    for idx, val in enumerate(arr.values, start=1):
        if last != val:
            values.append(val)
            run_end.append(idx)
        else:
            run_end[-1] = idx
        last = val
    return RunEndIndex(name=arr.name, values=values, run_end=run_end)


@overload
def de_encode(arr: Array) -> DictEncodedArray: ...


@overload
def de_encode(arr: ArrayIndex) -> DictEncodedIndex: ...


def de_encode(arr: ArrayIndex | Array) -> DictEncodedIndex | DictEncodedArray:
    # not using list(set(...)) to preserve order
    values = list(dict.fromkeys(arr.values))
    indices = list(map(values.index, arr.values))
    return DictEncodedIndex(name=arr.name, values=values, indices=indices)


def series_to_col(
    col: pd.Series,
) -> ArrayIndex | DictEncodedIndex | Array | DictEncodedArray:
    match col.name, col.dtype.type:
        case "value", t if issubclass(t, str) or t is object:
            print(f"type: {t}, value: {col.iloc[:3]}")
            col = col.astype("category")
            return DictEncodedArray(
                name=col.name,
                values=col.cat.categories,
                indices=col.cat.codes,
            )
        case "value", t if issubclass(t, int):
            return Array(name=col.name, values=col.values)
        case _, t if issubclass(t, (bool, float, bytes)):
            return Array(name=col.name, values=col.values)
        case _, t if issubclass(t, str) or t is object:
            print(f"idx_type: {t}, value: {col.iloc[:3]}")
            col = col.astype("category")
            return DictEncodedIndex(
                name=col.name,
                values=col.cat.categories,
                indices=col.cat.codes,
            )
        case _, t if issubclass(t, (int, datetime, timedelta)) or t is object:
            return ArrayIndex(name=col.name, values=col.values)
        case n, t:
            raise NotImplementedError(f"{n}: unknown type {t}")


def to_tables(df: pd.DataFrame) -> Table:
    if df.empty:
        return []
    return [series_to_col(col) for _, col in df.items()]


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
    json_blob = RootModel[Table](tbls).model_dump_json(indent=2)
    Path(opts.new_json).write_text(json_blob)
