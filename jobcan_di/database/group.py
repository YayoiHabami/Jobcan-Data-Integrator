"""
This module provides functions to store and retrieve the response
of the `/v1/group/` API.

The data is stored in a SQLite database and is retrieved
as a dict object (like the API response).

Functions
---------
- `create_tables`: Create `groups` table in the database
- `update`: Insert or update `groups` data in the database
- `retrieve`: Retrieve `groups` data from the database
"""
import sqlite3
from typing import Optional



def create_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist.

    Note:
        This function creates the following tables:
            - groups
    """
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        group_code TEXT PRIMARY KEY,
        group_name TEXT,
        parent_group_code TEXT,
        description TEXT,
        UNIQUE (group_code, group_name)
    )
    """)

    conn.commit()


def update(conn: sqlite3.Connection,
           data: dict):
    """Update data in the groups table.

    Args:
        conn: SQLite3 connection object
        data: Group data to be inserted or updated.
              The data should be the 'results' element of the result from the '/v1/group/' API.
    """
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO groups (group_code, group_name, parent_group_code, description)
    SELECT ?, ?, ?, ?
    WHERE NOT EXISTS (
        SELECT 1 FROM groups
        WHERE group_name = ? AND
            (
                (? IS NULL AND group_code IS NULL) OR
                (? IS NOT NULL AND group_code = ?)
            )
    );
    """, (data['group_code'], data['group_name'], data['parent_group_code'], data['description'],
          data['group_name'], data['group_code'], data['group_code'], data['group_code']))

    conn.commit()


def retrieve(conn: sqlite3.Connection,
             group_code:Optional[list[str]] = None):
    """Read data from the groups table.

    Args:
        conn: SQLite3 connection object
        group_code: list of str
            List of group codes to be read from the table.
            If empty or None, all data will be read.

    Returns:
        list of dict: Group data
    """
    # If group_code is not specified, read all data
    if not group_code:
        group_code = []

    cursor = conn.cursor()

    where_statement = ''
    if group_code:
        where_statement = f"WHERE group_code IN ({','.join(['?']*len(group_code))})"

    # TODO Use JSON_ARRAY() to return the parent_group_code as a JSON array
    cursor.execute(f"""
    SELECT * FROM groups {where_statement}
    """, group_code)

    results = []

    for row in cursor.fetchall():
        results.append({
            'group_code': row[0],
            'group_name': row[1],
            'parent_group_code': row[2],
            'description': row[3]
        })

    return results
