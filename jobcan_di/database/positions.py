"""
This module provides functions to create, update, and read data
from the response of the `/v1/positions/` API.

The data is stored in a SQLite database and is retrieved
as a dict object (like the API response).

Functions
---------
- `create_tables`: Create `positions` table in the database
- `update`: Insert or update `positions` data in the database
- `retrieve`: Retrieve `positions` data from the database
"""
import sqlite3
from typing import Optional



def create_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist.

    Note:
        This function creates the following tables:
            - positions
    """
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS positions (
        position_code TEXT PRIMARY KEY,
        position_name TEXT,
        description TEXT
    )
    """)

    conn.commit()


def update(conn: sqlite3.Connection,
           data: dict):
    """Update data in the positions table.

    Args:
        conn: SQLite3 connection object
        data: Position data to be inserted or updated.
              The data should be the 'results' element of the result from the '/v1/positions/' API.
    """
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO positions (position_code, position_name, description)
    VALUES (?, ?, ?)
    """, (data["position_code"], data["position_name"], data["description"]))

    conn.commit()


def retrieve(conn: sqlite3.Connection,
             position_code: Optional[list[str]] = None):
    """Retrieve `positions` data from the positions table.

    Args:
        conn: SQLite3 connection object
        position_code: list of str
            List of position codes to be read from the table.
            If empty or None, all data will be read.

    Returns:
        list of dict: List of position data.
    """
    if position_code is None:
        position_code = []

    cursor = conn.cursor()

    where_statement = ""
    if position_code:
        where_statement = f"WHERE position_code IN ({','.join(['?']*len(position_code))})"

    # TODO: Use JSON_ARRAY() instead of for loop
    cursor.execute(f"""
    SELECT * FROM positions
    {where_statement}
    """, position_code)

    results = []

    for row in cursor.fetchall():
        results.append({
            "position_code": row[0],
            "position_name": row[1],
            "description": row[2]
        })

    return results
