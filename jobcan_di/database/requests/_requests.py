"""
This module provides functions to handle `requests` data.

Functions
---------
- `update`: Insert or update data in the database
- `retrieve`: Get data from the database

Target
------
- `/v1/requests/{request_id}` API (GET)
"""
import json
import sqlite3
from typing import Optional, Literal, Union

from ._data_class import FileDataList
from ._customized_items import retrieve_customized_items, update_customized_items
from ._expense import retrieve_expense, update_expense
from ._payment import retrieve_payment, update_payment
from ._ec import retrieve_ec, update_ec
from ._approval_process import retrieve_approval_process, update_approval_process
from ._viewers import retrieve_viewers, update_viewers
from ._modify_logs import retrieve_modify_logs, update_modify_logs
from ._default_attachment_files import retrieve_default_attachment_files, update_default_attachment_files


def _update_files(cursor, f_list:FileDataList) -> None:
    """Update 'files' and 'file_associations' table.

    Args:
        cursor: SQLite3 cursor object
        f_list: FileDataList object
    """
    cursor.executemany("""
    INSERT OR REPLACE INTO files (id, name, type, user_name, date, deleted)
    VALUES (?, ?, ?, ?, ?, ?)""", f_list.get_file_data())

    # update 'file_associations' table
    cursor.executemany("""
    INSERT OR REPLACE INTO file_associations (
        request_id, file_id, customized_item_id, expense_specific_row_id,
        payment_specific_row_id, approval_step_id, approval_after_completion_id, default_attachment
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(request_id, file_id) DO UPDATE SET
        customized_item_id = excluded.customized_item_id,
        expense_specific_row_id = excluded.expense_specific_row_id,
        payment_specific_row_id = excluded.payment_specific_row_id,
        approval_step_id = excluded.approval_step_id,
        approval_after_completion_id = excluded.approval_after_completion_id,
        default_attachment = excluded.default_attachment
    """, f_list.get_file_association_data())

    # TODO: remove items from 'file_associations' table if the number of items is less than before


def update(conn:sqlite3.Connection,
           data:dict) -> None:
    """Insert or update `requests` data in the database.

    Args:
        conn: SQLite3 connection object
        data: Data to be inserted or updated.
              The data should be the result from the '/v1/request/{request_id}/' API.
    """
    cursor = conn.cursor()

    f_list = FileDataList(data['id'])

    # update 'requests' table
    cursor.execute(f"""
    INSERT OR REPLACE INTO requests (
        id, title, status, form_id, form_name, form_type, settlement_type,
        applied_date, applicant_code, applicant_last_name, applicant_first_name,
        applicant_group_name, applicant_group_code, applicant_position_name,
        proxy_applicant_last_name, proxy_applicant_first_name, group_name, group_code,
        project_name, project_code, flow_step_name, is_content_changed, total_amount,
        pay_at, final_approval_period, final_approved_date
    ) VALUES ( {'?, ' * 25} ? )""", (
        data["id"], data["title"], data["status"],
        data["form_id"], data["form_name"], data["form_type"],
        data["settlement_type"], data["applied_date"],
        data["applicant_code"],
        data["applicant_last_name"], data["applicant_first_name"],
        data["applicant_group_name"], data["applicant_group_code"],
        data["applicant_position_name"],
        data["proxy_applicant_last_name"], data["proxy_applicant_first_name"],
        data["group_name"], data["group_code"], data["project_name"], data["project_code"],
        data["flow_step_name"], data["is_content_changed"], data["total_amount"],
        data["pay_at"], data["final_approval_period"], data["final_approved_date"]
    ))

    # update "customized_items" table
    detail = data["detail"]
    update_customized_items(cursor, detail, data["id"], f_list)

    # update "expense" table
    update_expense(cursor, detail["expense"], data["id"], f_list)

    # update "payment" table
    update_payment(cursor, detail["payment"], data["id"], f_list)

    # update "ec" table
    update_ec(cursor, detail["ec"], data["id"])

    # update "approval_process" table
    update_approval_process(cursor, detail["approval_process"], data["id"], f_list)

    # update "viewers" table
    update_viewers(cursor, detail["viewers"], data["id"])

    # update "modify_logs" table
    update_modify_logs(cursor, detail["modify_logs"], data["id"])

    # update "default_attachment_files" table
    update_default_attachment_files(detail["default_attachment_files"], f_list)

    # update "file" table
    _update_files(cursor, f_list)

    conn.commit()


