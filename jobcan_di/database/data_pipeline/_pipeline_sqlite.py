"""Data pipeline for SQLite

This module provides functions to initialize tables and get a connection object

Classes
-------
- SQLiteDataSource: Data source class for SQLite

Functions
---------
- get_connection: Get a connection object for SQLite
- get_existing_tables: Get names of existing tables in the database
- init_sqlite_tables: Initialize tables for SQLite
- load_transformed_named_data: Load transformed data into the database
    for named insertion profile
- load_transformed_positional_data: Load transformed data into the database
    for positional insertion profile
"""
import json
import sqlite3
from typing import Any, ClassVar

from jobcan_di.database.schema_toolkit import TableStructure, SQLDialect
from ._source_result_format import SourceResultFormat
from ._data_source import DBDataSource, UnitOfResult



SQLiteConnectionAlias = sqlite3.Connection
"""Type alias for SQLite connection""" # TODO: Add TypeAlias type hint for this (Python 3.10~)

def get_connection(path:str, *, readonly:bool=False) -> SQLiteConnectionAlias:
    """Get a connection object for SQLite

    Parameters
    ----------
    path : str
        Path to the database file
    readonly : bool, optional
        If True, open the database in read-only mode

    Returns
    -------
    SQLiteConnectionAlias
        Connection object
    """
    if not readonly:
        return sqlite3.connect(path)

    return sqlite3.connect(
        f"file:{path}?mode=ro",
        uri=True
    )

#
# Table Initialization
#

def get_existing_tables(conn:sqlite3.Connection) -> list[str]:
    """Get names of existing tables in the database

    Parameters
    ----------
    conn : sqlite3.Connection
        Connection object

    Returns
    -------
    list[str]
        List of table names
    """
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    return [table[0] for table in tables]

def init_sqlite_tables(conn:sqlite3.Connection,
                       table_structure:TableStructure) -> None:
    """Initialize tables for SQLite

    Parameters
    ----------
    table_structure : TableStructure
        Table structure
    conn : sqlite3.Connection
        Connection object
    """
    conn.execute(table_structure.raw_sql)
    conn.commit()

def extract_data_at_once(
        path:str, query:str, result_format:SourceResultFormat
    ) -> list[UnitOfResult]:
    """Extract data from the SQLite database at once

    Parameters
    ----------
    path : str
        Path to the database file
    query : str
        SQL query to retrieve the data
    result_format : SourceResultFormat
        Format of the result (multiple-results, single-result, ...)

    Returns
    -------
    list[tuple[Any, ...]]
        Extracted data
    """
    conn = get_connection(path, readonly=True)
    cursor = conn.cursor()

    cursor.execute(query)
    data = cursor.fetchall()

    # Deserialize JSON data
    if result_format == SourceResultFormat.JSON_OBJECT_RESULTS:
        data = [json.loads(row[0]) for row in data]
    # TODO: Add other result formats

    conn.close()

    return data


#
# Data source
#

class SQLiteDataSource(DBDataSource):
    """SQLite data source

    Attributes
    ----------
    name : str
        Name of the data source
    ttype : str
        Type of the data source
    result_format : SourceResultFormat
        Format of the result (multiple-results, single-result, ...)
    results_key : str
        Key name corresponding to the list of data in the JSON object.
        For `SourceResultFormat.NESTED_JSON` (Other formats ignore this attribute)
    path : str
        Path to the SQLite database
    query : str
        SQL query to retrieve the data
    """
    ttype: ClassVar[str] = "SQLite"
    sql_dialect: ClassVar[SQLDialect] = SQLDialect.SQLITE

    def __init__(self, name: str,
                 result_format: SourceResultFormat, results_key: str,
                 path: str, query: str):
        super().__init__(name, result_format, results_key, query)
        self.path = path

    def extract_data(self) -> list[UnitOfResult]:
        """Extract data from the SQLite database"""
        return extract_data_at_once(self.path, self.query, self.result_format)

#
# Data loading (Load; ETL)
#

def load_transformed_named_data(
        conn:sqlite3.Connection,
        query:str,
        transformed:list[dict[str, Any]]
    ) -> bool:
    """Load transformed data into the database
    for named insertion profile

    Parameters
    ----------
    conn : sqlite3.Connection
        Connection object
    query : str
        SQL query to insert data into the table
    transformed : list[dict[str, Any]]
        transformed data

    Returns
    -------
    bool
        True if the insertion was successful
    """
    cursor = conn.cursor()

    for row in transformed:
        cursor.execute(query, row)

    conn.commit()
    return True

def load_transformed_positional_data(
        conn:sqlite3.Connection,
        query:str,
        transformed:list[tuple[Any]]
    ) -> bool:
    """Load transformed data into the database
    for positional insertion profile

    Parameters
    ----------
    conn : sqlite3.Connection
        Connection object
    query : str
        SQL query to insert data into the table
    transformed : list[tuple[Any]]
        transformed data

    Returns
    -------
    bool
        True if the insertion was successful
    """
    cursor = conn.cursor()

    for row in transformed:
        cursor.execute(query, row)

    conn.commit()
    return True
