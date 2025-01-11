from datetime import date
import json
from pathlib import Path
from typing import Any, Callable, TypeAlias

import pandas as pd

import pyarrow as pa
from pyarrow.json import read_json


def create_json_data(csv: str = "dowjones.csv", get_seaborn_dst: bool = False):
    if get_seaborn_dst:
        url = f"https://raw.githubusercontent.com/mwaskom/seaborn-data/master/{csv}"
    else:
        url = csv
    df = pd.read_csv(url)
    df.to_json(csv.replace("csv", "json"), orient="records")


def eg_tbl(embed: str) -> pa.Table:
    assert embed, "embed a larger json file"

    cols = [pa.int32(), pa.string(), pa.binary(), pa.bool_()]

    schema = pa.schema([(f"f{i}", t) for i, t in enumerate(cols)])

    db_cols = {
        "f0": list(range(4)),
        "f1": ["OwBPJ", "AseeP", "SMlIm", "AsDf"],
        "f2": [
            b'{"name":"OwBPJ", "flag": true}',
            b'{"name":"AseeP", "flag": true}',
            b'{"name": "SMlIm", "flag": false}',
            Path(embed).read_bytes(),
        ],
        "f3": [True, True, False, False],
    }

    return pa.Table.from_pydict(db_cols, schema=schema)


def blob(embed: str = "dowjones.json") -> tuple[pa.ChunkedArray, pa.Table]:
    db_tbl = eg_tbl(embed)
    for fld in db_tbl.schema:
        if fld.type == pa.binary():  # return first binary column
            return db_tbl.column(fld.name), db_tbl
    raise ValueError(f"no binary column in table: {db_tbl.column_names}")


json_predicate_t: TypeAlias = dict[str, Callable[[Any], Any]]


def transform(data: dict[str, Any], pred: json_predicate_t) -> dict[str, Any]:
    if not pred:
        return data

    try:
        return {**data, **{k: pred[k](data[k]) for k in pred}}
    except KeyError as err:
        key = err.args[0]
        if key not in pred:
            print(f"missing key from json predicate: {pred}")
        if key not in data:
            print(f"missing key from data: {data}")
        raise


def extract_transform_load(
    buf: pa.BinaryScalar, pred: json_predicate_t = {}, schema: pa.Schema = None
) -> pa.Table:
    """NOTE: If blobs are larger than 2GB, we could use `pa.LargeBinaryScalar`"""
    match data := json.loads(buf.as_py()):
        case list():
            return pa.Table.from_pylist(
                [transform(i, pred) for i in data], schema=schema
            )
        case _:
            raise ValueError(f"not implemented for {type(data)}")


def extract_transform_load_chunked(
    buffers: pa.ChunkedArray, pred: json_predicate_t = {}, schema: pa.Schema = None
) -> pa.Table:
    # FIXME: insert identifier row
    return pa.Table.from_pylist(
        [transform(json.loads(buf.as_py()), pred) for buf in buffers], schema=schema
    )


if __name__ == "__main__":
    binary_col, db_tbl = blob()

    ## benchmarks on my laptop: 11th Gen Intel Core i7-1185G7
    batched, value = binary_col[:3], binary_col[-1]

    # pa.Table: ~34-37 us
    value_tbl = extract_transform_load_chunked(batched)

    # pa.Table: ~681-709 us
    ts_schema = pa.schema([("Date", pa.date32()), ("Price", pa.float32())])
    ts_tbl = extract_transform_load(
        value, schema=ts_schema, pred={"Date": date.fromisoformat}
    )

    df = ts_tbl.to_pandas().set_index("Date")

    # >225 us
    json_as_arrow = [read_json(pa.BufferReader(buf.as_buffer())) for buf in batched]
