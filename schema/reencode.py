#!/usr/bin/env python

"""Reencode old map type JSON to new table/tables type JSON

"""

from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Literal, TypeAlias

import pandas as pd
import pyarrow as pa
from pydantic import RootModel
from rich.pretty import pprint

from dbmap import make_records
from models import Array, ArrayIndex, DEArray, DEIndex, REIndex, RLIndex, Table


def _parse(row):
    a, b, c = list(row.values())
    return {"metric": a, "seq": int(b.lstrip("t")), "value": c}


def to_df(json_doc: dict):
    data = make_records(json_doc, {}, [])
    tbl = pa.Table.from_pylist([_parse(r) for r in data])
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


def to_tables(df: pd.DataFrame) -> Table:
    indices, columns = [], []
    for colname in df.columns:
        col = df[colname]
        match col.name, col.dtype.type:
            case "value", t if t in (str, bool):
                col = col.astype("category")
                arr = DEArray(
                    name=col.name,
                    values=col.cat.categories,
                    indices=col.cat.codes,
                )
                columns.append(arr)
            case "value", _:
                arr = Array(name=col.name, values=col.values)
                columns.append(arr)
            case _, t if t in (str, bool):
                col = col.astype("category")
                arr = DEIndex(
                    name=col.name,
                    values=col.cat.categories,
                    indices=col.cat.codes,
                )
                indices.append(arr)
            case _, _:
                arr = ArrayIndex(name=col.name, values=col.values)
                indices.append(arr)
    return Table(indices=indices, columns=columns)


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
