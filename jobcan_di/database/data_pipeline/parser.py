"""
This module provides functions such as `parse_toml` to obtain
instances of `PipelineDefinition` from TOML files.

Functions
---------
- parse_toml: Parse a TOML file and return a PipelineDefinition object
- parse_toml_data: Parse a TOML string and return a PipelineDefinition object
- parse_table_definitions: Parse the table definitions in the TOML data
- parse_data_link: Parse the information about where to get data from
      and which tables to store data in.
- parse_data_source: Parse a data source in the TOML data

Examples
--------
The format of TOML files that can be loaded using the `parse_toml`
and `parse_toml_data` functions is similar to
[db_definition.toml](../../test/db_definition.toml) and has the following structure:

- `[table_definitions]`: Section defining destination tables
- `[data_links]`: Section defining ETL processes
  - `[[data_links.sources]]`: Section defining data retrieval methods
  - `[data_links.insertion_profiles]`: Section defining data processing and writing methods
    - Specify table names defined in the `table_definitions` section
    - Example: When defining a `users` table, specify conversion and
      writing methods under `[data_links.insertion_profiles.users]`

Additionally, the following functions are provided to convert each section of
`table_definitions`, `data_link`, and `data_link.sources` into class instances.
All functions take arguments of type `tomlkit.items.Table`:

```python
from jobcan_di.database.data_pipeline import (
    PipelineDefinition,
    TableDefinition, DataLink, DataSource
)
from jobcan_di.database.data_pipeline.parser import (
    parse_toml_data, parse_table_definitions,
    parse_data_link, parse_data_source
)
import tomlkit

# Loading TOML file
with open('db_definition.toml') as f:
    toml_str = f.read()
    toml_data = tomlkit.parse(toml_str)

# Get PipelineDefinition instance from TOML data
pipeline_def = parse_toml_data(toml_data)

# Can also convert table_definitions and data_link sections into instances
table_def: TableDefinition = parse_table_definitions(toml_data['table_definitions'])
data_link: DataLink = parse_data_link(toml_data['data_link'])

# Can also convert each section of data_link.sources into instances
sources: list[DataSource] = []
for source in toml_data['data_link']['sources']:
    sources.append(parse_data_source(source))
```
"""
from typing import Final, Optional, Union

import tomlkit as toml
import tomlkit.items as toml_items

# From schema_toolkit
from jobcan_di.database.schema_toolkit import SQLDialect, TableStructure
from jobcan_di.database.schema_toolkit.sql_parser import parse_sql
# Data source
from ._source_result_format import SourceResultFormat, DEFAULT_RESULTS_KEY
from ._data_source import APIDataSource, DataSource
from ._pipeline_sqlite import SQLiteDataSource
# Pipeline definition
from ._db_definition import DBDefinition, SQLiteDBDefinition
from ._insertion_profile import (
    InsertionProfile,
    PositionalInsertionProfile, NamedInsertionProfile,
    ParameterConversionMethod, Source
)
from ._pipeline_definition import PipelineDefinition, DataLink



def parse_toml(file_path:str) -> PipelineDefinition:
    """Parse a TOML file and return a PipelineDefinition object

    Parameters
    ----------
    file_path : str
        Path to the TOML file

    Returns
    -------
    PipelineDefinition
        Pipeline definition
    """
    with open(file_path, 'r', encoding="utf-8") as f:
        data = f.read()

    return parse_toml_data(data)

def parse_toml_data(data:str) -> PipelineDefinition:
    """Parse a TOML string and return a PipelineDefinition object

    Parameters
    ----------
    data : str
        TOML data

    Returns
    -------
    PipelineDefinition
        Pipeline definition
    """
    toml_data = toml.loads(data)

    td = toml_data.get("table_definitions")
    if (td is None) or (not isinstance(td, toml_items.Table)):
        raise ValueError("Table definition ('table_definition') not found " \
                         "in the TOML data or is not a table")
    table_definition = parse_table_definitions(td)

    dl = toml_data.get("data_link")
    if (dl is None) or (not isinstance(dl, toml_items.Table)):
        raise ValueError("Data link ('data_link') not found " \
                         "in the TOML data or is not a table")
    data_link = parse_data_link(dl)

    return PipelineDefinition(table_definition=table_definition, data_link=data_link)

