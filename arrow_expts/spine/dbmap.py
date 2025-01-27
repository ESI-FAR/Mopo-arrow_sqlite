from argparse import ArgumentParser
from datetime import datetime
from enum import Enum, auto
import json
import re
from typing import cast
import weakref

import pandas as pd

from spinedb_api import DatabaseMapping
from spinedb_api.temp_id import TempId


def json_loads_ts(json_str: str | bytes):
    return pd.Series(json.loads(json_str)["data"])


SEQ_PAT = re.compile(r"(t|p)([0-9]+)")

def filter_frequencies(freq: str) -> str:
    # not very robust yet
    filtered_freq  = freq \
        .replace("years", "Y") \
        .replace("year", "Y") \
        .replace("months", "M") \
        .replace("month", "M") \
        .replace("quarters", "Q") \
        .replace("quarter", "Q") \
        .replace("weeks", "W") \
        .replace("week", "W") \
        .replace("hours", "h") \
        .replace("hour", "h") \
        .replace("minutes", "min") \
        .replace("minute", "min") \
        .replace("seconds", "s") \
        .replace("second", "s") \
        .replace("microseconds", "us") \
        .replace("microsecond", "us") \
        .replace("nanoseconds", "ns") \
        .replace("nanosecond", "ns")
    if re.compile("^[0-9]+$").match(filtered_freq):
        # If frequency is an integer, the implied unit is "minutes"
        return freq + "m"
    else:
        return freq

class IndexType(Enum):
    Timestamp = auto()
    Sequence = auto()
    Generic = auto()


