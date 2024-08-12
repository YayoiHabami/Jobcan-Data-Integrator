"""
This module provides functions to update and get 'expense' data.

Functions
---------
- `update_expense`: Update 'expense' table
- `retrieve_expense`: Retrieve 'expense' data from the database

Target
------
- `/v1/requests/{request_id}` API (GET)
    - `detail` -> `expense`
"""
import json
import sqlite3
from typing import Union

from ._data_class import FileDataList



def _update_expense_specific_row_custom_item_value(
        cursor:sqlite3.Cursor,
        custom_item_values:dict,
        custom_item_id:int) -> None:
    """Update 'custom_item_values' table (<-'custom_items').

    Args:
        cursor: SQLite3 cursor object
        custom_item_values: 'value' element of the 'custom_items' element of the request
        custom_item_id: Custom item ID
    """
    cursor.execute("""
    INSERT INTO custom_item_values (custom_item_id, generic_master_code, generic_master_record_name,
                                    generic_master_record_code, content, memo)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(custom_item_id) DO UPDATE SET
        generic_master_code = excluded.generic_master_code,
        generic_master_record_name = excluded.generic_master_record_name,
        generic_master_record_code = excluded.generic_master_record_code,
        content = excluded.content,
        memo = excluded.memo
    """, (custom_item_id, custom_item_values['generic_master_code'],
          custom_item_values['generic_master_record_name'],
          custom_item_values['generic_master_record_code'],
          custom_item_values['content'], custom_item_values['memo']))
    # get the last inserted row id
    cursor.execute('SELECT id FROM custom_item_values WHERE custom_item_id = ?', (custom_item_id,))
    civ_id = cursor.fetchone()[0]

    # update 'custom_item_value_extension_items' table
    _extension_items = _exi if (_exi:=custom_item_values["extension_items"]) is not None else []
    for i, cive_i in enumerate(_extension_items):
        cursor.execute("""
        INSERT INTO custom_item_value_extension_items (custom_item_value_id, name, value, item_index)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(custom_item_value_id, item_index) DO UPDATE SET
            name = excluded.name,
            value = excluded.value
        """, (civ_id, cive_i["name"], cive_i["value"], i))

    # TODO: remove items from 'custom_item_value_extension_items' table if the number of items is less than before


def _update_expense_specific_row_custom_items(
        cursor:sqlite3.Cursor,
        custom_items:list[dict],
        row_id:int) -> None:
    """Update 'custom_items' table (<-'expense_specific_rows').

    Args:
        cursor: SQLite3 cursor object
        custom_items: 'detail'->'expense'->'specifics'->'rows'->'custom_items' element of the request
        row_id: Expense specific row ID
    """
    for i, ci_i in enumerate(custom_items):
        update_custom_item_values_table = False
        if (ci_i["value"] is None) or (isinstance(ci_i['value'], str)):
            # the 'value' element is simply stored in the 'custom_items' table
            value = "" if ci_i["value"] is None else ci_i["value"]
        else:
            # the 'value' element is stored in the 'custom_item_values' table
            value = None
            update_custom_item_values_table = True

        cursor.execute("""
        INSERT INTO custom_items (expense_specific_row_id, name, item_type, value, item_index)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(expense_specific_row_id, item_index) DO UPDATE SET
            name = excluded.name,
            item_type = excluded.item_type,
            value = excluded.value
        """, (row_id, ci_i["name"], ci_i["item_type"], value, i))
        # get the last inserted row id
        cursor.execute(
            "SELECT id FROM custom_items WHERE expense_specific_row_id = ? AND item_index = ?",
            (row_id, i))
        ci_i_id = cursor.fetchone()[0]

        # update 'custom_item_values' table
        if update_custom_item_values_table:
            _update_expense_specific_row_custom_item_value(cursor, ci_i['value'], ci_i_id)

    # TODO: remove items from 'custom_items' table if the number of items is less than before


