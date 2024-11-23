"""
Core data structures for schema toolkit.

This module defines the core data structures used in the schema toolkit.

Classes
-------
- `SQLDialect`: Supported SQL dialects
- `ColumnStructure`: Column structure
- `TableStructure`: Table structure
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Any



class SQLDialect(Enum):
    """Supported SQL dialects."""
    SQLITE = auto()
    OTHER = auto()

@dataclass
class ColumnStructure:
    """Column structure

    Attributes:
    -----------
    name : str
        Column name
    ttype : str
        Column type (e.g. INTEGER, TEXT)
    not_null : bool
        True if the column is NOT NULL
    autoincrement : bool
        True if the column is AUTOINCREMENT
    default : Any
        Default value of the column
    foreign_key : Optional[tuple[str, str]]
        (table_name, column_name) of the foreign key reference
    """
    name: str
    """Column name"""
    ttype: str
    """Column type"""
    not_null: bool = False
    """True if the column is NOT NULL"""
    autoincrement: bool = False
    """True if the column is AUTOINCREMENT"""
    default: Optional[Any] = None
    """Default value of the column"""
    foreign_key: Optional[tuple[str, str]] = None
    """(table_name, column_name) of the foreign key reference"""

@dataclass
class TableStructure:
    """Table structure

    Attributes:
    -----------
    name : str
        Table name
    columns : list[ColumnStructure]
        List of column structures
    unique_keys : list[list[str]]
        List of unique constraints
        - e.g. [['column1', 'column2'], ['column3']]
    primary_keys : list[str]
        List of primary key constraints
        - e.g. ['column1', 'column2']
    raw_sql : Optional[str]
        Raw SQL statement for creating the table

    Examples
    --------
    ```sql
    CREATE TABLE IF NOT EXISTS projects (
        project_code TEXT PRIMARY KEY,
        project_name TEXT,
        UNIQUE (project_code, project_name)
    ```

    is represented as:

    ```python
    TableStructure(
        name='projects',
        columns=[
            ColumnStructure(name='project_code', ttype='TEXT', not_null=True),
            ColumnStructure(name='project_name', ttype='TEXT')
        ],
        primary_keys=['project_code'],
        unique_keys=[['project_code', 'project_name']]
    )
    ```
    """
    name: str
    """Table name"""
    columns: list[ColumnStructure]
    """List of column structures"""
    unique_keys: list[list[str]] = field(default_factory=list)
    """List of unique constraints
    - e.g. [['column1', 'column2'], ['column3']]"""
    primary_keys: list[str] = field(default_factory=list)
    """List of primary key constraints
    - e.g. ['column1', 'column2']"""
    raw_sql: str = ""
    """Raw SQL statement for creating the table"""
