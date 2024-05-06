from argparse import ArgumentParser
import json
from string import ascii_lowercase
from random import choices
import weakref

import pandas as pd

from spinedb_api import DatabaseMapping


def json_loads_ts(json_str: str):
    return pd.Series(json.loads(json_str)["data"])


def make_records(json_doc: dict, idx_lvls: dict, res: list[dict]) -> list[dict]:
    """Parse time-series w/ a multi-index stored as a nested map

    Ask Suvayu for the example DB

    """

    def idx_name(json_doc: dict, lvls: dict) -> str:
        """Read index_name, if abset, generate one"""
        try:
            name: str = json_doc["index_name"]
        except KeyError:
            while (name := "".join(choices(ascii_lowercase, k=5))) in lvls:
                pass
        finally:
            return name

    if isinstance(json_doc, dict) and "data" in json_doc:
        for key, val in json_doc["data"]:
            index_name = idx_name(json_doc, idx_lvls)
            make_records(val, {**idx_lvls, index_name: key}, res)
        return res
    else:
        idx_lvls["value"] = json_doc
        res.append(idx_lvls)
        return res


def json_loads_multi_dim_ts(json_str: str):
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
        self._finalizer = weakref.finalize(self, self.db.connection.close)
        self.data = {}

    @classmethod
    def prep_df(cls, df: pd.DataFrame, prefix: str, cols: list[str]):
        return df[cols].rename({col: f"{prefix}_{col}" for col in cols}, axis=1)

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
                pd.DataFrame(self.db.parameter_value_list())
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
            df = pd.DataFrame(self.db.parameter_definition_list())
            self.data["param_definitions"] = self.prep_df(df, "parameter", cols)
        return self.data["param_definitions"]

    @property
    def entities(self) -> pd.DataFrame:
        if self.data.get("entities") is None:
            entity = pd.DataFrame(self.db.query(self.db.entity_sq))
            entity = self.prep_df(entity, "entity", ["id", "class_id", "name"])
            eclass = pd.DataFrame(self.db.query(self.db.entity_class_sq))
            eclass = self.prep_df(eclass, "entity_class", ["id", "name"])
            self.data["entities"] = entity.merge(
                eclass, on="entity_class_id", how="left"
            )
        return self.data["entities"]

    @property
    def alternatives(self) -> pd.DataFrame:
        if self.data.get("alternatives") is None:
            df = pd.DataFrame(self.db.alternative_list())
            self.data["alternatives"] = self.prep_df(df, "alternatives", ["id", "name"])
        return self.data["alternatives"]

    def get_ts(self, param: str, **cols) -> pd.DataFrame:
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
        return ts


if __name__ == "__main__":
    parser = ArgumentParser("Read Spine DB")
    parser.add_argument("db_url", help="DB url")
    opts = parser.parse_args()

    handle = MyDBMap(opts.db_url)
    # ts = handle.get_ts("unit_flow")  # 4
    # ts = handle.get_ts("cost_t")  # 268
