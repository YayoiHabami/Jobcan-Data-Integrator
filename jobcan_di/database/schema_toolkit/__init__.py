"""Module for analyzing SQL query strings and performing comparison verification
with the actual database.

Classes
-------
- Enum for SQL dialects
  - `SQLDialect`: Supported SQL dialects
- Class for representing database schema
  - `ColumnStructure`: Column structure
  - `TableStructure`: Table structure

Functions
---------
- SQL query analysis functions
  - `parse_sql`: Parse SQL query strings. Currently only supports CREATE TABLE statements.
- Table structure verification functions
  - `check_table_structure`: Check if the table structure matches the expected structure.
"""
from ._core import ColumnStructure, TableStructure, SQLDialect

from .sql_parser import parse_sql
from .validator import check_table_structure
