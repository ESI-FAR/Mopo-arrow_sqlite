#!/usr/bin/env python

"""Reencode old map type JSON to new table/tables type JSON

"""

from collections import defaultdict
from pathlib import Path
from io import BytesIO
import json

import pandas as pd
import pyarrow as pa
from pydantic import RootModel

from dbmap import make_records
from models import ArrayIndex, DEIndex, REIndex, RLIndex, Table, Tables


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
    # FIXME: not validating!
    # not using list(set(...)) to preserve order
    dictionary = list(dict.fromkeys(arr.values))
    indices = list(map(dictionary.index, arr.values))
    return DEIndex(name=arr.name, values=dictionary, indices=indices)


def to_tables(df: pd.DataFrame) -> Tables:
    grouped = df.groupby("metric")
    tbls = []
    for grp in grouped.groups:
        _df = df.loc[grouped.groups[grp]]
        _tbl = defaultdict(list)
        for col in _df.columns:
            arr = {"name": col, "values": _df[col]}
            if col == "value":
                _tbl["columns"].append(arr)
            else:
                if col == "metric":
                    arr = de_encode(ArrayIndex(**arr))
                _tbl["indices"].append(arr)
        tbls.append(_tbl)
    return Tables(batches=tbls)


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
    Path(opts.new_json).write_text(RootModel[Tables](tbls).model_dump_json())
