from argparse import ArgumentParser
from datetime import datetime
import json
import re
from typing import cast, Any, Callable, Iterable, TypeAlias
from warnings import warn
import weakref

import pandas as pd
import numpy as np

from spinedb_api import DatabaseMapping
from spinedb_api.temp_id import TempId


def json_loads_ts(json_str: str | bytes):
    return pd.Series(json.loads(json_str)["data"])


# Regex pattern to indentify numerical sequences encoded as string
SEQ_PAT = re.compile(r"(t|p)([0-9]+)")
# Regex pattern to identify a number encoded as a string
FREQ_PAT = re.compile("^[0-9]+$")


def normalise_freq(freq: int | str):
    """Normalise integer/string to frequency.

    The frequency value is as understood by `pandas.Timedelta`.  Note
    that ambiguous values such as month or year are still retained
    with the intention to handle later in the pipeline.

    """
    if isinstance(freq, int):
        return str(freq) + "m"
    if FREQ_PAT.match(freq):
        # If frequency is an integer, the implied unit is "minutes"
        return freq + "m"
    # not very robust yet
    return (
        freq.replace("years", "Y")
        .replace("year", "Y")
        .replace("months", "M")
        .replace("month", "M")
        .replace("weeks", "W")
        .replace("week", "W")
        .replace("days", "D")
        .replace("day", "D")
        .replace("hours", "h")
        .replace("hour", "h")
        .replace("minutes", "min")
        .replace("minute", "min")
        .replace("seconds", "s")
        .replace("second", "s")
    )


to_numpy = {
    "Y": "Y",
    "M": "M",
    "W": "W",
    "D": "D",
    "h": "h",
    "min": "m",
    "s": "s",
}


def low_res_datetime(start: str, freq: str, periods: int) -> pd.DatetimeIndex:
    """Create pd.DatetimeIndex with lower time resolution.

    The default resolution of pd.date_time is [ns], which puts
    boundaries on allowed start- and end-dates due to limited storage
    capacity. Choosing a resolution of [s] instead opens up that range
    considerably.

    "For nanosecond resolution, the time span that can be represented
    using a 64-bit integer is limited to approximately 584 years."  -
    https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timestamp-limitations

    You can check the available ranges with `pd.Timestamp.min` and
    `pd.Timestamp.max`.

    """
    if re_match := re.search(r"^([0-9]+) *(.*)$", freq):
        period_parts = re_match.groups()
    else:
        raise ValueError(f"invalid frequency: {freq!r}")

    if len(period_parts) != 2:
        raise ValueError(f"invalid frequency: {freq!r}")

    number_str, unit = period_parts
    start_date_np = np.datetime64(start, "s")
    # print(f"start_date_np: {start_date_np}")
    # print(to_numpy[unit])
    freq_np = np.timedelta64(int(number_str), to_numpy[unit])
    # print(f"freq_np: {freq_np}")
    freq_pd = pd.Timedelta(freq_np)
    # print(f"freq_pd: {freq_pd}")

    date_array = np.arange(start_date_np, start_date_np + periods * freq_np, freq_np)
    date_array_with_frequency = pd.DatetimeIndex(
        date_array, freq=freq_pd, dtype="datetime64[s]"
    )

    return date_array_with_frequency


def _atoi(name: str, val: str) -> dict[str, int | str]:
    """Convert string to number if it matches `t0001` or `p2001`.

    If a match is found, also override the name to "time" or "period"
    respectively.

    """
    if m := SEQ_PAT.match(val):
        name = "period" if "p" == m.group(1) else "time"
        return {name: int(m.group(2))}
    else:
        return {name: val}


_FmtIdx: TypeAlias = Callable[[str, str | Any], dict[str, Any]]


def _formatter(index_type: str) -> _FmtIdx:
    """Get a function that formats the values of a name value pair.

    The name is the column name.  The function returned depends on the
    `index_type`.  An unknown `index_type` returns a noop formatter,
    but it also issues a warning.  A noop formatter can be requested
    explicitly by passing the type "noop"; no warning is issued in
    this case.

    Index types:
    ============

    - "date_time" :: converts value to `datetime`

    - "duration" :: converts string to `pandas.Timedelta` compatible
      argument; note it still allows for ambiguous units like month or
      year.

    - "str" :: convert the value to integer if it matches `t0001` or
      `p2002`, and the name to "time" and "period" respectively;
      without a match it is a noop.

    - "float" | "time_pattern" | "noop" :: noop

    - fallback :: noop with a warning

    """
    match index_type:
        case "date_time" | "datetime":
            return lambda name, key: {name: datetime.fromisoformat(key)}
        case "duration":
            return lambda name, key: {name: normalise_freq(key)}
        case "str":
            # custom handling when data matches `SEQ_PAT`
            return _atoi
        case "float" | "time_pattern" | "timepattern" | "noop":
            return lambda name, key: {name: key}
        case _:  # fallback to noop w/ a warning
            warn(f"{index_type}: unknown type, fallback to noop formatter")
            return lambda name, key: {name: key}