#
# Parse table_definitions
#

def parse_table_definitions(table_definitions:toml_items.Table) -> DBDefinition:
    """Parse the table definitions in the TOML data

    Parameters
    ----------
    table_definitions : tomlkit.items.Table
        Table definitions

    Returns
    -------
    DBDefinition
        Database definition

    Raises
    ------
    ValueError
        If the table definitions are not valid
    """
    # Get the SQL dialect
    if (dialect := table_definitions.get("type")) is None:
        raise ValueError("SQL dialect ('table_definitions' > 'type') not found " \
                         "in the table definitions")
    # convert the dialect to an SQLDialect enum
    dialect_str = dialect.unwrap().upper()
    try:
        sql_dialect = SQLDialect[dialect_str]
    except KeyError:
        sql_dialect = SQLDialect.OTHER

    if sql_dialect == SQLDialect.SQLITE:
        return _parse_sqlite_table_definitions(table_definitions)
    else:
        raise NotImplementedError(f"SQL dialect '{dialect_str}' not supported: " \
                                  f"choose from {', '.join(SQLDialect.__members__)}")

def _parse_sqlite_table_definitions(table_definitions:toml_items.Table) -> SQLiteDBDefinition:
    """Parse the SQLite table definitions in the TOML data

    Parameters
    ----------
    table_definitions : tomlkit.items.Table
        Table definitions
    """
    # Get the path to the SQLite database
    if (path := table_definitions.get("path")) is None:
        raise ValueError("Path to the SQLite database " \
                         "('table_definitions' > 'path') not found")
    path = path.unwrap()

    # Get the table structures
    if (_tables := table_definitions.get("tables")) is None:
        raise ValueError("Table structures ('table_definitions' > 'tables') not found")
    tables = _parse_table_structure(_tables, dialect=SQLDialect.SQLITE)

    return SQLiteDBDefinition(tables, path=path)

def _parse_table_structure(tables:toml_items.Array,
                           dialect:SQLDialect) -> list[TableStructure]:
    """Parse the table structures in the TOML data

    Parameters
    ----------
    tables : tomlkit.items.Array
        Table structures
    dialect : SQLDialect
        SQL dialect

    Returns
    -------
    list[TableStructure]
        List of table structures
    """
    table_structures = []
    for i, table in enumerate(tables):
        if not isinstance(table, toml_items.String):
            raise ValueError("Table structure (CREATE TABLE statement in " \
                             "'table_definitions' > 'tables') is not a string")
        if not (table_structure := parse_sql(table.unwrap(), dialect)):
            # If `table` does not contain a valid CREATE TABLE statement
            raise ValueError(f"The {i}-th table structure in 'table_definitions' > 'tables' " \
                             "is not a valid CREATE TABLE statement")
        table_structures.append(table_structure[0])

    return table_structures

#
# Parse data_link
#

def parse_data_link(data:toml_items.Table) -> DataLink:
    """Parse the data link in the TOML data

    Parameters
    ----------
    data : tomlkit.items.Table
        Data link

    Returns
    -------
    DataLink
        Data link
    """
    # Get the data sources (empty data source is allowed)
    if (sources := data.get("sources")) is None:
        sources = []
    else:
        sources = _parse_data_sources(sources)

    # Get the insertion profiles
    insertion_profiles = data.get("insertion_profile")
    if (insertion_profiles is None) or (not isinstance(insertion_profiles, toml_items.Table)):
        raise ValueError("Insertion profiles ('data_link' > 'insertion_profile') " \
                         "not found or is not a table")
    insertion_profiles = _parse_insertion_profiles(insertion_profiles)

    # Create the data link & validate the data sources
    dl = DataLink([], insertion_profiles)
    for source in sources:
        if dl.add_source(source) is False:
            raise ValueError(f"Data source '{source.name}' already exists in the data link")
    return dl

#
# Parse data_link.sources
#

_VALID_SOURCE_TYPES: Final = {"API"} | set(SQLDialect.__members__.keys())
"""Set of valid source types"""