def retrieve(cursor:sqlite3.Cursor,
             request_id:str) -> dict:
    """Retrieve `requests` data from the database.

    Args:
        cursor: SQLite3 cursor object
        request_id: Request ID

    Returns:
        Request data.
        The data structure is similar to the response of the `/v1/requests/{request_id}` API.
    """
    cursor.execute("""
    SELECT JSON_OBJECT(
        'id', r.id,
        'title', r.title,
        'status', r.status,
        'form_id', r.form_id,
        'form_name', r.form_name,
        'form_type', r.form_type,
        'settlement_type', r.settlement_type,
        'applied_date', r.applied_date,
        'applicant_code', r.applicant_code,
        'applicant_last_name', r.applicant_last_name,
        'applicant_first_name', r.applicant_first_name,
        'applicant_group_name', r.applicant_group_name,
        'applicant_group_code', r.applicant_group_code,
        'applicant_position_name', r.applicant_position_name,
        'proxy_applicant_last_name', r.proxy_applicant_last_name,
        'proxy_applicant_first_name', r.proxy_applicant_first_name,
        'group_name', r.group_name,
        'group_code', r.group_code,
        'project_name', r.project_name,
        'project_code', r.project_code,
        'flow_step_name', r.flow_step_name,
        'is_content_changed', CASE WHEN r.is_content_changed=1 THEN json('true')
                                   WHEN r.is_content_changed=0 THEN json('false')
                                   ELSE NULL END,
        'total_amount', r.total_amount,
        'pay_at', r.pay_at,
        'final_approval_period', r.final_approval_period,
        'final_approved_date', r.final_approved_date,
        'detail', (
            SELECT JSON_OBJECT(
                'customized_items', NULL,
                'expense', NULL,
                'payment', NULL,
                'ec', NULL,
                'approval_process', NULL,
                'viewers', NULL,
                'default_attachment_files', NULL,
                'modify_logs', NULL
            )
        )
    )
    FROM requests r
    WHERE r.id = ?;
    """, (request_id,))

    result = cursor.fetchone()
    if result is None:
        return None

    # get data from other tables
    j_data = json.loads(result[0])
    j_data["detail"]["customized_items"] = retrieve_customized_items(cursor, request_id)
    j_data["detail"]["expense"] = retrieve_expense(cursor, request_id)
    j_data["detail"]["payment"] = retrieve_payment(cursor, request_id)
    j_data["detail"]["ec"] = retrieve_ec(cursor, request_id)
    j_data["detail"]["approval_process"] = retrieve_approval_process(cursor, request_id)
    j_data["detail"]["viewers"] = retrieve_viewers(cursor, request_id)
    j_data["detail"]["default_attachment_files"] = retrieve_default_attachment_files(cursor, request_id)
    j_data["detail"]["modify_logs"] = retrieve_modify_logs(cursor, request_id)

    return j_data

def retrieve_ids(
        cursor:sqlite3.Cursor,
        form_id: Union[int, str],
        *,
        status: Optional[set[Literal["in_progress", "completed",
                                     "rejected", "canceled", "returned",
                                     "canceled_after_completion"]]] = None,
        ant_status: Optional[set[Literal["in_progress", "completed",
                                         "rejected", "canceled", "returned",
                                         "canceled_after_completion"]]] = None
    ) -> list[str]:
    """Retrieve request IDs from the database.

    Args:
        cursor: SQLite3 cursor object
        form_id: Form ID
        status: Request status
        ant_status: Request status to exclude

    Note:
        status and ant_status cannot be specified at the same time.
    """
    if status is not None and ant_status is not None:
        raise ValueError("status and ant_status cannot be specified at the same time.")

    query = "SELECT id FROM requests WHERE form_id = ?"
    params = [form_id]
    if status is not None:
        query += " AND status IN (" + ", ".join("?" * len(status)) + ")"
        params.extend(status)
    elif ant_status is not None:
        query += " AND status NOT IN (" + ", ".join("?" * len(ant_status)) + ")"
        params.extend(ant_status)

    cursor.execute(query, params)

    return [r[0] for r in cursor.fetchall()]
