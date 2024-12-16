"""Package providing functions and classes for ETL processing

This package provides functionality for implementing ETL (Extract, Transform, Load) processes
to extract data, transform it, and load it into databases.

Classes (Summary)
-------
PipelineDefinition
    Class for defining ETL processes.
    Holds table definitions (table_definition)
    and ETL process definitions (data_link).

DataLink
    Class for holding ETL process definitions.
    Defines data extraction methods (sources) and
    data transformation/loading methods (insertion_profiles).

DataSource
    Class for holding data extraction methods.
    Extracts data via the extract_data method.

Module Structure
---------------
data_pipeline.parser
    Provides functions to obtain PipelineDefinition from TOML files.
    Main functions:
    - parse_toml: Get PipelineDefinition from TOML file
    - parse_toml_data: Get PipelineDefinition from TOML string

data_pipeline.pipeline
    Provides functions to execute ETL processes.
    Main functions:
    - execute_etl_pipeline: Execute ETL process based on PipelineDefinition

Examples
--------
>>> from data_pipeline.parser import parse_toml
>>> from data_pipeline.pipeline import execute_etl_pipeline
>>>
>>> # Get pipeline definition from TOML file
>>> pipeline_def = parse_toml('db_definition.toml')
>>>
>>> # Execute ETL process
>>> execute_etl_pipeline(pipeline_def)

See Also
--------
jobcan_di.database : Parent package for database operations

Notes
-----
TOML files consist of the following sections:
- [table_definitions]: Define destination tables
- [data_links]: Define ETL processes
  - [[data_links.sources]]: Define data extraction methods
  - [data_links.insertion_profiles]: Define data transformation and loading methods

Classes
-------
- Define data sources
  - `SourceResultFormat`: Class for defining the format of data sources
  - `DataSource`: Abstract class for data sources
    - `APIDataSource`: Class for extracting data from APIs
    - `DBDataSource`: Class for extracting data from databases
    - `RawDataSource`: Class for extracting raw data
    - `SQLiteDataSource`: Class for extracting data from SQLite databases
- Define pipeline definitions
  - `DBDefinition`: Abstract class for defining database structures
  - `SQLiteDBDefinition`: Class for defining SQLite database structures
  - `InsertionProfile`: Abstract class for defining data transformation/loading methods
    - `NamedInsertionProfile`: Class for defining named parameter insertion profiles
    - `PositionalInsertionProfile`: Class for defining positional parameter insertion profiles
  - `DataLink`: Class for defining ETL process definitions
  - `PipelineDefinition`: Class for defining ETL processes

Functions
---------
- `parse_toml`: Get PipelineDefinition from TOML file
- `parse_toml_data`: Get PipelineDefinition from TOML string
- `parse_table_definitions`: Parse table definitions from TOML file
- `parse_data_link`: Parse data link from TOML file
- `parse_data_source`: Parse data source from TOML file

Constants
---------
- `DEFAULT_RESULTS_KEY`: Default key for results in data sources
"""
# Data source
from ._source_result_format import (
    SourceResultFormat, DEFAULT_RESULTS_KEY
)
from ._data_source import (
    DataSource, APIDataSource, DBDataSource, RawDataSource
)
from ._pipeline_sqlite import SQLiteDataSource

# Pipeline definitions
from ._db_definition import DBDefinition, SQLiteDBDefinition
from ._insertion_profile import (
    InsertionProfile, NamedInsertionProfile, PositionalInsertionProfile,
    ParameterConversionMethod
)
from ._pipeline_definition import DataLink, PipelineDefinition

# Parser for pipeline definitions
from .parser import (
    parse_toml, parse_toml_data,
    parse_table_definitions, parse_data_link, parse_data_source
)