def _parse_data_sources(sources:toml_items.AoT) -> list[DataSource]:
    """Parse the data sources in the TOML data

    Parameters
    ----------
    sources : tomlkit.items.AoT
        Data sources

    Returns
    -------
    list[DataSource]
        Data sources

    Raises
    ------
    ValueError
        If the data sources are not valid (except for empty data source)
    """
    data_sources = []
    for i, source in enumerate(sources):
        try:
            if (ds := parse_data_source(source)) is not None:
                data_sources.append(ds)
        except ValueError as e:
            raise ValueError(f"{e.args[0]} in the {i}-th data source" \
                             "('data_link' > 'sources')") from e

    return data_sources

def parse_data_source(source: toml_items.Table) -> Optional[DataSource]:
    """Parse a data source in the TOML data

    Parameters
    ----------
    source : tomlkit.items.Table
        Data source

    Returns
    -------
    Optional[DataSource]
        Data source object or None if the data source is empty

    Raises
    ------
    ValueError
        If the data source is not valid (except for empty data source)
    """
    if len(source.keys()) == 0:
        # Empty data source
        return None

    # Get the source name
    _source_name = source.get("name")
    if (_source_name is None) or (not isinstance(_source_name, toml_items.String)):
        raise ValueError("Name of the data source not found or is not a string")
    source_name = _source_name.unwrap()

    # Get the source type
    _source_type = source.get("type")
    if (_source_type is None) or (not isinstance(_source_type, toml_items.String)):
        raise ValueError("Source type of the data source not found or is not a string")
    source_type = _source_type.unwrap().upper()
    if source_type not in _VALID_SOURCE_TYPES:
        raise ValueError(f"Source type '{source_type}' not supported: " \
                         f"choose from {', '.join(_VALID_SOURCE_TYPES)}")

    # Parse the result format
    _result_format = source.get("result_format")
    if (_result_format is None) or (not isinstance(_result_format, toml_items.String)):
        raise ValueError("Result format of the data source not found or is not a string")
    result_format_str = _result_format.unwrap().upper().replace("-", "_")
    if result_format_str not in SourceResultFormat.__members__:
        raise ValueError(f"Result format '{result_format_str}' not supported: " \
                            f"choose from {', '.join(SourceResultFormat.__members__)}")
    result_format = SourceResultFormat[result_format_str]

    # Parse the results_key
    _results_key = source.get("results_key")
    if (_results_key is None) or (not isinstance(_results_key, toml_items.String)):
        results_key = DEFAULT_RESULTS_KEY
    else:
        results_key = _results_key.unwrap()

    if source_type == "API":
        return _parse_api_data_source(source, source_name, result_format, results_key)
    elif source_type == "SQLITE":
        return _parse_sqlite_data_source(source, source_name, result_format, results_key)
    else:
        raise NotImplementedError(f"Data source type '{source_type}' not implemented")

def _parse_api_data_source(
        source:toml_items.Table, source_name:str,
        result_format:SourceResultFormat, results_key:str
    ) -> APIDataSource:
    """Parse an API data source in the TOML data

    Parameters
    ----------
    source : tomlkit.items.Table
        API data source
    source_name : str
        Name of the data source
    result_format : SourceResultFormat
        Format of the result
    results_key : str
        Key name corresponding to the list of data in the JSON object
    """
    # Get the API endpoint
    _endpoint = source.get("endpoint")
    if (_endpoint is None) or (not isinstance(_endpoint, toml_items.String)):
        raise ValueError("API endpoint not found or is not a string " \
                         f"in the data source '{source_name}'")
    endpoint = _endpoint.unwrap()

    # Get the HTTP headers
    _headers = source.get("headers")
    if (_headers is None) or (not (isinstance(_headers, toml_items.Table) and
            isinstance(_headers, toml_items.InlineTable))):
        headers = {}
    else:
        headers = dict(_headers)

    # Get the URL parameters
    _params = source.get("params")
    if (_params is None) or (not (isinstance(_params, toml_items.Table) and
            isinstance(_params, toml_items.InlineTable))):
        params = {}
    else:
        params = dict(_params)

    return APIDataSource(source_name, result_format, results_key, endpoint, headers, params)

