"""
This module provides functions to update and get 'viewers' table.

Functions
---------
- `update_viewers`: Update 'viewers' table
- `retrieve_viewers`: Retrieve 'viewers' data from the database

Target
------
- `/v1/requests/{request_id}` API (GET)
  - `detail` -> `viewers`
"""
import json
import sqlite3
from typing import Union



def update_viewers(
        cursor:sqlite3.Cursor,
        viewers:Union[list[dict],None],
        request_id:str) -> None:
    """Update 'viewers' table.

    Args:
        cursor: SQLite3 cursor object
        viewers: List of viewer data
        request_id: Request ID
    """
    if viewers is None:
        return

    for i, v_i in enumerate(viewers):
        cursor.execute("""
        INSERT INTO viewers (request_id, user_name, status, group_name, position, viewer_index)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(request_id, viewer_index) DO UPDATE SET
            user_name = excluded.user_name,
            status = excluded.status,
            group_name = excluded.group_name,
            position = excluded.position
        """, (
            request_id,
            v_i["user_name"], v_i["status"], v_i["group"], v_i["position"],
            i
        ))

    # TODO: remove items from 'viewers' table if the number of items is less than before


def retrieve_viewers(
        cursor:sqlite3.Cursor,
        request_id:str
    ) -> dict:
    """Retrieve 'viewers' data from the database.

    Args:
        cursor: SQLite3 cursor object
        request_id: Request ID

    Returns:
        Viewer data.
        The data structure is as follows:

        ```python
        [
            {
                "user_name": "user_name",
                "status": "status",
                "group_name": "group_name",
                "position": "position"
            },
            ...
        ]
        ```
    """
    cursor.execute("""
    SELECT JSON_GROUP_ARRAY(
        JSON_OBJECT(
            'user_name', v.user_name,
            'status', v.status,
            'group_name', v.group_name,
            'position', v.position
        )
    )
    FROM viewers v
    WHERE v.request_id = ?;
    """, (request_id,))

    result = cursor.fetchone()
    if result is None:
        return None

    return json.loads(result[0])
