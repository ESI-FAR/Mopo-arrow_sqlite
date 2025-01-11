import contextlib
import sqlite3

import pandas as pd

# This works for the time-series generated after following the spineopt tutorial
# https://spine-tools.github.io/SpineOpt.jl/latest/tutorial/unit_commitment/

query = """
SELECT
  pv.id,
  pv.alternative_id,
  pv.entity_id,
  e.name as entity,
  pv.parameter_definition_id,
  pd.name AS param,
  ts.key as time,
  ts.value
FROM
  parameter_value pv,
  json_each(json(pv.value), '$.data') ts
    LEFT JOIN entity e ON pv.entity_id = e.id
    LEFT JOIN parameter_definition pd ON pv.parameter_definition_id = pd.id
WHERE pv.parameter_definition_id = 1;
"""


def read_ts_params(dbfile: str):
    with contextlib.closing(sqlite3.connect(dbfile)) as con:
        df = pd.read_sql(query, con)
    return df
