#!/usr/bin/env python
from argparse import ArgumentParser
from pathlib import Path

from spinedb_api import DatabaseMapping

from dbmap import json_loads_multi_dim_ts

__doc__ = f"""Read map-style timeseries from a Spine db

Run interactively to inspect the timeseries:

$ ipython -i ./{__file__.rsplit("/", 1)[-1]} path/to/db.sqlite

"""

parser = ArgumentParser(__doc__)
parser.add_argument("db", help="SQLite Spine database file")


def dump_to_file(data: str | bytes, path: str):
    match data:
        case str():
            Path(path).write_text(data)
        case bytes():
            Path(path).write_bytes(data)


if __name__ == "__main__":
    opts = parser.parse_args()
    db = DatabaseMapping(f"sqlite:///{opts.db}")
    ts_rows = db.get_items(
        "parameter_value",
        entity_class_name="grid__node__boundary",
        parameter_definition_name="timeseries",
    )
    ts_list = list(map(lambda i: json_loads_multi_dim_ts(i["value"]), ts_rows))
    # len: [8736, 8736, 8736, 8736, 8736, 8736]

    influx_rows = db.get_items(
        "parameter_value",
        entity_class_name="grid__node",
        parameter_definition_name="influx",
    )
    influx_list = list(map(lambda i: json_loads_multi_dim_ts(i["value"]), influx_rows))
    # len: [218400, 218400, 218400, 218400, 218400, 218400, 8736, 8736, 8736, 8736]

    cf_rows = db.get_items(
        "parameter_value",
        entity_class_name="flow__node",
        parameter_definition_name="capacityFactor",
    )
    # NOTE: this is a different data structure, so probably need
    # something else to parse (maybe one of the already implemented
    # parsers in dbmap works); dump an example
    dump_to_file(cf_rows[0]["value"], "capacity-factor-dump.json")
