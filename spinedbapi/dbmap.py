from argparse import ArgumentParser
import json
from typing import Literal
import weakref

import pandas as pd

from spinedb_api import DatabaseMapping


def make_records(json_doc: dict, idx_lvls: dict, res: list[dict]) -> list[dict]:
    """Parse time-series w/ a multi-index stored as a nested map

    Ask Suvayu for the example DB

    """
    if isinstance(json_doc, dict) and "data" in json_doc:
        for key, val in json_doc["data"]:
            make_records(val, {**idx_lvls, json_doc["index_name"]: key}, res)
        return res
    else:
        idx_lvls["value"] = json_doc
        res.append(idx_lvls)
        return res


class MyDBMap:
    def __init__(self, url: str, value_type: Literal["time_series", "map"]):
        self.db = DatabaseMapping(f"sqlite:///{url}")
        self._finalizer = weakref.finalize(self, self.db.connection.close)
        self.value_type = value_type
        self.data = {}

    @classmethod
    def set_df(cls, attr: str):
        return NotImplemented

    @property
    def param_values(self) -> pd.DataFrame:
        if self.data.get("param_values") is None:
            df = pd.DataFrame(self.db.parameter_value_list().all())
            val_t = df["type"].unique()[0]
            if self.value_type != val_t:
                raise ValueError(f"expected: {self.value_type} != found: {val_t}")
            self.data["param_values"] = df
        return self.data["param_values"]

    @property
    def param_definitions(self) -> pd.DataFrame:
        if self.data.get("param_definitions") is None:
            df = pd.DataFrame(self.db.parameter_definition_list().all())
            self.data["param_definitions"] = df
        return self.data["param_definitions"]

    @property
    def entities(self) -> pd.DataFrame:
        if self.data.get("entities") is None:
            self.data["entities"] = pd.DataFrame(self.db.query(self.db.entity_sq).all())
        return self.data["entities"]

    @property
    def alternatives(self) -> pd.DataFrame:
        if self.data.get("alternatives") is None:
            self.data["alternatives"] = pd.DataFrame(self.db.alternative_list().all())
        return self.data["alternatives"]

    def get_ts(self, param_definition, alternative) -> pd.DataFrame:
        param = self.param_definitions.query(f"name == '{param_definition}'").iloc[0]
        cond = " & ".join(
            (
                f"({p} == {v})"
                for p, v in zip(
                    ("parameter_definition_id", "alternative_id"),
                    (param["id"], alternative),
                )
            )
        )
        df = self.param_values.query(cond)
        entities = df["entity_id"].map(
            lambda i: self.entities[["id", "name"]].query(f"id == {i}").iloc[0, 1]
        )

        if self.value_type == "time_series":
            ts = (
                df["value"]
                .apply(lambda i: pd.Series(json.loads(i)["data"]))
                .assign(entity=entities)
            )
            return ts
        elif self.value_type == "map":
            res = make_records(json.loads(df["value"].iloc[0]), {}, [])
            ts = pd.DataFrame(res)
            ts["time"] = ts["time"].str.strip("t").astype(int)
            # ts["period"] = ts["period"].str.strip("p").astype(int)
            return ts
        else:
            raise ValueError


if __name__ == "__main__":
    parser = ArgumentParser("Read Spine DB")
    parser.add_argument("db_url", help="DB url")
    parser.add_argument("--value-type", type=str, help="Parameter value type")
    opts = parser.parse_args()

    handle = MyDBMap(opts.db_url, opts.value_type)
    # ts = handle.get_ts("unit_flow", 4)
    ts = handle.get_ts("cost_t", 268)
