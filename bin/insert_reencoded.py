#!/usr/bin/env python
from argparse import ArgumentParser
from pathlib import Path

from rich.pretty import pprint

from spinedb_api import DatabaseMapping

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("db", help="SQLite Spine database file")
    parser.add_argument("files", nargs="+", help="JSON files to insert")
    opts = parser.parse_args()

    files = list(map(Path, opts.files))
    db = DatabaseMapping(f"sqlite:///{opts.db}")

    items = db.get_items("parameter_value", entity_class_name="flow__node")
    for item, infile in zip(items, files):
        item.update(value=infile.read_bytes())
    db.commit_session("Update flow__node to new format")

    # items = db.get_items("parameter_value", entity_name="flow__node_wind__80NO")
    # for item, infile in zip(items, files):
    #     item.update(value=infile.read_bytes())
    # db.commit_session("Update flow__node_wind__80NO to new format")