def make_records(
    json_doc: dict | int | float | str,
    idx_lvls: dict,
    res: list[dict],
    *,
    idx_name: str = "default",
) -> list[dict]:
    """Parse time-series w/ a multi-index stored as a nested map

    Ask Suvayu for the example DB

    """

    match json_doc:
        # maps
        case {"data": list() as data, "type": "map", **_r}:
            index_name = json_doc.get("index_name", "time")  # use "time" if "index_name" does not exist
            index_type = json_doc.get("index_type")
            for key, val in data:
                if index_type == "date_time":
                    key = datetime.fromisoformat(key)
                if index_type == "duration":
                    key = pd.Timedelta(key)
                make_records(val, {**idx_lvls, index_name: key}, res)
        case {"data": dict() as data, "type": "map", **_r}:
            index_name = json_doc.get("index_name", "time")  # use "time" if "index_name" does not exist
            index_type = json_doc.get("index_type")
            for key, val in data.items():
                if index_type == "date_time":
                    key = datetime.fromisoformat(key)
                if index_type == "duration":
                    key = pd.Timedelta(key)
                make_records(val, {**idx_lvls, index_name: key}, res)
        # time series
        case {"data": dict() as data, "type": "time_series", **_r}:
            index_name = json_doc.get("index_name", "time")  # use "time" if "index_name" does not exist
            for key, val in data.items():
                key = datetime.fromisoformat(key)
                make_records(val, {**idx_lvls, index_name: key}, res)
        case {
            "data": [[str(), float() | int()], *_] as data,
            "type": "time_series",
            **_r,
        }:
            index_name = json_doc.get("index_name", "time")  # use "time" if "index_name" does not exist
            for key, val in data:
                key = datetime.fromisoformat(key)
                make_records(val, {**idx_lvls, index_name: key}, res)
        case {"data": [float() | int(), *_] as data, "type": "time_series", **_r}:
            index_name = json_doc.get("index_name", "time")  # use "time" if "index_name" does not exist
            ignore_year = json_doc.get(index, {}).get("ignore_year", None)
            repeat = json_doc.get(index, {}).get("repeat", None)
            if ignore_year == False:
                raise ValueError('Can\'t handle `ignore_year == False`. Please re-format your dataset.')
            if repeat == False:
                raise ValueError('Can\'t handle `repeat == False`. Please re-format your dataset.')
            match json_doc:
                case {
                    "index": {
                        "start": start,
                        "resolution": freq,
                        "ignore_year": bool(),
                        "repeat": bool(),
                    },
                    **_r,
                }:
                    freq = filter_frequencies(freq)
                    index = pd.date_range(start=start, freq=freq, periods=len(data))
                case _:
                    if json_doc.get(index, {}) != {}:
                        raise NotImplementedError('Can\'t handle a partially set `index` value. Please re-format your dataset.')
                    index = pd.date_range(
                        start="0001-01-01", periods=len(data), freq="1h"
                    )
            for time, val in zip(index, data):
                make_records(val, {**idx_lvls, index_name: time, "value": val}, res)
        case {
            "data": [[str(), dict() | float() | int()], *_] as data,
            "type": "time_series",
            **_r,
        }:
            if m := SEQ_PAT.match(data[0][0]):
                idx_type = IndexType.Sequence
                index_name = json_doc.get(
                    "index_name", "period" if "p" == m.group(1) else "seq"
                )
            else:
                idx_type = IndexType.Generic
                index_name = json_doc.get("index_name", idx_name)  # use idx_name if "index_name" does not exist
            for key, val in data:
                if idx_type == IndexType.Sequence:
                    m = SEQ_PAT.match(key)
                    assert m is not None
                    key = int(m.group(2))
                make_records(val, {**idx_lvls, index_name: key}, res)

        # arrays
        case {"type": "array", "data": [str() | float() | int(), *_] as data, **_r}:
            value_type = json_doc.get("value_type", "float")  # use "float" if "value_type" does not exist
            index_name = json_doc.get("index_name", "i")  # use "i" if "index_name" does not exist

            if value_type == "duration":
                try:
                    data = [pd.Timedelta(filter_frequencies(value)) for value in data]
                except ValueError as err:
                    if "invalid unit abbreviation" in repr(err):
                        raise ValueError('"year" and "month" are ambiguous time units. Please convert them to days.')
                    else:
                        raise err
            elif value_type == "date_time":
                data = [datetime.fromisoformat(key) for key in data]
            elif value_type == "float":
                data = [pd.to_numeric(value) for value in data]
            elif value_type == "str":
                pass
            else:
                raise NotImplementedError(f"Can't match {value_type} arrays.")
            for value in data:
                res.append({index_name: value})

        # date-time
        case {"type": "date_time", "data": str() as data, **_r}:
            idx_lvls["value"] = datetime.fromisoformat(data)
            res.append(idx_lvls)

        # duration
        case {"type": "duration", "data": int() | str() as data, **_r}:
            if type(data) == int:
                data = str(data) + "m"  # integer time unit is "minutes"
            try:
                data = pd.Timedelta(filter_frequencies(data))
            except ValueError as err:
                if "invalid unit abbreviation" in repr(err):
                    raise ValueError('"year" and "month" are ambiguous time units. Please convert them to days.')
                else:
                    raise err
            res.append({"value": data})

        # time_pattern
        case {"type": "time_pattern", **_r}:
            raise NotImplementedError("Can't convert `time_pattern`. Please convert it to a `time_series`".)

        # values
        case int() | float() | str() | bool():
            idx_lvls["value"] = json_doc
            res.append(idx_lvls)
        case _:
            raise NotImplementedError("Can't match this JSON structure yet.")
    return res


def json_loads_multi_dim_ts(json_str: str | bytes):
    recs = make_records(json.loads(json_str), {}, [])
    ts = pd.DataFrame((r.values() for r in recs), columns=recs[0].keys())
    # ts["time"] = ts["time"].str.strip("t").astype(int)
    # ts["period"] = ts["period"].str.strip("p").astype(int)

    # assuming last column as value column
    *idx_cols, value_col = ts.columns.to_list()
    ts = ts.astype(
        {col: "category" for col, _ in ts.dtypes.items() if col != value_col}
    ).set_index(idx_cols)[value_col]
    return ts


