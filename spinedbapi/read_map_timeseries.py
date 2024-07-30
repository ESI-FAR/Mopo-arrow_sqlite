#!/usr/bin/env python
from argparse import ArgumentParser

from spinedb_api import DatabaseMapping

from dbmap import json_loads_multi_dim_ts

__doc__ = f"""Read map-style timeseries from a Spine db

Run interactively to inspect the timeseries:

$ ipython -i ./{__file__.rsplit("/", 1)[-1]} path/to/db.sqlite

"""

parser = ArgumentParser(__doc__)
parser.add_argument("db", help="SQLite Spine database file")

if __name__ == "__main__":
    opts = parser.parse_args()
    db = DatabaseMapping(f"sqlite:///{opts.db}")
    rows = db.get_items(
        "parameter_value",
        entity_class_name="grid__node__boundary",
        parameter_definition_name="timeseries",
    )
    ts_list = list(map(lambda i: json_loads_multi_dim_ts(i["value"]), rows))
