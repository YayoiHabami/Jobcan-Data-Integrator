"""
This module provides functions to update and get data in the 'approval_process' table.

Functions
---------
- `update_approval_process`: Update 'approval_process' table
- `retrieve_approval_process`: Retrieve 'approval_process' data from the database

Target
------
- `/v1/requests/{request_id}` API (GET)
  - `detail` -> `approval_process`
"""
import json
import sqlite3
from typing import Union

from ._data_class import CommentDataList, FileDataList



def _update_approval_route_modify_logs(
        cursor:sqlite3.Cursor,
        modify_logs:list[dict],
        ap_id:int) -> None:
    """Update 'approval_route_modify_logs' table.

    Args:
        cursor: SQLite3 cursor object
        modify_logs: 'detail'->'approval_process'->'approval_route_modify_logs' element
            of the request
        ap_id: Approval process ID
    """
    for i, modify_log in enumerate(modify_logs):
        cursor.execute("""
        INSERT INTO approval_route_modify_logs (approval_process_id, date, user_name, log_index)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(approval_process_id, log_index) DO UPDATE SET
            date = excluded.date,
            user_name = excluded.user_name
        """, (ap_id, modify_log["date"], modify_log["user_name"], i))

    # TODO: remove items from 'approval_route_modify_logs' table if the number of items is less than before


def _update_approval_step_approvers(
        cursor:sqlite3.Cursor,
        approvers:list[dict],
        as_id:int) -> None:
    """Update 'approvers' table.

    Args:
        cursor: SQLite3 cursor object
        approvers: 'approvers' element of the approval step
        as_id: Approval step ID
    """
    for i, a_i in enumerate(approvers):
        cursor.execute("""
        INSERT INTO approvers (approval_step_id, status, approved_date, approver_name,
                               proxy_approver_name, proxy_approver_code,
                               approver_index)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(approval_step_id, approver_index) DO UPDATE SET
            status = excluded.status,
            approved_date = excluded.approved_date,
            approver_name = excluded.approver_name,
            proxy_approver_name = excluded.proxy_approver_name,
            proxy_approver_code = excluded.proxy_approver_code
        """, (
            as_id, a_i["status"], a_i["approved_date"], a_i["approver_name"],
            a_i["proxy_approver_name"], a_i["proxy_approver_code"], i
        ))

    # TODO: remove items from 'approvers' table if the number of items is less than before


def _update_approval_steps(
        cursor:sqlite3.Cursor,
        steps:list[dict],
        ap_id:int,
        f_list:FileDataList,
        c_list:CommentDataList) -> None:
    """Update 'approval_steps' table.

    Args:
        cursor: SQLite3 cursor object
        steps: 'detail'->'approval_process'->'steps' element of the request
        ap_id: Approval process ID
        f_list: FileDataList object
        c_list: CommentDataList object
    """
    for i, as_i in enumerate(steps):
        cursor.execute("""
        INSERT INTO approval_steps (approval_process_id, name, condition, status, step_index)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(approval_process_id, step_index) DO UPDATE SET
            name = excluded.name,
            condition = excluded.condition,
            status = excluded.status
        """, (ap_id, as_i["name"], as_i["condition"], as_i["status"], i))
        # get the last inserted row id
        cursor.execute(
            "SELECT id FROM approval_steps WHERE approval_process_id = ? AND step_index = ?",
            (ap_id, i))
        as_i_id = cursor.fetchone()[0]

        # update "approvers" table
        if as_i["approvers"] is not None:
            _update_approval_step_approvers(cursor, as_i["approvers"], as_i_id)

        # update comments
        _comments = as_i["comments"] if as_i["comments"] is not None else []
        for c_i in _comments:
            c_list.add_comment(c_i, as_i_id, None)

        # add file data
        _files = as_i["files"] if as_i["files"] is not None else []
        for f_i in _files:
            f_list.add_file(f_i, 3, as_i_id)

    # TODO: remove items from 'approval_steps' table if the number of items is less than before


