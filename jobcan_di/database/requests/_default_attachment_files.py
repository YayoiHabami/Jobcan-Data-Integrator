"""
This module provides functions to handle `default_attachment_files` data.

Functions
---------
- `update_default_attachment_files`: Update 'files' and 'file_associations' tables
    for default attachment files
- `retrieve_default_attachment_files`: Retrieve 'default_attachment_files' data
    from the database

Target
------
- `/v1/requests/{request_id}` API (GET)
  - `detail` -> `default_attachment_files`
"""
import json
import sqlite3
from typing import Union

from ._data_class import FileDataList



def update_default_attachment_files(
        daf:Union[list[dict],None],
        f_list:FileDataList) -> None:
    """Update 'files' and 'file_associations' tables for default attachment files.

    Args:
        daf: 'detail'->'default_attachment_files' element of the request
        f_list: FileDataList object
    """
    if daf is None:
        return

    for f_i in daf:
        f_list.add_file(f_i, 5, None)


def retrieve_default_attachment_files(
        cursor:sqlite3.Cursor,
        request_id:str) -> dict:
    """Retrieve 'default_attachment_files' data from the database.

    Args:
        cursor: SQLite3 cursor object
        request_id: Request ID

    Returns:
        Default attachment files data.
        The data structure is similar to the `detail`->`default_attachment_files` element
        in the response of the `/v1/requests/{request_id}` API.
    """
    # Use recursive Common Table Expression (CTE) to get JSON_GROUP_ARRAY
    # with repeated file information recursively for 'default_attachment'
    # in the 'file_association' table.
    # e.g. A file with file_id 12345 and a value of 3 in file_association.default_attachment
    #      appears 3 times in the list of "default_attachment_files".
    cursor.execute("""
    WITH RECURSIVE repeated_files AS (
        SELECT
            f.id,
            f.name,
            f.type,
            a.default_attachment - 1 AS remaining_attachments
        FROM file_associations a
        JOIN files f ON a.file_id = f.id
        WHERE a.request_id = ? AND a.default_attachment > 0
        UNION ALL
        SELECT
            rf.id,
            rf.name,
            rf.type,
            rf.remaining_attachments - 1
        FROM repeated_files rf
        WHERE rf.remaining_attachments > 0
    )
    SELECT JSON_GROUP_ARRAY(
        JSON_OBJECT(
            'id', rf.id,
            'name', rf.name,
            'type', rf.type
        )
    ) AS default_attachment_files
    FROM repeated_files rf
    ;""", (request_id,))

    result = cursor.fetchone()
    if result is None:
        return None

    return json.loads(result[0])
