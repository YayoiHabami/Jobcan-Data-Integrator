"""Module for validating table structure against the expected structure.

Functions
---------
- `check_table_structure`: Check if the table structure matches the expected structure.
"""
import sqlite3
from typing import Optional

from ._core import TableStructure, SQLDialect


def _validate_table_info(table_info: list[tuple],
                         table_structure: TableStructure) -> Optional[str]:
    """Validate table information against the expected table structure.

    Args
    ----
    table_info : list[tuple]
        Table information from the PRAGMA table_info() query
    table_structure : TableStructure
        Expected table structure

    Returns
    -------
    str: Error message if the table information does not match the expected structure
         None if the table information matches the expected structure
    """
    for column_structure in table_structure.columns:
        match = next((c for c in table_info if c[1] == column_structure.name), None)
        if not match:
            return f"Column '{column_structure.name}' does not exist " \
                   f"in table '{table_structure.name}'."

        _, name, ctype, notnull, default_value, pk = match

        # Check column type
        if ctype.upper() != column_structure.ttype.upper():
            return f"Column '{name}' in table '{table_structure.name}' type mismatch: " \
                   f"Expected {column_structure.ttype}, Found {ctype}."

        # Check NOT NULL constraint
        if bool(notnull) != column_structure.not_null:
            return f"Column '{name}' in table '{table_structure.name}' " \
                   "NOT NULL constraint mismatch."

        # Check DEFAULT value
        if ((default_value or column_structure.default)
            and (default_value != column_structure.default)):
            return f"Column '{name}' in table '{table_structure.name}' DEFAULT value mismatch: " \
                   f"Expected {column_structure.default}, Found {default_value}."

        # Check AUTOINCREMENT constraint (only relevant for INTEGER PRIMARY KEY AUTOINCREMENT)
        if "INTEGER" in ctype.upper() and column_structure.autoincrement and pk == 0:
            # No direct SQLite PRAGMA or table info to check AUTOINCREMENT,
            # but if specified, should be part of primary key
            return f"Column '{name}' in table '{table_structure.name}' " \
                   "AUTOINCREMENT constraint mismatch."

    # Check for unexpected columns
    actual_columns = [col[1] for col in table_info]
    expected_columns = [col.name for col in table_structure.columns]
    if set(actual_columns) != set(expected_columns):
        unexpected_column_names = [f"'{x}'" for x in (set(actual_columns) - set(expected_columns))]
        return f"Unexpected column(s): {', '.join(unexpected_column_names)}."

    # Check PRIMARY KEY constraint
    actual_primary_keys = [col[1] for col in table_info if col[-1] > 0]
    if set(actual_primary_keys) != set(table_structure.primary_keys):
        expected = ", ".join(f"'{pk}'" for pk in table_structure.primary_keys)
        expected = expected or "None"
        actual = ", ".join(f"'{pk}'" for pk in actual_primary_keys)
        actual = actual or "None"
        return "Primary key mismatch: " \
               f"Expected: {expected}, Found: {actual}."

    return None

def _validate_index_list(cursor: sqlite3.Cursor,
                         index_list: list[tuple],
                         table_structure: TableStructure) -> Optional[str]:
    """Validate index information against the expected table structure.

    Args
    ----
    cursor : sqlite3.Cursor
        SQLite3 cursor object
    index_list : list[tuple]
        Index information from the PRAGMA index_list() query
    table_structure : TableStructure
        Expected table structure

    Returns
    -------
    str: Error message if the index information does not match the expected structure
         None if the index information matches the expected structure
    """
    # Check UNIQUE constraints
    def get_unique_columns(index_name):
        cursor.execute(f"PRAGMA index_info({index_name})")
        return [info[2] for info in cursor.fetchall()]

    actual_unique_keys = []
    for index in index_list:
        if index[2] and 'u' in index[3]:  # assuming 'u' indicates a UNIQUE constraint
            unique_columns = get_unique_columns(index[1])
            actual_unique_keys.append(set(unique_columns))

    if not all(set(uq) in actual_unique_keys for uq in table_structure.unique_keys):
        expected = ", ".join(str(list(uq)) for uq in table_structure.unique_keys)
        actual = ", ".join(str(list(uq)) for uq in actual_unique_keys)
        return f"Unique keys mismatch or not present in table '{table_structure.name}': " \
               f"Expected {expected}, Found: {actual}."

    return None

