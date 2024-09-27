from spinedb_api import DatabaseMapping

path = "path/to/egypt-national.sqlite"

db = DatabaseMapping(f"sqlite:///{path}")

# costs: PublicItem is a set of 10 timeseries
costs, *_ = db.get_items(
    "parameter_value", entity_class_name="model", parameter_definition_name="cost_t"
)

# costs could be represented by a single data frame like this:
# index names: ['database', 'entity_class_name', 'entity_byname', 'parameter_name', 'alternative_name', 'cost_type', 'solve', 'period']
# index values:
# ['egypt-national', 'model', 'cost', 'cost_t', '2018__Import_results@2024-03-28T13:42:34', 'commodity', 'full-year-dispatch', 'p2018']
# ['egypt-national', 'model', 'cost', 'cost_t', '2018__Import_results@2024-03-28T13:42:34', 'CO2', 'full-year-dispatch', 'p2018']
# ['egypt-national', 'model', 'cost', 'cost_t', '2018__Import_results@2024-03-28T13:42:34', 'other_operational', 'full-year-dispatch', 'p2018']
#
# only 'cost_type' has differing values, but that is easily analysed using pandas MultiIndex API.


path2 = "path/to/BB_data.sqlite"
db2 = DatabaseMapping(f"sqlite:///{path2}")
vals = db2.get_items(
    "parameter_value",
    entity_class_name="grid__node__boundary",
    parameter_definition_name="timeseries",
)
# vals: 6 time series; in comparison, the above example only returned
# 1 but the map object had 10 timeseries in it.
