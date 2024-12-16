"""
Module for the data pipeline

This module provides functions to perform ETL processing
based on the instance of `PipelineDefinition` obtained by
`data_pipeline.parser`. Here, ETL processing refers to
the process of acquiring (Extract), processing (Transform),
and writing (Load) data to DB.

Example
-------
The following example shows a simple way to perform ETL processing
using this package.

If `db_definition.toml` is written to create a `users` table
in `example_db.sqlite`, the execution of the following code
will create that database file and create that table.

```python
from jobcan_di.database.data_pipeline.parser import parse_toml
from jobcan_di.database.data_pipeline.pipeline import execute_etl_pipeline

# Get pipeline definition from toml file
pipeline_def = parse_toml('db_definition.toml')

# Execute ETL processing
execute_etl_pipeline(pipeline_def)
```
"""
from typing import Any, Optional, Callable

# From schema_toolkit
from jobcan_di.database.schema_toolkit import TableStructure, SQLDialect
from jobcan_di.database.schema_toolkit.validator import check_table_structure
# Pipeline definitions
from ._db_definition import DBDefinition, SQLiteDBDefinition
from ._insertion_profile import InsertionProfile, NamedInsertionProfile, PositionalInsertionProfile
from ._pipeline_definition import PipelineDefinition
# Pipeline components
from . import _pipeline_sqlite as sqlite_pipeline
from ._pipeline_sqlite import SQLiteConnectionAlias
from .transformation import transform_named_data, transform_positional_data



#
# Initialization
#

def get_connection(dialect:SQLDialect, authentications:dict[str, str]) -> Any:
    """Get a connection object for the given SQL dialect

    Parameters
    ----------
    dialect : SQLDialect
        SQL dialect
    authentications : dict[str, str]
        Authentication information;
        For SQLite, the path to the database file

    Returns
    -------
    Any
        Connection object
    """
    if dialect == SQLDialect.SQLITE:
        return sqlite_pipeline.get_connection(authentications["path"])

#
# Table Initialization
#

def init_tables(table_definition:DBDefinition,
                *, conn:Optional[Any]=None):
    """Initialize tables

    Parameters
    ----------
    table_definition : DBDefinition
        Database definition
    conn : Any, optional
        Connection object;
        if None, the connection will be created
    """
    if conn is None:
        conn = get_connection(table_definition.ttype, table_definition.authentications)

    # Check the table definition
    if isinstance(table_definition, SQLiteDBDefinition):
        # Prepare and validate connection
        if not isinstance(conn, SQLiteConnectionAlias):
            raise ValueError("The connection object must be a SQLite connection")

        # Prepare table initialization function
        existing_tables = sqlite_pipeline.get_existing_tables(conn)
        table_initiator: Callable[[Any, TableStructure], None] = sqlite_pipeline.init_sqlite_tables
    else:
        dialect = table_definition.ttype
        raise NotImplementedError(f"Table initialization for {dialect} is not implemented")

    # Initialize tables
    for table in table_definition.tables:
        if table.name not in existing_tables:
            # Table does not exist
            table_initiator(conn, table)
        else:
            # Already exists -> Check the table structure
            err = check_table_structure(conn, table, dialect=table_definition.ttype)
            if err is not None:
                # Update the table (ALTER TABLE)
                raise NotImplementedError(
                    f"Differences exist between the current '{table.name}' table "\
                    f"and the definition: {err}"
                )

#
# Main (ETL) Pipeline
# (Extract -> Transform -> Load)
#

def execute_etl_pipeline(definition:PipelineDefinition) -> None:
    """Execute the data pipeline.
    Extract data from the sources, transform it, and load it into the target table.

    Parameters
    ----------
    definition : PipelineDefinition
        Pipeline definition
    """
    # Create connection object to load
    target_conn = get_connection(definition.table_definition.ttype,
                                 definition.table_definition.authentications)

    # Initialize tables
    init_tables(definition.table_definition, conn=target_conn)

    # Extract data
    extracted: dict[str, Any] = {}
    for source in definition.data_link.sources:
        extracted[source.name] = source.extract_data()

    # Transform & Load
    for _, profile in definition.data_link.insertion_profiles.items():
        _transform_and_load_data(target_conn, profile, extracted)

def _transform_and_load_data(
        target_conn:Any,
        profile:InsertionProfile,
        extracted:dict[str, Any]) -> None:
    """Transform and load data into the target table

    Parameters
    ----------
    target_conn : Any
        Connection object for the target table
    profile : InsertionProfile
        Insertion profile
    extracted : dict[str, Any]
        Extracted data from the sources
    """
    if isinstance(profile, NamedInsertionProfile):
        # Transform data for the `table_name` table
        transformed = transform_named_data(
            extracted, profile.sources, profile.named_parameters(),
            conversion_method=profile.conversion_methods()
        )

        # Load data
        load_transformed_named_data(target_conn, profile.query, transformed)
    elif isinstance(profile, PositionalInsertionProfile):
        # Transform data for the `table_name` table
        transformed = transform_positional_data(
            extracted, profile.sources, profile.positional_parameters(),
            conversion_method=profile.conversion_methods()
        )

        # Load data
        load_transformed_positional_data(target_conn, profile.query, transformed)
    else:
        raise ValueError(f"Unsupported insertion profile: {profile}")

#
# Loading functions (L from ETL)
#

def load_transformed_named_data(
        conn: Any,
        query: str,
        transformed: list[dict[str, Any]]
    ) -> bool:
    """Load transformed data into the database
    for named insertion profile

    Parameters
    ----------
    conn : Any
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
    if isinstance(conn, sqlite_pipeline.SQLiteConnectionAlias):
        return sqlite_pipeline.load_transformed_named_data(
            conn, query, transformed
        )
    else:
        raise ValueError("Unsupported connection type" \
                         f"({type(conn).__name__})")

def load_transformed_positional_data(
        conn: Any,
        query: str,
        transformed: list[tuple[Any]]
    ) -> bool:
    """Load transformed data into the database
    for positional insertion profile

    Parameters
    ----------
    conn : Any
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
    if isinstance(conn, sqlite_pipeline.SQLiteConnectionAlias):
        return sqlite_pipeline.load_transformed_positional_data(
            conn, query, transformed
        )
    else:
        raise ValueError("Unsupported connection type" \
                         f"({type(conn).__name__}")
