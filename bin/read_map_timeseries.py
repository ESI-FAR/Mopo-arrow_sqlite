#!/usr/bin/env python
from argparse import ArgumentParser
import json
from pathlib import Path

from rich.pretty import pprint

from spinedb_api import DatabaseMapping

from arrow_expts.spine.dbmap import json_loads_multi_dim_ts

__doc__ = f"""Read map-style timeseries from a Spine db

Run interactively to inspect the timeseries:

$ ipython -i ./{__file__.rsplit("/", 1)[-1]} path/to/db.sqlite -pv <parameter value options>

"""

db_pv = {
    "egypt-national.sqlite": ["unit_node_flow"],
    "BB_data.sqlite": [
        "grid_node_ts",
        "grid_node_influx",
        "flow_node_cf",
        "flow_node_cf_wind",
    ],
}
pvalues = {
    "unit_node_flow": {
        "entity_class_name": "unit__node",
        "parameter_definition_name": "flow_t",
    },
    "grid_node_ts": {
        "entity_class_name": "grid__node__boundary",
        "parameter_definition_name": "timeseries",
    },  # len: [8736, 8736, 8736, 8736, 8736, 8736]
    "grid_node_influx": {
        "entity_class_name": "grid__node",
        "parameter_definition_name": "influx",
    },  # len: [218400, 218400, 218400, 218400, 218400, 218400, 8736, 8736, 8736, 8736]
    "flow_node_cf": {
        "entity_class_name": "flow__node",
        "parameter_definition_name": "capacityFactor",
    },
    "flow_node_cf_wind": {"entity_name": "flow__node_wind__80NO"},
}

parser = ArgumentParser(__doc__)
parser.add_argument("db", help="SQLite Spine database file")
parser.add_argument("-pv", choices=list(pvalues), help="Parameter value selection")


def dump_to_file(data: str | bytes, path: str):
    match data:
        case str():
            Path(path).write_text(data)
        case bytes():
            Path(path).write_bytes(data)


if __name__ == "__main__":
    opts = parser.parse_args()
    db_path = Path(opts.db)

    if db_path.name not in db_pv:
        raise ValueError(f"Unknown db: only supported: {list(db_pv)}")
    if opts.pv not in db_pv[db_path.name]:
        raise ValueError(
            f"Unsupported db parameter value combination: {db_path.name} -> {opts.pv}"
        )

    db = DatabaseMapping(f"sqlite:///{opts.db}", upgrade=True)

    _rows = db.get_items("parameter_value", **pvalues[opts.pv])
    # parsed = list(map(lambda i: json_loads_multi_dim_ts(i["value"]), _rows))

    # NOTE: this is a different data structure, so probably need
    # something else to parse (maybe one of the already implemented
    # parsers in dbmap works); dump an example
    if opts.pv == "flow_node_cf_wind":
        for i, data in enumerate(_rows):
            # dump_to_file(data["value"], f"capacity-factor-dump-{i}.json")
            dump_to_file(data["value"], f"wind-node-dump-{i}.json")
            pprint(json.loads(data["value"]), max_length=4)
