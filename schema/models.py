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
from datetime import datetime, timedelta
from typing import Annotated, Literal, Type, TypeAlias

from pydantic import RootModel
from pydantic.dataclasses import dataclass
from pydantic.types import StringConstraints


# more verbose alternative to the typealias below
@dataclass(frozen=True)
class Integers_:
    values: list[int]
    type: Type[int]


@dataclass(frozen=True)
class Strings_:
    values: list[str]
    type: Type[str]


@dataclass(frozen=True)
class Datetimes_:
    values: list[datetime]
    type: Type[datetime]


@dataclass(frozen=True)
class Booleans_:
    values: list[bool]
    type: Type[bool]


@dataclass(frozen=True)
class Floats_:
    values: list[float]
    type: Type[float]


Integers: TypeAlias = list[int]
Strings: TypeAlias = list[str]
Datetimes: TypeAlias = list[datetime]
Timedeltas: TypeAlias = list[timedelta]

interval_re = r"(Y|M|D|WD|h|m|s)[0-9]+-[0-9]+"
Interval = Annotated[
    str, StringConstraints(pattern=rf"^{interval_re}[,;]{interval_re}$|^{interval_re}$")
]
TimePattern: TypeAlias = list[Interval]

Booleans: TypeAlias = list[bool]
Floats: TypeAlias = list[float]


@dataclass(frozen=True)
class RLIndex:
    """Run length encoded array

    NOTE: this is not supported by PyArrow, we will have to convert to
    a supported format.

    """

    name: str
    values: Integers | Strings | Datetimes | Timedeltas | TimePattern
    value_type: Literal["integer", "string", "date-time", "duration", "time-pattern"]
    run_len: Integers
    type: Literal["rl_index"] = "rl_index"


@dataclass(frozen=True)
class REIndex:
    """Run end encoded array"""

    name: str
    values: Integers | Strings | Datetimes | Timedeltas | TimePattern
    value_type: Literal["integer", "string", "date-time", "duration", "time-pattern"]
    run_end: list[int]
    type: Literal["re_index"] = "re_index"


@dataclass(frozen=True)
class DEIndex:
    """Dictionary encoded array"""

    name: str
    values: Integers | Strings | Datetimes | Timedeltas | TimePattern
    value_type: Literal["integer", "string", "date-time", "duration", "time-pattern"]
    indices: list[int]
    type: Literal["de_index"] = "de_index"


@dataclass(frozen=True)
class ArrayIndex:
    """Any array that is an index, e.g. a sequence, timestamps, labels"""

    name: str
    values: Integers | Strings | Datetimes | Timedeltas | TimePattern
    value_type: Literal["integer", "string", "date-time", "duration", "time-pattern"]
    type: Literal["array_index"] = "array_index"


@dataclass(frozen=True)
class REArray:
    """Run end encoded array"""

    name: str
    values: Integers | Strings | Floats | Booleans
    value_type: Literal["integer", "string", "number", "boolean"]
    run_end: list[int]
    type: Literal["re_array"] = "re_array"


@dataclass(frozen=True)
class DEArray:
    """Dictionary encoded array"""

    name: str
    values: Integers | Strings | Floats | Booleans
    value_type: Literal["integer", "string", "number", "boolean"]
    indices: list[int]
    type: Literal["de_array"] = "de_array"


@dataclass(frozen=True)
class Array:
    """Array"""

    name: str
    values: Integers | Strings | Floats | Booleans
    value_type: Literal["integer", "string", "number", "boolean"]
    type: Literal["array"] = "array"


@dataclass(frozen=True)
class Table:
    """A table consisting of a set of columns"""

    indices: list[REIndex | DEIndex | ArrayIndex]
    columns: list[REArray | DEArray | Array]
    type: Literal["table"] = "table"


if __name__ == "__main__":
    from argparse import ArgumentParser
    import json
    from pathlib import Path

    parser = ArgumentParser(__doc__)
    parser.add_argument("json_file", help="Path of JSON schema file to write")
    opts = parser.parse_args()

    schema = RootModel[Table].model_json_schema()
    Path(opts.json_file).write_text(json.dumps(schema, indent=2))
