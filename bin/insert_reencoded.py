#!/usr/bin/env python
from argparse import ArgumentParser
from pathlib import Path

from spinedb_api import DatabaseMapping

if __name__ == "__main__":
    pvalues = {
        "flow_node": {"entity_class_name": "flow__node"},
        "flow_node_no": {"entity_name": "flow__node_wind__80NO"},
    }

    parser = ArgumentParser()
    parser.add_argument("db", help="SQLite Spine database file")
    parser.add_argument("files", nargs="+", help="JSON files to insert")
    parser.add_argument("-pv", choices=list(pvalues), help="Parameter value selection")
    opts = parser.parse_args()

    files = list(map(Path, opts.files))
    db = DatabaseMapping(f"sqlite:///{opts.db}", upgrade=True)

    items = db.get_items("parameter_value", **pvalues[opts.pv])
    for item, infile in zip(items, files):
        item.update(value=infile.read_bytes())

    if opts.pv.endswith("_no"):
        db.commit_session("Update flow__node_wind__80NO to new format")
    else:
        db.commit_session("Update flow__node to new format")