def _update_expense_specific_rows(
        cursor:sqlite3.Cursor,
        es_rows:list[dict],
        es_id:int,
        f_list:FileDataList) -> None:
    """Update 'expense_specific_rows' table.

    Args:
        cursor: SQLite3 cursor object
        es_rows: 'detail'->'expense'->'specifics'->'rows' element of the request
        es_id: Expense specific ID
        f_list: FileDataList object
    """
    for esr_i in es_rows:
        cursor.execute("""
        INSERT INTO expense_specific_rows (expense_specific_id, row_number, use_date, group_name,
                                            project_name, content_description, breakdown, amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(expense_specific_id, row_number) DO UPDATE SET
            use_date = excluded.use_date,
            group_name = excluded.group_name,
            project_name = excluded.project_name,
            content_description = excluded.content_description,
            breakdown = excluded.breakdown,
            amount = excluded.amount
        """, (es_id, esr_i['row_number'], esr_i['use_date'], esr_i['group_name'],
              esr_i['project_name'], esr_i['content_description'], esr_i['breakdown'],
              esr_i['amount']))
        # get the last inserted row id
        cursor.execute(
            "SELECT id FROM expense_specific_rows WHERE expense_specific_id = ? AND row_number = ?",
            (es_id, esr_i['row_number']))
        esr_i_id = cursor.fetchone()[0]

        # update 'custom_items' table
        if esr_i.get('custom_items', None) is not None:
            _update_expense_specific_row_custom_items(cursor, esr_i['custom_items'], esr_i_id)

        # add file data
        _files = esr_i['files'] if esr_i['files'] is not None else []
        for f_i in _files:
            f_list.add_file(f_i, 1, esr_i_id)

    # TODO: remove items from 'expense_specific_rows' table if the number of items is less than before


def _update_expense_specifics(
        cursor:sqlite3.Cursor,
        exp_specifics:list[dict],
        exp_id:int,
        f_list:FileDataList) -> None:
    """Update 'expense_specifics' and 'expense_specific_rows' tables.

    Args:
        cursor: SQLite3 cursor object
        exp_specifics: 'detail'->'expense'->'specifics' element of the request
        exp_id: Expense ID
        f_list: FileDataList object
    """
    # update 'expense_specifics' table
    for i, es_i in enumerate(exp_specifics):
        cursor.execute("""
        INSERT INTO expense_specifics (expense_id, type, col_number)
        VALUES (?, ?, ?)
        ON CONFLICT(expense_id, col_number) DO UPDATE SET
            type = excluded.type
        """, (exp_id, es_i["type"], i))
        # get the last inserted row id
        cursor.execute(
            "SELECT id FROM expense_specifics WHERE expense_id = ? AND col_number = ?",
            (exp_id, i))
        es_i_id = cursor.fetchone()[0]

        # update 'expense_specific_rows' table
        if es_i["rows"] is not None:
            _update_expense_specific_rows(cursor, es_i["rows"], es_i_id, f_list)

    # remove items from 'expense_specific' table if the number of items is less than before
    # TODO: make test pattern
    cursor.execute("SELECT id FROM expense_specifics WHERE expense_id = ?",
                   (exp_id,))
    es_id_list = [es_id[0] for es_id in cursor.fetchall()]
    if len(exp_specifics) < len(es_id_list):
        cursor.execute(
            "DELETE FROM expense_specificsWHERE expense_id = ? AND col_number > ?",
            (exp_id, len(exp_specifics) - 1)
        )


def update_expense(
        cursor:sqlite3.Cursor,
        exp:Union[dict,None],
        request_id:str,
        f_list:FileDataList,
        default_use_suspend_payment: Union[bool,None]=None,
        default_content_description: Union[str,None]=None
    ) -> None:
    """Update 'expense' table.

    Args:
        cursor: SQLite3 cursor object
        exp: 'detail'->'expense' element of the request
        request_id: Request ID
        f_list: FileDataList object
        default_use_suspend_payment: Default value of
            'detail'->'expense'->'use_suspense_payment' element
        default_content_description: Default value of
            'detail'->'expense'->'content_description' element

    Note:
        - `default_use_suspend_payment` and `default_content_description` are used
        when GET request missing the corresponding elements.
    """
    if exp is None:
        return

    cursor.execute("""
    INSERT INTO expense (
        request_id, amount, related_request_title, related_request_id,
        use_suspense_payment, content_description, advanced_payment, suspense_payment_amount
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(request_id) DO UPDATE SET
        amount = excluded.amount,
        related_request_title = excluded.related_request_title,
        related_request_id = excluded.related_request_id,
        use_suspense_payment = excluded.use_suspense_payment,
        content_description = excluded.content_description,
        advanced_payment = excluded.advanced_payment,
        suspense_payment_amount = excluded.suspense_payment_amount
    """, (
        request_id, exp["amount"],
        exp["related_request_title"],
        exp["related_request_id"],
        exp.get("use_suspense_payment", default_use_suspend_payment),
        exp.get("content_description", default_content_description),
        exp["advanced_payment"],
        exp["suspense_payment_amount"]
    ))
    # get the last inserted row id
    cursor.execute("SELECT id FROM expense WHERE request_id = ?", (request_id,))
    exp_id = cursor.fetchone()[0]

    # update "expense_specifics" table
    if exp["specifics"] is not None:
        _update_expense_specifics(cursor, exp["specifics"], exp_id, f_list)