def _update_approval_after_completion(
        after_completion:dict,
        ap_id:int,
        f_list:FileDataList,
        c_list:CommentDataList) -> None:
    """Update elements in 'approval_after_completion'

    Args:
        after_completion: 'detail'->'approval_process'->'after_completion' element of the request
        ap_id: Approval process ID
        f_list: FileDataList object
        c_list: CommentDataList object
    """
    # add comments
    _comments = _cmt if (_cmt:=after_completion["comments"]) is not None else []
    for c_i in _comments:
        c_list.add_comment(c_i, None, ap_id)

    # add file data
    _files = _f if (_f:=after_completion["files"]) is not None else []
    for f_i in _files:
        f_list.add_file(f_i, 4, ap_id)


def update_approval_process(
        cursor:sqlite3.Cursor,
        ap:Union[dict,None],
        request_id:str,
        f_list:FileDataList) -> None:
    """Update 'approval_process' table.

    Args:
        cursor: SQLite3 cursor object
        ap: 'detail'->'approval_process' element of the request
        request_id: Request ID
        f_list: FileDataList object
    """
    if ap is None:
        return

    # comments
    c_list = CommentDataList()

    cursor.execute("""
    INSERT INTO approval_process (request_id, is_route_changed_by_applicant)
    VALUES (?, ?)
    ON CONFLICT(request_id) DO UPDATE SET
        is_route_changed_by_applicant = excluded.is_route_changed_by_applicant
    """, (request_id, ap["is_route_changed_by_applicant"]))
    # get the last inserted row id
    cursor.execute("SELECT id FROM approval_process WHERE request_id = ?", (request_id,))
    ap_id = cursor.fetchone()[0]

    # update "approval_route_modify_logs" table
    if ap["approval_route_modify_logs"] is not None:
        _update_approval_route_modify_logs(cursor, ap["approval_route_modify_logs"], ap_id)

    # update "approval_steps" table
    if ap["steps"] is not None:
        _update_approval_steps(cursor, ap["steps"], ap_id, f_list, c_list)

    # update "approval_after_completion" table
    if ap["after_completion"] is not None:
        _update_approval_after_completion(ap["after_completion"], ap_id, f_list, c_list)

    # update comments
    _update_comments(cursor, c_list)

# -> 'comments' and 'comment_associations'


def _update_comments(cursor:sqlite3.Cursor,
                     c_list:CommentDataList) -> None:
    """Update 'comments' and 'comment_associations' tables.

    Args:
        cursor: SQLite3 cursor object
        c_list: CommentDataList object
    """
    # update 'comment' table
    comment_ids = []
    for c_i in c_list.get_comment_data():
        # check if the record already exists
        cursor.execute("""SELECT id FROM comments
        WHERE user_name = ? AND date = ? AND (
            (text IS NULL AND ? IS NULL) OR text = ?
        );""", (c_i[0], c_i[1], c_i[2], c_i[2]))
        existing_id = cursor.fetchone()
        if existing_id is not None:
            cursor.execute("UPDATE comments SET deleted = ? WHERE id = ?",
                           (c_i[3], existing_id[0]))
            comment_ids.append(existing_id[0])
        else:
            cursor.execute(
                "INSERT INTO comments (user_name, date, text, deleted) VALUES (?, ?, ?, ?)",
                c_i
            )
            # get the last inserted row id
            cursor.execute("""SELECT id FROM comments
            WHERE user_name = ? AND date = ? AND (
                (text IS NULL AND ? IS NULL) OR text = ?
            );""", (c_i[0], c_i[1], c_i[2], c_i[2]))
            comment_ids.append(cursor.fetchone()[0])
    c_list.set_comment_ids(comment_ids)

    # update 'comment_associations' table
    cursor.executemany("""
    INSERT INTO comment_associations (comment_id, approval_step_id, approval_after_completion_id)
    VALUES (?, ?, ?)
    ON CONFLICT(comment_id) DO UPDATE SET
        approval_step_id = excluded.approval_step_id,
        approval_after_completion_id = excluded.approval_after_completion_id
    """, c_list.get_comment_association_data())

    # TODO: remove items from 'comment_associations' table if the number of items is less than before


