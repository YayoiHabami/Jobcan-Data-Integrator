"""
This module provides functions to update and get 'payment' data in the database.

Functions
---------
- `update_payment`: Update 'payment' table
- `retrieve_payment`: Retrieve 'payment' data from the database

Target
------
- `/v1/requests/{request_id}` API (GET)
    - `detail` -> `payment`
"""
import json
import sqlite3
from typing import Union

from ._data_class import FileDataList



def _update_payment_specific_rows(
        cursor:sqlite3.Cursor,
        pay_specific_rows:list[dict],
        ps_id:int,
        f_list:FileDataList
    ) -> None:
    """Update 'payment_specific_rows' table.

    Args:
        cursor: SQLite3 cursor object
        pay_specific_rows: 'detail'->'payment'->'specifics'->'rows' element of the request
        ps_id: Payment specific ID
        f_list: FileDataList object
    """
    for psr_i in pay_specific_rows:
        cursor.execute("""
        INSERT INTO payment_specific_rows (payment_specific_id, company_name, zip_code, address,
                                            bank_name, bank_name_kana, bank_account_name_kana,
                                            bank_code, branch_code, row_number, use_date, group_name,
                                            project_name, content_description, breakdown, amount)
        VALUES ({','.join(['?']*16)})
        ON CONFLICT(payment_specific_id, row_number) DO UPDATE SET
            company_name = excluded.company_name,
            zip_code = excluded.zip_code,
            address = excluded.address,
            bank_name = excluded.bank_name,
            bank_name_kana = excluded.bank_name_kana,
            bank_account_name_kana = excluded.bank_account_name_kana,
            bank_code = excluded.bank_code,
            branch_code = excluded.branch_code,
            use_date = excluded.use_date,
            group_name = excluded.group_name,
            project_name = excluded.project_name,
            content_description = excluded.content_description,
            breakdown = excluded.breakdown,
            amount = excluded.amount
        """, (
            ps_id, psr_i["company_name"], psr_i["zip_code"], psr_i["address"],
            psr_i["bank_name"], psr_i["bank_name_kana"], psr_i["bank_account_name_kana"],
            psr_i["bank_code"], psr_i["branch_code"], psr_i["row_number"], psr_i["use_date"],
            psr_i["group_name"], psr_i["project_name"], psr_i["content_description"],
            psr_i["breakdown"], psr_i["amount"]
        ))
        # get the last inserted row id
        cursor.execute(
            "SELECT id FROM payment_specific_rows WHERE payment_specific_id = ? AND row_number = ?",
            (ps_id, psr_i["row_number"]))
        psr_i_id = cursor.fetchone()[0]

        # add file data
        _files = psr_i["files"] if psr_i["files"] is not None else []
        for f_i in _files:
            f_list.add_file(f_i, 2, psr_i_id)

        # TODO: remove items from 'payment_specific_rows' table if the number of items is less than before


def _update_payment_specifics(
        cursor:sqlite3.Cursor,
        pay_specifics:list[dict],
        pay_id:int,
        f_list:FileDataList) -> None:
    """Update 'payment_specifics' and 'payment_specific_rows' tables.

    Args:
        cursor: SQLite3 cursor object
        pay_specifics: 'detail'->'payment'->'specifics' element of the request
        pay_id: Payment ID
        f_list: FileDataList object
    """
    for i, ps_i in enumerate(pay_specifics):
        cursor.execute("""
        INSERT INTO payment_specifics (payment_id, type, col_number)
        VALUES (?, ?, ?)
        ON CONFLICT(payment_id, col_number) DO UPDATE SET
            type = excluded.type
        """, (pay_id, ps_i["type"], i))
        # get the last inserted row id
        cursor.execute(
            "SELECT id FROM payment_specifics WHERE payment_id = ? AND col_number = ?",
            (pay_id, i))
        ps_i_id = cursor.fetchone()[0]

        # update 'payment_specific_rows' table
        if ps_i["rows"] is not None:
            _update_payment_specific_rows(cursor, ps_i["rows"], ps_i_id, f_list)

    # TODO: remove items from 'payment_specific' table if the number of items is less than before


def update_payment(
        cursor:sqlite3.Cursor,
        pay:Union[dict,None],
        request_id:str,
        f_list:FileDataList) -> None:
    """Update 'payment' table.

    Args:
        cursor: SQLite3 cursor object
        pay: 'detail'->'payment' element of the request
        request_id: Request ID
        f_list: FileDataList object
    """
    if pay is None:
        return

    cursor.execute("""
    INSERT INTO payment (
        request_id, amount, related_request_title, related_request_id, content_description
    ) VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(request_id) DO UPDATE SET
        amount = excluded.amount,
        related_request_title = excluded.related_request_title,
        related_request_id = excluded.related_request_id,
        content_description = excluded.content_description
    """, (
        request_id, pay["amount"], pay["related_request_title"],
        pay["related_request_id"], pay["content_description"]
    ))
    # get the last inserted row id
    cursor.execute("SELECT id FROM payment WHERE request_id = ?", (request_id,))
    pay_id = cursor.fetchone()[0]

    # update "payment_specifics" table
    if pay["specifics"] is not None:
        _update_payment_specifics(cursor, pay["specifics"], pay_id, f_list)


def retrieve_payment(cursor:sqlite3.Cursor,
                     request_id:str) -> dict:
    """Retrieve 'payment' data from the database.

    Args:
        cursor: SQLite3 cursor object
        request_id: Request ID

    Returns:
        Payment data.
        The data structure is similar to the `detail`->`payment` element
        in the response of `v1/requests/{request_id}` API.
    """
    cursor.execute("""
    SELECT JSON_OBJECT(
        'amount', p.amount,
        'related_request_title', p.related_request_title,
        'related_request_id', p.related_request_id,
        'content_description', p.content_description,
        'specifics', (
            SELECT JSON_GROUP_ARRAY(
                JSON_OBJECT(
                    'rows', (
                        SELECT JSON_GROUP_ARRAY(
                            JSON_OBJECT(
                                'row_number', psr.row_number,
                                'company_name', psr.company_name,
                                'zip_code', psr.zip_code,
                                'address', psr.address,
                                'bank_name', psr.bank_name,
                                'bank_name_kana', psr.bank_name_kana,
                                'bank_account_name_kana', psr.bank_account_name_kana,
                                'bank_code', psr.bank_code,
                                'branch_code', psr.branch_code,
                                'use_date', psr.use_date,
                                'group_name', psr.group_name,
                                'project_name', psr.project_name,
                                'content_description', psr.content_description,
                                'breakdown', psr.breakdown,
                                'amount', psr.amount,
                                'files', (
                                    SELECT JSON_GROUP_ARRAY(
                                        JSON_OBJECT(
                                            'id', f.id,
                                            'name', f.name,
                                            'type', f.type
                                        )
                                    )
                                    FROM file_associations fa
                                    JOIN files f ON fa.file_id = f.id
                                    WHERE fa.payment_specific_row_id = psr.id
                                )
                            )
                        )
                        FROM payment_specific_rows psr
                        WHERE psr.payment_specific_id = ps.id
                        ORDER BY psr.row_number
                    ),
                    'type', ps.type
                )
            )
            FROM payment_specifics ps
            WHERE ps.payment_id = p.id
            ORDER BY ps.col_number
        )
    )
    FROM payment p
    WHERE p.request_id = ?;
    """, (request_id,))

    result = cursor.fetchone()
    if result is None:
        return None

    return json.loads(result[0])