class MyDBMap:
    def __init__(self, url: str):
        self.db = DatabaseMapping(f"sqlite:///{url}")
        self._finalizer = weakref.finalize(self, self.db.close)
        self.data = {}

    @classmethod
    def prep_df(cls, df: pd.DataFrame, prefix: str, cols: list[str]):
        _df = df.loc[:, cols].rename({col: f"{prefix}_{col}" for col in cols}, axis=1)
        return cast(pd.DataFrame, _df)

    def get(self, item_type: str):
        return (
            {
                k: v.db_id if isinstance(v, TempId) else v
                for k, v in row._asdict().items()
            }
            for row in self.db.get_items(item_type=item_type)
        )

    @property
    def param_values(self) -> pd.DataFrame:
        if self.data.get("param_values") is None:
            cat_cols = ["type", "entity_class_name"]
            drop_cols = [
                *[
                    f"{pre}_{post}"
                    for pre in ["object", "relationship"]
                    for post in ["id", "class_id"]
                ],
                "list_value_id",
                "commit_id",
            ]

            df = (
                pd.DataFrame(self.get(item_type="parameter_value"))
                .drop(columns=drop_cols, errors="ignore")
                .rename({"parameter_definition_id": "parameter_id"}, axis=1)
                .merge(self.param_definitions, on=["parameter_id"], how="left")
                .merge(self.entities, on=["entity_id", "entity_class_id"], how="left")
                .astype({col: "category" for col in cat_cols})
            )
            self.data["param_values"] = df
        return self.data["param_values"]

    @property
    def param_definitions(self) -> pd.DataFrame:
        if self.data.get("param_definitions") is None:
            cols = ["id", "name"]
            df = pd.DataFrame(self.get(item_type="parameter_definition"))
            self.data["param_definitions"] = self.prep_df(df, "parameter", cols)
        return self.data["param_definitions"]

    @property
    def entities(self) -> pd.DataFrame:
        if self.data.get("entities") is None:
            entity = pd.DataFrame(self.get(item_type="entity"))
            entity = self.prep_df(entity, "entity", ["id", "class_id", "name"])
            eclass = pd.DataFrame(self.get(item_type="entity_class"))
            eclass = self.prep_df(eclass, "entity_class", ["id", "name"])
            self.data["entities"] = entity.merge(
                eclass, on="entity_class_id", how="left"
            )
        return self.data["entities"]

    @property
    def alternatives(self) -> pd.DataFrame:
        if self.data.get("alternatives") is None:
            df = pd.DataFrame((self.get(item_type="alternative")))
            self.data["alternatives"] = self.prep_df(df, "alternatives", ["id", "name"])
        return self.data["alternatives"]

    def get_ts(self, param: str, drop: list[str] = [], **sel: str) -> pd.DataFrame:
        df = self.param_values.query(f"parameter_name == {param!r}")

        if len(value_types := df.type.unique()) == 1:
            value_type = value_types[0]
        else:
            raise ValueError(f"{value_types=}, not unique")

        if value_type == "time_series":
            func = json_loads_ts
        elif value_type == "map":
            func = json_loads_multi_dim_ts
        else:
            raise ValueError

        ts = (
            df["value"]
            .apply(func)
            .assign(
                alternative=df["alternative_id"],
                entity_class=df["entity_class_name"],
                entity=df["entity_name"],
            )
        )

        if sel:
            selection = " & ".join(f"({col} == {val!r})" for col, val in sel.items())
            ts = ts.query(selection)
        return ts.drop(columns=[*sel, *drop])


if __name__ == "__main__":
    parser = ArgumentParser("Read Spine DB")
    parser.add_argument("db_url", help="DB url")
    opts = parser.parse_args()

    handle = MyDBMap(opts.db_url)
    # ts = handle.get_ts("unit_flow")  # 4
    # ts = handle.get_ts("cost_t")  # 268
