# Reading the Spine database using `spinedb_api`

- [x] use `spinedb_api` as a library to read the database, and create `pandas.DataFrame`s.
- [ ] use `spinedb_api` to read the database and create datastructures
  similar to Spine Toolbox (baseline)

# Example datasets
- Egypt National: has time-series with multi-index (ask Suvayu)
- BB\_data: has a variety of parameter\_values (ask Suvayu / EU ESI Mopo sharepoint:General\WP3 Toolbox CONFIDENTIAL\data_examples)

# SQL to read dataset

## BB\_data

```sql
SELECT
	pv.id,
	pv.alternative_id,
	pdefs.name AS parameter,
	ec.name AS entity_class,
	e.name AS entity,
	pv.value
FROM parameter_value pv
JOIN parameter_definition pdefs, entity_class ec, entity e
ON
	pv.parameter_definition_id = pdefs.id AND
	pv.entity_class_id = ec.id AND
	pv.entity_id = e.id
WHERE pdefs.name = 'timeseries';
```