def _parse_sqlite_data_source(
        source:toml_items.Table, source_name:str,
        result_format:SourceResultFormat, results_key:str
    ) -> SQLiteDataSource:
    """Parse a SQLite data source in the TOML data

    Parameters
    ----------
    source : tomlkit.items.Table
        SQLite data source
    source_name : str
        Name of the data source
    result_format : SourceResultFormat
        Format of the result
    results_key : str
        Key name corresponding to the list of data in the JSON objects
    """
    # Get the path to the SQLite database
    _path = source.get("path")
    if (_path is None) or (not isinstance(_path, toml_items.String)):
        raise ValueError("Path to the SQLite database not found or is not a string "\
                         f"in the data source '{source_name}'")
    path = _path.unwrap()

    # Get the SQL query
    _query = source.get("query")
    if (_query is None) or (not isinstance(_query, toml_items.String)):
        raise ValueError("SQL query not found or is not a string" \
                         f"in the data source '{source_name}'")
    query = _query.unwrap()

    return SQLiteDataSource(source_name, result_format, results_key, path=path, query=query)

#
# Parse data_link.insertion_profile
#

def _parse_insertion_profiles(profile:toml_items.Table) -> dict[str, InsertionProfile]:
    """Parse the insertion profiles in the TOML data

    Parameters
    ----------
    profile : tomlkit.items.Table
        Insertion profiles

    Returns
    -------
    dict[str, dict[str, str]]
        Insertion profiles
    """
    insertion_profiles:dict[str, InsertionProfile] = {}
    for table_name, profile in profile.items():
        if not isinstance(profile, toml_items.Table):
            raise ValueError(f"Insertion profile for table '{table_name}' is not a table")

        # Get the SQL query
        _query = profile.get("query")
        if (_query is None) or (not isinstance(_query, toml_items.String)):
            raise ValueError("SQL query not found or is not a string in the insertion profile " \
                             f"for table '{table_name}'")
        query = _query.unwrap()

        # Get the source(s)
        sources : list[Source] = []
        for s, regex in [("source", False), ("regex_source", True)]:
            _source = profile.get(s)
            if _source is None:
                continue
            if isinstance(_source, toml_items.String):
                sources.append(Source(name=_source.unwrap(), regex=regex))
            elif isinstance(_source, toml_items.Array):
                for i, s in enumerate(_source):
                    if not isinstance(s, toml_items.String):
                        raise ValueError(f"The {i}-th {s} is not a string " \
                                        f"in the insertion profile for table '{table_name}'")
                    sources.append(Source(name=s.unwrap(), regex=regex))
            else:
                raise ValueError(f"{s} is not a string or an array of strings " \
                                f"in the insertion profile for table '{table_name}'")
        if len(sources) == 0:
            raise ValueError("Source not found in the insertion profile " \
                             f"for table '{table_name}'")

        # Determine whether Positional or Named Parameter is used
        is_positional = "positional_parameters" in profile
        is_named = "named_parameters" in profile
        if is_positional and is_named:
            raise ValueError(f"Insertion profile for table '{table_name}' " \
                             "cannot have both positional and named parameters")
        elif not (is_positional or is_named):
            raise ValueError(f"Insertion profile for table '{table_name}' " \
                             "must have either positional or named parameters")

        # Parse the insertion profile
        if is_positional:
            insertion_profiles[table_name] = _parse_positional_insertion_profile(
                profile, query, sources, table_name
            )
        else:
            insertion_profiles[table_name] = _parse_named_insertion_profile(
                profile, query, sources, table_name
            )

    return insertion_profiles

