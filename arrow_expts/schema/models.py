#!/usr/bin/env python
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pandas>=2",
#   "pydantic>=2",
# ]
# ///

"""Write JSON schema for JSON blob in SpineDB

"""

# from dataclasses import dataclass
# from dataclasses import field
from datetime import datetime, timedelta
from typing import Annotated, Literal, Type, TypeAlias

import pandas as pd
from pydantic import RootModel
from pydantic.dataclasses import dataclass
from pydantic.dataclasses import Field as field
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


NullableFloats: TypeAlias = list[float | None]
NullableIntegers: TypeAlias = list[int | None]
NullableStrings: TypeAlias = list[str | None]
NullableBooleans: TypeAlias = list[bool | None]

Floats: TypeAlias = list[float]
Integers: TypeAlias = list[int]
Strings: TypeAlias = list[str]
Booleans: TypeAlias = list[bool]

Datetimes: TypeAlias = list[datetime]
Timedeltas: TypeAlias = list[timedelta]

# FIXME: how to do w/o Pydantic?
time_pat_re = r"(Y|M|D|WD|h|m|s)[0-9]+-[0-9]+"
TimePattern: TypeAlias = Annotated[str, StringConstraints(pattern=time_pat_re)]
TimePatterns: TypeAlias = list[TimePattern]


ValueType: TypeAlias = Literal[
    "string", "integer", "number", "boolean", "date-time", "duration", "time-pattern"
]
type_map: dict[type, ValueType] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    datetime: "date-time",
    pd.Timestamp: "date-time",
    timedelta: "duration",
    pd.Timedelta: "duration",
    TimePattern: "time-pattern",
}


class _TypeInferMixin:
    def __post_init__(self):
        value_type, *_ = set(map(type, getattr(self, "values"))) - {type(None)}
        # NOTE: have to do it like this since inherited dataclasses are frozen
        super().__setattr__("value_type", type_map[value_type])


@dataclass(frozen=True)
class RLIndex(_TypeInferMixin):
    """Run length encoded array

    NOTE: this is not supported by PyArrow, if we use it, we will have
    to convert to a supported format.

    """

    name: str
    run_len: Integers
    values: Strings | Datetimes | Timedeltas | TimePatterns
    value_type: Literal["string", "date-time", "duration", "time-pattern"] = field(
        init=False
    )
    type: Literal["rl_index"] = "rl_index"


@dataclass(frozen=True)
class REIndex(_TypeInferMixin):
    """Run end encoded array"""

    name: str
    run_end: list[int]
    values: Strings | Datetimes | Timedeltas | TimePatterns
    value_type: Literal["string", "date-time", "duration", "time-pattern"] = field(
        init=False
    )
    type: Literal["re_index"] = "re_index"


@dataclass(frozen=True)
class DEIndex(_TypeInferMixin):
    """Dictionary encoded array"""

    name: str
    indices: list[int]
    values: Strings | Datetimes | Timedeltas | TimePatterns
    value_type: Literal["string", "date-time", "duration", "time-pattern"] = field(
        init=False
    )
    type: Literal["de_index"] = "de_index"


@dataclass(frozen=True)
class ArrayIndex(_TypeInferMixin):
    """Any array that is an index, e.g. a sequence, timestamps, labels"""

    name: str
    values: Integers | Strings | Datetimes | Timedeltas | TimePatterns
    value_type: Literal[
        "integer", "string", "date-time", "duration", "time-pattern"
    ] = field(init=False)
    type: Literal["array_index"] = "array_index"


@dataclass(frozen=True)
class REArray(_TypeInferMixin):
    """Run end encoded array

    Note: Run end encoded arrays do not support null/missing values
    """

    name: str
    run_end: list[int]
    values: Strings | Floats | Booleans
    value_type: Literal["string", "number", "boolean"] = field(init=False)
    type: Literal["re_array"] = "re_array"


@dataclass(frozen=True)
class DEArray(_TypeInferMixin):
    """Dictionary encoded array"""

    name: str
    indices: list[int | None]
    values: Strings | Floats | Booleans
    value_type: Literal["string", "number", "boolean"] = field(init=False)
    type: Literal["de_array"] = "de_array"


@dataclass(frozen=True)
class Array(_TypeInferMixin):
    """Array"""

    name: str
    values: NullableIntegers | NullableStrings | NullableFloats | NullableBooleans
    value_type: Literal["integer", "string", "number", "boolean"] = field(init=False)
    type: Literal["array"] = "array"


Table: TypeAlias = list[REIndex | DEIndex | ArrayIndex | REArray | DEArray | Array]


if __name__ == "__main__":
    from argparse import ArgumentParser
    import json
    from pathlib import Path

    parser = ArgumentParser(__doc__)
    parser.add_argument("json_file", help="Path of JSON schema file to write")
    opts = parser.parse_args()

    schema = RootModel[Table].model_json_schema()
    Path(opts.json_file).write_text(json.dumps(schema, indent=2))
