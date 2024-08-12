"""
This module provides functions to store and retrieve the response
of the `/v1/forms/` API.

The data is stored in a SQLite database and is retrieved
as a dict object (like the API response).

Functions
---------
- `create_tables`: Create `forms` table in the database
- `update`: Insert or update `forms` data in the database
- `retrieve`: Retrieve `forms` data from the database
- `retrieve_form_ids`: Retrieve all form ids from the database
"""
import sqlite3
from typing import Optional



def create_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist.

    Note:
        This function creates the following tables:
            - forms
    """
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS forms (
        id INTEGER PRIMARY KEY,
        category TEXT,
        form_type TEXT,
        settlement_type TEXT,
        name TEXT,
        view_type TEXT,
        description TEXT
    )
    """)

    conn.commit()


def update(conn: sqlite3.Connection,
           data: dict):
    """Update `forms` data in the forms table.

    Args:
        conn: SQLite3 connection object
        data: Form data to be inserted or updated.
              The data should be the 'results' element of the result from the '/v1/forms/' API.
    """
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO forms (id, category, form_type, settlement_type, name, view_type, description)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["id"], data["category"], data["form_type"], data["settlement_type"],
        data["name"], data["view_type"], data["description"]
    ))

    conn.commit()


def retrieve(conn: sqlite3.Connection,
             form_id: Optional[list[int]] = None):
    """Retrieve `forms` data from the forms table.

    Args:
        conn: SQLite3 connection object
        form_id: list of int
            List of form ids to be read from the table.
            If empty, all data will be read.

    Returns:
        list of dict: List of form data.
    """
    if form_id is None:
        form_id = []

    cursor = conn.cursor()

    where_statement = ""
    if form_id:
        where_statement = f"WHERE id IN ({','.join(['?']*len(form_id))})"

    cursor.execute(f"""
    SELECT * FROM forms
    {where_statement}
    """, form_id)

    results = []

    for row in cursor.fetchall():
        results.append({
            "id": row[0],
            "category": row[1],
            "form_type": row[2],
            "settlement_type": row[3],
            "name": row[4],
            "view_type": row[5],
            "description": row[6]
        })

    return results


def retrieve_form_ids(conn: sqlite3.Connection) -> list[int]:
    """Retrieve all form ids from the forms table.

    Args:
        conn: SQLite3 connection object

    Returns:
        list of int: List of form ids.
    """
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id FROM forms
    """)

    return [int(row[0]) for row in cursor.fetchall()]