def _validate_foreign_keys(cursor: sqlite3.Cursor,
                           table_structure: TableStructure,
                           dialect: SQLDialect
                           ) -> Optional[str]:
    """Validate foreign key information against the expected table structure.

    Args
    ----
    cursor : sqlite3.Cursor
        SQLite3 cursor object
    table_structure : TableStructure
        Expected table structure
    dialect : SQLDialect
        SQL dialect of the DBMS

    Returns
    -------
    str: Error message if the foreign key information does not match the expected structure
         None if the foreign key information matches the expected structure
    """
    # Check if foreign keys are enabled
    expected = any(col.foreign_key for col in table_structure.columns)
    cursor.execute("PRAGMA foreign_keys")
    if ((not (a:=cursor.fetchone()[0])) and (a != expected)
        and (dialect != SQLDialect.SQLITE)):
        # If DBMS is SQLite, foreign keys are not enabled by default
        return "Foreign keys are not enabled."

    # Check foreign key constraints
    cursor.execute(f"""
    WITH fk_info AS (
        SELECT "from", "table", "to"
        FROM pragma_foreign_key_list('{table_structure.name}')
    )
    SELECT
        ti.name AS column_name,
        fk."table" AS referenced_table,
        fk."to" AS referenced_column
    FROM pragma_table_info('{table_structure.name}') ti
    LEFT JOIN fk_info fk ON ti.name = fk."from"
    WHERE NOT (fk."table" IS NULL AND fk."to" IS NULL)
    ORDER BY ti.cid;
    """)
    fk_info = cursor.fetchall()

    for column_structure in table_structure.columns:
        match = next((fk for fk in fk_info if fk[0] == column_structure.name), None)
        if not match:
            if column_structure.foreign_key:
                return f"Column '{column_structure.name}' in table '{table_structure.name}' " \
                       "FOREIGN KEY constraint mismatch: " \
                       f"Expected {column_structure.foreign_key}, Found None."
        else:
            _, referenced_table, referenced_column = match
            if (referenced_table, referenced_column) != column_structure.foreign_key:
                return f"Column '{column_structure.name}' in table '{table_structure.name}' " \
                       "FOREIGN KEY constraint mismatch: " \
                       f"Expected {column_structure.foreign_key}, " \
                       f"Found ({referenced_table}, {referenced_column})."

def check_table_structure(conn: sqlite3.Connection,
                          table_structure: TableStructure,
                          dialect: SQLDialect = SQLDialect.SQLITE
                          ) -> Optional[str]:
    """Check if the table structure matches the expected structure.

    Args
    ----
    conn : sqlite3.Connection
        SQLite3 connection object
    table_structure : TableStructure
        Expected table structure
    dialect : SQLDialect, optional
        SQL dialect of the DBMS, by default SQLDialect.SQLite

    Returns
    -------
    str : Error message if the table structure does not match the expected structure
          None if the table structure matches the expected structure
    """
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master " \
                   f"WHERE type='table' AND name='{table_structure.name}'")
    if not cursor.fetchone():
        return f"Table '{table_structure.name}' does not exist."

    # Get table columns information
    cursor.execute(f"PRAGMA table_info({table_structure.name})")
    table_info = cursor.fetchall()

    # Validate table_info against table_structure
    if (err := _validate_table_info(table_info, table_structure)):
        return err

    # Get index information
    cursor.execute(f"PRAGMA index_list({table_structure.name})")
    index_list = cursor.fetchall()

    # Validate index_list against table_structure
    if (err := _validate_index_list(cursor, index_list, table_structure)):
        return err

    # Validate foreign keys
    if (err := _validate_foreign_keys(cursor, table_structure, dialect)):
        return err

    return None
