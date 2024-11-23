"""
This module provides functions to store and retrieve the response
of the `/v1/project/` API.

The data is stored in a SQLite database and is retrieved
as a dict object (like the API response).

Functions
---------
- `create_tables`: Create `projects` table in the database
- `update`: Update the `projects` table with the API response
- `retrieve`: Retrieve project data from the `projects` table
"""
import json
import sqlite3
from typing import Optional



def create_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist.

    Note:
        This function creates the following tables:
            - projects
    """
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS projects (
        project_code TEXT PRIMARY KEY,
        project_name TEXT)
    """)

    conn.commit()

def update(conn: sqlite3.Connection,
           data: dict):
    """Update data in the projects table.

    Args:
        conn: SQLite3 connection object
        data: Project data to be inserted or updated.
              The data should be the 'results' element of the result from the '/v1/project/' API.
    """
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO projects (project_code, project_name)
    VALUES (?, ?)
    """, (data['project_code'], data['project_name']))

    conn.commit()

def retrieve(conn: sqlite3.Connection,
             project_code: Optional[list[str]] = None) -> list[dict]:
    """Retrieve project data from the database.

    Args:
        conn: SQLite3 connection object
        project_code: Project code(s) to retrieve data for
                      If None, all project data is retrieved

    Returns:
        dict: Project data
    """
    cursor = conn.cursor()

    query = """
    SELECT json_object(
        'project_code', project_code,
        'project_name', project_name
    ) AS project_json
    FROM projects
    """

    if project_code is None:
        cursor.execute(query)
    else:
        where_clause = f"WHERE project_code IN ({','.join(['?']*len(project_code))})"
        cursor.execute(query + where_clause,
                       project_code)

    return [json.loads(row[0]) for row in cursor.fetchall()]
