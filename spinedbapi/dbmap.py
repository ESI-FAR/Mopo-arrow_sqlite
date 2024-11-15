from argparse import ArgumentParser
import json
from string import ascii_lowercase
from random import choices
from typing import cast
import weakref

import pandas as pd

from spinedb_api import DatabaseMapping
from spinedb_api.temp_id import TempId


def idx_name(json_doc: dict, lvls: dict) -> str:
    """Read index_name, if absent, generate one"""
    try:
        name: str = json_doc["index_name"]
    except KeyError:
        while (name := "".join(choices(ascii_lowercase, k=5))) in lvls:
            pass
    finally:
        return name


def json_loads_ts(json_str: str | bytes):
    return pd.Series(json.loads(json_str)["data"])


def make_records(json_doc: dict, idx_lvls: dict, res: list[dict]) -> list[dict]:
    """Parse time-series w/ a multi-index stored as a nested map

    Ask Suvayu for the example DB

    """

    if isinstance(json_doc, dict) and "data" in json_doc:
        for key, val in json_doc["data"]:
            index_name = idx_name(json_doc, idx_lvls)
            make_records(val, {**idx_lvls, index_name: key}, res)
        return res
    else:
        idx_lvls["value"] = json_doc
        res.append(idx_lvls)
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