def make_records(
    json_doc: dict | int | float | str,
    idx_lvls: dict,
    res: list[dict],
    *,
    lvlname_base: str = "default",
) -> list[dict]:
    """Parse parameter value into a list of records

    Spine db stores parameter_value as JSON.  After the JSON blob has
    been decoded to a Python dict, this function can transform it into
    a list of records (dict) like a table.  These records can then be
    consumed by Pandas to create a dataframe.

    The parsing logic works recursively by traversing depth first.
    Each call incrementally accumulates a cell/level of a record in
    the `idx_lvls` dictionary, once the traversal reaches a leaf node,
    the final record is appended to the list `res`.  The final result
    is also returned by the function, allowing for composition.

    If at any level, the index level name is missing, a default base
    name can be provided by setting a default `lvlname_base`.  The
    level name is derived by concatenating the base name with depth
    level.

    """
    lvlname = lvlname_base + f"{len(idx_lvls)}"

    # NOTE: The private functions below are closures, defined early in
    # the function such that they have the original arguments to
    # `make_records` available to them, but nothing more.  They either
    # help with some computation, raise a warning, or are helpers to
    # append to the result.
    def _from_pairs(data: Iterable[Iterable], fmt: _FmtIdx):
        assert isinstance(json_doc, dict)
        index_name = json_doc.get("index_name", lvlname)
        for key, val in data:
            _lvls = {**idx_lvls, **fmt(index_name, key)}
            make_records(val, _lvls, res, lvlname_base=lvlname_base)

    def _deprecated(var: str, val: Any):
        assert isinstance(json_doc, dict)
        index_name = json_doc.get("index_name")
        msg = f"{index_name}: {var}={val} is deprecated, handle in model, defaulting to time index from 0001-01-01."
        warn(msg, DeprecationWarning)

    def _time_index(idx: dict, length: int):
        start = idx.get("start", "0001-01-01T00:00:00")
        resolution = idx.get("resolution", "1h")
        freq = normalise_freq(resolution)
        return low_res_datetime(start=start, freq=freq, periods=length)

    def _append_arr(arr: Iterable, fmt: _FmtIdx):
        assert isinstance(json_doc, dict)
        index_name = json_doc.get("index_name", "i")
        for value in arr:
            res.append({**idx_lvls, **fmt(index_name, value)})

    match json_doc:
        # maps
        case {"data": dict() as data, "type": "map"}:
            # NOTE: is "index_type" mandatory?  In case it's not, we
            # check for it separately, and fallback in a way that
            # raises a warning but doesn't crash; same for the
            # 2-column array variant below.
            index_type = json_doc.get("index_type", "undefined-index_type-in-map")
            _from_pairs(data.items(), _formatter(index_type))
        case {"data": dict() as data, "index_type": index_type}:
            # NOTE: relies on other types not having "index_type";
            # same for the 2-column array variant below.
            _from_pairs(data.items(), _formatter(index_type))
        case {"data": [[_, _], *_] as data, "type": "map"}:
            index_type = json_doc.get("index_type", "undefined-index_type-in-map")
            _from_pairs(data, _formatter(index_type))
        case {"data": [[_, _], *_] as data, "index_type": index_type}:
            _from_pairs(data, _formatter(index_type))
        # time series
        case {"data": dict() as data, "type": "time_series"}:
            _from_pairs(data.items(), _formatter("date_time"))
        case {"data": [[str(), float() | int()], *_] as data, "type": "time_series"}:
            _from_pairs(data, _formatter("date_time"))
        case {
            "data": [float() | int(), *_] as data,
            "type": "time_series",
            "index": dict() as idx,
        }:
            match idx:
                case {"ignore_year": ignore_year}:
                    _deprecated("ignore_year", ignore_year)
                case {"repeat": repeat}:
                    _deprecated("repeat", repeat)

            index = _time_index(idx, len(data))
            _from_pairs(zip(index, data), _formatter("noop"))
        case {"type": "time_series", "data": [float() | int(), *_] as data}:
            _append_arr(data, _formatter("noop"))
        # arrays
        case {
            "type": "array",
            "value_type": value_type,
            "data": [str() | float() | int(), *_] as data,
        }:
            _append_arr(data, _formatter(value_type))
        case {"type": "array", "data": [float() | int(), *_] as data}:
            _append_arr(data, _formatter("float"))
        # date_time | duration | time_pattern
        case {
            "type": "date_time" | "duration" | "time_pattern" as data_t,
            "data": str() | int() as data,
        }:
            _fmt = _formatter(data_t)
            res.append({**idx_lvls, **_fmt("value", data)})
        # values
        case int() | float() | str() | bool() as data:
            _fmt = _formatter("noop")
            res.append({**idx_lvls, **_fmt("value", data)})
        case _:
            raise ValueError(f"match not found: {json_doc}")
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
