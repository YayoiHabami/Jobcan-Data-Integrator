"""
This module provides functions to update and get `modify_logs` table.

Functions
---------
- `update_modify_logs`: Update `modify_logs` table
- `retrieve_modify_logs`: Retrieve `modify_logs` data from the database

Target
------
- `/v1/requests/{request_id}` API (GET)
  - `detail` -> `modify_logs`
"""
import json
import sqlite3
from typing import Union



def _update_modify_log_detail_specifics(
        cursor:sqlite3.Cursor,
        modify_log_specifics:Union[list[dict], dict],
        mld_id:int) -> None:
    """Update 'modify_log_detail_specifics' table.

    Args:
        cursor: SQLite3 cursor object
        modify_log_specifics: 'detail'->'modify_logs'->'detail'->'specifics' element of the request
        mld_id: Modify log ID
    """
    if isinstance(modify_log_specifics, dict):
        modify_log_specifics = [modify_log_specifics]

    for i, mls_i in enumerate(modify_log_specifics):
        cursor.execute("""
        INSERT INTO modify_log_detail_specifics (modify_log_detail_id, status, difference, specific_index)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(modify_log_detail_id, specific_index) DO UPDATE SET
            status = excluded.status,
            difference = excluded.difference
        """, (mld_id, mls_i["status"], mls_i["difference"], i))


def update_modify_logs(
        cursor:sqlite3.Cursor,
        modify_logs:Union[list[dict],None],
        request_id:str) -> None:
    """Update 'modify_logs' table.

    Args:
        cursor: SQLite3 cursor object
        modify_logs: List of modify log data
        request_id: Request ID
    """
    if modify_logs is None:
        return

    for i, ml_i in enumerate(modify_logs):
        cursor.execute("""
        INSERT INTO modify_logs (request_id, date, user_name, log_index)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(request_id, log_index) DO UPDATE SET
            date = excluded.date,
            user_name = excluded.user_name
        """, (request_id, ml_i["date"], ml_i["user_name"], i))
        # get the last inserted row id
        cursor.execute(
            "SELECT id FROM modify_logs WHERE request_id = ? AND log_index = ?",
            (request_id, i)
        )
        ml_i_id = cursor.fetchone()[0]

        # update "modify_log_details" table
        for j, mld_i in enumerate(ml_i["detail"]):
            cursor.execute("""
            INSERT INTO modify_log_details (modify_log_id, title, old_value, new_value, log_type, log_detail_index)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(modify_log_id, log_detail_index) DO UPDATE SET
                title = excluded.title,
                old_value = excluded.old_value,
                new_value = excluded.new_value,
                log_type = excluded.log_type
            """, (ml_i_id,
                  mld_i["title"],
                  mld_i["old"], mld_i["new"], mld_i["log_type"],
                  j))
            # get the last inserted row id
            cursor.execute(
                """SELECT id FROM modify_log_details
                   WHERE modify_log_id = ? AND log_detail_index = ?""",
                (ml_i_id, j))
            mld_i_id = cursor.fetchone()[0]

            # update "modify_log_specifics" table
            if mld_i["specifics"] is not None:
                _update_modify_log_detail_specifics(cursor, mld_i["specifics"], mld_i_id)

        # TODO: remove items from 'modify_log_details' table if the number of items is less than before

    # TODO: remove items from 'modify_logs' table if the number of items is less than before


def retrieve_modify_logs(
        cursor:sqlite3.Cursor,
        request_id:str) -> dict:
    """Retrieve 'modify_logs' data from the database.

    Args:
        cursor: SQLite3 cursor object
        request_id: Request ID

    Returns:
        Modify log data.
        The data structure is similar to the `detail`->`modify_logs` element
        in the response of the `/v1/requests/{request_id}` API.
    """
    cursor.execute("""
    SELECT JSON_GROUP_ARRAY(
        JSON_OBJECT(
            'date', ml.date,
            'user_name', ml.user_name,
            'detail', (
                SELECT JSON_GROUP_ARRAY(
                    JSON_OBJECT(
                        'title', mld.title,
                        'old', mld.old_value,
                        'new', mld.new_value,
                        'log_type', mld.log_type,
                        'specifics', (
                            SELECT JSON_GROUP_ARRAY(
                                JSON_OBJECT(
                                    'status', mls.status,
                                    'difference', mls.difference
                                )
                            )
                            FROM modify_log_detail_specifics mls
                            WHERE mls.modify_log_detail_id = mld.id
                            ORDER BY mls.specific_index
                        )
                    )
                )
                FROM modify_log_details mld
                WHERE mld.modify_log_id = ml.id
                ORDER BY mld.log_detail_index
            )
        )
    )
    FROM modify_logs ml
    WHERE ml.request_id = ?;
    """, (request_id,))
    result = cursor.fetchone()
    if result is None:
        return None

    return json.loads(result[0])