def retrieve_approval_process(cursor:sqlite3.Cursor,
                              request_id:str) -> dict:
    """Retrieve 'approval_process' data from the database.

    Args:
        cursor: SQLite3 cursor object
        request_id: Request ID

    Returns:
        Approval process data.
        The data structure is similar to the `detail`->`approval_process` element
        in the response of the `/v1/requests/{request_id}` API.
    """
    cursor.execute("""
    SELECT JSON_OBJECT(
        'is_route_changed_by_applicant', CASE WHEN ap.is_route_changed_by_applicant=1 THEN json('true')
                                              WHEN ap.is_route_changed_by_applicant=0 THEN json('false')
                                              ELSE NULL END,
        'approval_route_modify_logs', (
            SELECT JSON_GROUP_ARRAY(
                JSON_OBJECT(
                    'date', arml.date,
                    'user_name', arml.user_name
                )
            )
            FROM approval_route_modify_logs arml
            WHERE arml.approval_process_id = ap.id
            ORDER BY arml.log_index
        ),
        'steps', (
            SELECT JSON_GROUP_ARRAY(
                JSON_OBJECT(
                    'name', ast.name,
                    'condition', ast.condition,
                    'status', ast.status,
                    'approvers', (
                        SELECT JSON_GROUP_ARRAY(
                            JSON_OBJECT(
                                'status', a.status,
                                'approved_date', a.approved_date,
                                'approver_name', a.approver_name,
                                'proxy_approver_name', a.proxy_approver_name,
                                'proxy_approver_code', a.proxy_approver_code
                            )
                        )
                        FROM approvers a
                        WHERE a.approval_step_id = ast.id
                        ORDER BY a.approver_index
                    ),
                    'comments', (
                        SELECT JSON_GROUP_ARRAY(
                            JSON_OBJECT(
                                'user_name', c.user_name,
                                'date', c.date,
                                'text', c.text,
                                'deleted', CASE WHEN c.deleted=1 THEN json('true')
                                                WHEN c.deleted=0 THEN json('false')
                                                ELSE NULL END
                            )
                        )
                        FROM comments c
                        JOIN comment_associations ca ON c.id = ca.comment_id
                        WHERE ca.approval_step_id = ast.id
                    ),
                    'files', (
                        SELECT JSON_GROUP_ARRAY(
                            JSON_OBJECT(
                                'user_name', f.user_name,
                                'date', f.date,
                                'id', f.id,
                                'name', f.name,
                                'type', f.type,
                                'deleted', CASE WHEN f.deleted=1 THEN json('true')
                                                WHEN f.deleted=0 THEN json('false')
                                                ELSE NULL END
                            )
                        )
                        FROM file_associations fa
                        JOIN files f ON fa.file_id = f.id
                        WHERE fa.approval_step_id = ast.id
                    )
                )
            )
            FROM approval_steps ast
            WHERE ast.approval_process_id = ap.id
            ORDER BY ast.step_index
        ),
        'after_completion', (
            SELECT JSON_OBJECT(
                'comments', (
                    SELECT JSON_GROUP_ARRAY(
                        JSON_OBJECT(
                            'user_name', c.user_name,
                            'date', c.date,
                            'text', c.text,
                            'deleted', CASE WHEN c.deleted=1 THEN json('true')
                                            WHEN c.deleted=0 THEN json('false')
                                            ELSE NULL END
                        )
                    )
                    FROM comments c
                    JOIN comment_associations ca ON c.id = ca.comment_id
                    WHERE ca.approval_after_completion_id = ap.id
                ),
                'files', (
                    SELECT JSON_GROUP_ARRAY(
                        JSON_OBJECT(
                            'user_name', f.user_name,
                            'date', f.date,
                            'id', f.id,
                            'name', f.name,
                            'type', f.type,
                            'deleted', CASE WHEN f.deleted=1 THEN json('true')
                                            WHEN f.deleted=0 THEN json('false')
                                            ELSE NULL END
                        )
                    )
                    FROM file_associations fa
                    JOIN files f ON fa.file_id = f.id
                    WHERE fa.approval_after_completion_id = ap.id
                )
            )
        )
    )
    FROM approval_process ap
    WHERE request_id = ?;
    """, (request_id,))
    result = cursor.fetchone()
    if result is None:
        return None

    return json.loads(result[0])