def _parse_positional_insertion_profile(
        profile:toml_items.Table,
        query:str,
        sources:list[Source],
        table_name:str
    ) -> PositionalInsertionProfile:
    """Parse a positional insertion profile in the TOML data

    Parameters
    ----------
    profile : tomlkit.items.Table
        Positional insertion profile
    query : str
        SQL query to insert data into the table
    sources : list[Source]
        Source of the data
    table_name : str
        Name of the table

    Returns
    -------
    PositionalInsertionProfile
        Positional insertion profile
    """
    # Get the positional parameters
    _parameters = profile.get("positional_parameters")
    if (_parameters is None) or (not isinstance(_parameters, toml_items.Array)):
        raise ValueError("Positional parameters not found or is not an array " \
                         f"in the insertion profile for table '{table_name}'")
    # Parse the positional parameters
    parameters:dict[str, list[Union[str, int]]] = {}
    for i, parameter in enumerate(_parameters):
        if not isinstance(parameter, toml_items.Array):
            raise ValueError(f"The {i}-th positional parameter is not an array " \
                             f"in the insertion profile for table '{table_name}'")
        parameters[str(i)] = list(parameter)

    # Get the parameter conversion method
    _conversion_method = profile.get("conversion_method")
    conversion_method:dict[str, ParameterConversionMethod] = {}
    if _conversion_method is None:
        pass
    elif not isinstance(_conversion_method, toml_items.Array):
        raise ValueError("Parameter conversion method not found or is not an array " \
                         f"in the insertion profile for table '{table_name}'")
    elif len(_conversion_method) % 2 != 0:
        raise ValueError("Parameter conversion method is not a list of pairs " \
                         f"in the insertion profile for table '{table_name}'")
    else:
        # Parse the parameter conversion method
        for i in range(0, len(_conversion_method), 2):
            index = _conversion_method[i]
            if (not isinstance(index, toml_items.Integer)) or (not 0 <= index < len(parameters)):
                raise ValueError(f"Invalid index '{index}' in the conversion method " \
                                f"in the insertion profile for table '{table_name}'")
            method = _conversion_method[i+1]
            if (not isinstance(method, toml_items.String)) or \
            ((m_str:=method.unwrap().upper().replace("-", "_"))
                    not in ParameterConversionMethod.__members__):
                raise ValueError(f"Invalid conversion method '{method}' " \
                                f"in the insertion profile for table '{table_name}'")
            conversion_method[str(index)] = ParameterConversionMethod[m_str]

    return PositionalInsertionProfile(
        query, sources=sources,
        parameters=parameters, conversion_method=conversion_method
    )

def _parse_named_insertion_profile(
        profile:toml_items.Table,
        query:str,
        sources:list[Source],
        table_name:str
    ) -> NamedInsertionProfile:
    """Parse a named insertion profile in the TOML data

    Parameters
    ----------
    profile : tomlkit.items.Table
        Named insertion profile
    query : str
        SQL query to insert data into the table
    sources : list[Source]
        Source of the data
    table_name : str
        Name of the table

    Returns
    -------
    NamedInsertionProfile
        Named insertion profile
    """
    # Get the named parameters
    _parameters = profile.get("named_parameters")
    if (_parameters is None) or (not isinstance(_parameters, toml_items.Array)):
        raise ValueError("Named parameters not found or is not an array " \
                         f"in the insertion profile for table '{table_name}'")
    # Parse the named parameters
    parameters:dict[str, list[Union[str, int]]] = {}
    for i in range(0, len(_parameters), 2):
        key = _parameters[i]
        if not isinstance(key, toml_items.String):
            raise ValueError(f"The key ({i}-th value) of a named parameter is not a string " \
                             f"in the insertion profile for table '{table_name}'")
        parameter = _parameters[i+1]
        if not isinstance(parameter, toml_items.Array):
            raise ValueError(f"The named parameter for '{key}' is not an array " \
                             f"in the insertion profile for table '{table_name}'")
        parameters[key.unwrap()] = list(parameter)

    # Get the parameter conversion method
    _conversion_method = profile.get("conversion_method")
    conversion_method: dict[str, ParameterConversionMethod] = {}
    if _conversion_method is None:
        pass
    elif not isinstance(_conversion_method, toml_items.Array):
        raise ValueError("Parameter conversion method not found or is not an array " \
                         f"in the insertion profile for table '{table_name}'")
    elif len(_conversion_method) % 2 != 0:
        raise ValueError("Parameter conversion method is not a list of pairs " \
                         f"in the insertion profile for table '{table_name}'")
    else:
        # Parse the parameter conversion method
        for i in range(0, len(_conversion_method), 2):
            key = _conversion_method[i]
            if (not isinstance(key, toml_items.String)) or (key.unwrap() not in parameters):
                raise ValueError(f"Invalid key '{key}' in the conversion method " \
                                f"in the insertion profile for table '{table_name}'")
            method = _conversion_method[i+1]
            if (not isinstance(method, toml_items.String)) or \
            ((m_str:=method.unwrap().upper().replace("-", "_"))
                    not in ParameterConversionMethod.__members__):
                raise ValueError(f"Invalid conversion method '{method}' " \
                                f"in the insertion profile for table '{table_name}'")
            conversion_method[key.unwrap()] = ParameterConversionMethod[m_str]

    return NamedInsertionProfile(
        query, sources=sources,
        parameters=parameters, conversion_method=conversion_method
    )