def retrieve_expense(cursor:sqlite3.Cursor,
                     request_id:str) -> dict:
    """Retrieve "expense" data from the database.

    Args:
        cursor: SQLite3 cursor object
        request_id: Request ID

    Returns:
        Expense data.
        The data structure is similar to the `detail`->`expense` element
        in the response of the `/v1/requests/{request_id}` API.
    """
    cursor.execute("""
    SELECT JSON_OBJECT(
        'amount', e.amount,
        'related_request_title', e.related_request_title,
        'related_request_id', e.related_request_id,
        'specifics', (
            SELECT JSON_GROUP_ARRAY(
                   JSON_OBJECT(
                        'rows', (
                            SELECT JSON_GROUP_ARRAY(
                                JSON_OBJECT(
                                    'row_number', esr.row_number,
                                    'use_date', esr.use_date,
                                    'group_name', esr.group_name,
                                    'project_name', esr.project_name,
                                    'content_description', esr.content_description,
                                    'breakdown', esr.breakdown,
                                    'amount', esr.amount,
                                    'custom_items', (
                                        SELECT JSON_GROUP_ARRAY(
                                            JSON_OBJECT(
                                                'name', ci.name,
                                                'item_type', ci.item_type,
                                                'value', (
                                                    CASE
                                                        WHEN ci.value IS NULL THEN (
                                                            SELECT JSON_OBJECT(
                                                                'generic_master_code', civ.generic_master_code,
                                                                'generic_master_record_name', civ.generic_master_record_name,
                                                                'generic_master_record_code', civ.generic_master_record_code,
                                                                'content', civ.content,
                                                                'memo', civ.memo,
                                                                'extension_items', (
                                                                    SELECT JSON_GROUP_ARRAY(
                                                                        JSON_OBJECT(
                                                                            'name', cive.name,
                                                                            'value', cive.value
                                                                        )
                                                                    )
                                                                    FROM custom_item_value_extension_items cive
                                                                    WHERE cive.custom_item_value_id = civ.id
                                                                )
                                                            )
                                                            FROM custom_item_values civ
                                                            WHERE civ.custom_item_id = ci.id
                                                        )
                                                        ELSE ci.value
                                                    END
                                                )
                                            )
                                        )
                                        FROM custom_items ci
                                        WHERE ci.expense_specific_row_id = esr.id
                                        ORDER BY ci.item_index
                                    ),
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
                                        WHERE fa.expense_specific_row_id = esr.id
                                    )
                                )
                            )
                            FROM expense_specific_rows esr
                            WHERE esr.expense_specific_id = es.id
                            ORDER BY esr.row_number
                        ),
                        'type', es.type
                   )
            )
            FROM expense_specifics es
            WHERE es.expense_id = e.id
            ORDER BY es.col_number
        ),
        'use_suspense_payment', CASE WHEN e.use_suspense_payment=1 THEN json('true')
                                     WHEN e.use_suspense_payment=0 THEN json('false')
                                     ELSE NULL END,
        'content_description', e.content_description,
        'advanced_payment', e.advanced_payment,
        'suspense_payment_amount', e.suspense_payment_amount
    )
    FROM expense e
    WHERE e.request_id = ?;
    """, (request_id,))

    result = cursor.fetchone()

    if result is None:
        return None
    return json.loads(result[0])
