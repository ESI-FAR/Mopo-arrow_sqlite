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

NullableIntegers: TypeAlias = list[int | None]
NullableFloats: TypeAlias = list[float | None]
NullableStrings: TypeAlias = list[str | None]
NullableBooleans: TypeAlias = list[bool | None]
NullableDatetimes: TypeAlias = list[datetime | None]
NullableTimedeltas: TypeAlias = list[timedelta | None]
NullableTimePatterns: TypeAlias = list[TimePattern | None]

IndexTypes: TypeAlias = Integers | Strings | Datetimes | Timedeltas | TimePatterns
ValueTypes: TypeAlias = (
    Integers | Strings | Floats | Booleans | Datetimes | Timedeltas | TimePatterns
)
NullableValueTypes: TypeAlias = (
    NullableIntegers
    | NullableStrings
    | NullableFloats
    | NullableBooleans
    | NullableDatetimes
    | NullableTimedeltas
    | NullableTimePatterns
)


ValueTypeNames: TypeAlias = Literal[
    "string", "integer", "number", "boolean", "date-time", "duration", "time-pattern"
]
IndexValueTypeNames: TypeAlias = Literal[
    "string", "integer", "date-time", "duration", "time-pattern"
]

type_map: dict[type, ValueTypeNames] = {
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
    values: IndexTypes
    value_type: IndexValueTypeNames = field(init=False)
    type: Literal["rl_index"] = "rl_index"


@dataclass(frozen=True)
class REIndex(_TypeInferMixin):
    """Run end encoded array"""

    name: str
    run_end: Integers
    values: IndexTypes
    value_type: IndexValueTypeNames = field(init=False)
    type: Literal["re_index"] = "re_index"


@dataclass(frozen=True)
class DEIndex(_TypeInferMixin):
    """Dictionary encoded array"""

    name: str
    indices: Integers
    values: IndexTypes
    value_type: IndexValueTypeNames = field(init=False)
    type: Literal["de_index"] = "de_index"


@dataclass(frozen=True)
class ArrayIndex(_TypeInferMixin):
    """Any array that is an index, e.g. a sequence, timestamps, labels"""

    name: str
    values: IndexTypes
    value_type: IndexValueTypeNames = field(init=False)
    type: Literal["array_index"] = "array_index"


@dataclass(frozen=True)
class RLArray(_TypeInferMixin):
    """Run length encoded array

    NOTE: this is not supported by PyArrow, if we use it, we will have
    to convert to a supported format.

    """

    name: str
    run_len: Integers
    values: NullableValueTypes
    value_type: ValueTypeNames = field(init=False)
    type: Literal["rl_array"] = "rl_array"


@dataclass(frozen=True)
class REArray(_TypeInferMixin):
    """Run end encoded array"""

    name: str
    run_end: Integers
    values: NullableValueTypes
    value_type: ValueTypeNames = field(init=False)
    type: Literal["re_array"] = "re_array"


@dataclass(frozen=True)
class DEArray(_TypeInferMixin):
    """Dictionary encoded array"""

    name: str
    indices: NullableIntegers
    values: NullableValueTypes
    value_type: ValueTypeNames = field(init=False)
    type: Literal["de_array"] = "de_array"


@dataclass(frozen=True)
class Array(_TypeInferMixin):
    """Array"""

    name: str
    values: NullableValueTypes
    value_type: ValueTypeNames = field(init=False)
    type: Literal["array"] = "array"


# NOTE: To add run-length encoding to the schema, add it to the
# following type union following which, we need to implement a
# converter to an Arrow array type
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
