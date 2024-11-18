#!/usr/bin/env python
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pydantic>=2",
# ]
# ///

"""Write JSON schema for JSON blob in SpineDB

"""

# from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar

from pydantic import RootModel
from pydantic.dataclasses import dataclass


@dataclass(frozen=True)
class REIndex:
    """Run end encoded array"""

    name: str
    values: list[str | float | int | datetime]
    run_end: list[int]
    type: str = "re_index"


@dataclass(frozen=True)
class DEIndex:
    """Dictionary encoded array"""

    name: str
    values: list[str | float | int | datetime]
    indices: list[int]
    type: str = "de_index"


@dataclass(frozen=True)
class ArrayIndex:
    """Any array that is an index, e.g. a sequence, timestamps, labels"""

    name: str
    values: list[str | int | datetime]
    type: str = "array_index"


@dataclass(frozen=True)
class Array:
    """Array"""

    name: str
    values: list[str | float | int]
    type: str = "array"


@dataclass(frozen=True)
class Table:
    """A table consisting of a set of columns"""

    indices: list[REIndex | DEIndex | ArrayIndex]
    columns: list[Array]
    type: str = "table"


@dataclass(frozen=True)
class Tables:
    """A table consisting of multiple batches of smaller tables"""

    batches: list[Table]
    type: str = "tables"


JSONBlob = TypeVar("JSONBlob", Tables, Table)


if __name__ == "__main__":
    from argparse import ArgumentParser
    import json
    from pathlib import Path

    parser = ArgumentParser(__doc__)
    parser.add_argument("json_file", help="Path of JSON schema file to write")
    opts = parser.parse_args()

    schema = RootModel[JSONBlob].model_json_schema()
    Path(opts.json_file).write_text(json.dumps(schema, indent=2))
