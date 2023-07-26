"""Utilities for working with ADBC, pyarrow and SQlite."""

import adbc_driver_manager.dbapi
import adbc_driver_sqlite.dbapi
import pyarrow as pa

from typing import Any, Callable


def execute_on_sqlite(database_uri: str,
                      my_function: Callable,
                      *args: Any, **kwargs: Any) -> Any:
    """Execute a function on an SQlite database.

    Returns:
        Return of `my_function`.
    """
    with adbc_driver_sqlite.dbapi.connect(database_uri) as connection:
        with connection.cursor() as cursor:
            result = my_function(cursor, *args, **kwargs)
        connection.commit()
        return result

def _insert_data_into_table(cursor: adbc_driver_manager.dbapi.Cursor,
                           table_name: str,
                           data: pa.lib.Table,
                           mode: str) -> int:
    """Create a table and fill it with data or append data to an existing one.

    Args:
        cursor: database cursor
        table_name: name of the table to create or append to
        data: pa table
        mode: "create" a new table, or "append" to an existing one

    Returns:
        Number of rows inserted
    """

    if mode == "create":
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    result = cursor.adbc_ingest(table_name, data, mode=mode)
    return result



def write_data_to_db(database_uri: str,
                     table_name: str,
                     data: pa.lib.Table,
                     mode: str) -> int:
    """Create a table and fill it with data or append data to an existing one.

    Args:
        database_uri: uri of the database
        table_name: name of the table to create or append to
        data: pa table, containing data and schema
        mode: "create" a new table, or "append" to an existing one

    Returns:
        Number of rows inserted
    """
    rows_inserted: int = execute_on_sqlite(database_uri,
                                           _insert_data_into_table,
                                           table_name,
                                           data,
                                           mode)
    return rows_inserted


def database_equality(uri_database_1: str,
                      uri_database_2: str) -> bool:
    """Compare equality of two SQlite databases."""

    connection: adbc_driver_manager.dbapi.Connection

    with adbc_driver_sqlite.dbapi.connect(uri_database_1) as connection:
        objects_1: py.lib.RecordBatchReader = connection.adbc_get_objects()

    with adbc_driver_sqlite.dbapi.connect(uri_database_2) as connection:
        objects_2: py.lib.RecordBatchReader = connection.adbc_get_objects()

    all_record_batches_1 = objects_1.read_all()
    all_record_batches_2 = objects_2.read_all()

    equal: bool = all_record_batches_1.equals(all_record_batches_2)
    return equal
