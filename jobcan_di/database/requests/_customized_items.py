"""
This module provides functions to update and get 'customized_items' data.

Functions
---------
- `update_customized_items`: Update 'customized_items' table
- `retrieve_customized_items`: Retrieve 'customized_items' data from the database

Target
------
- `/v1/requests/{request_id}` API (GET)
  - `detail` -> `customized_items`
"""
import json
import sqlite3

from ._data_class import GenericMasterDataList, FileDataList



def _update_customized_item_table(cursor:sqlite3.Cursor,
                                  cd_i:dict,
                                  customized_item_id:int,
                                  g_list:GenericMasterDataList):
    """Update 'table_data' table (<-'customized_items').

    Args:
        cursor: SQLite3 cursor object
        cd_i: Customized item data
        customized_item_id: Customized item ID
        g_list: GenericMasterDataList object
    """
    _tables = cd_i["table"] if cd_i["table"] is not None else []
    for i, td_i in enumerate(_tables):
        for j, td_ij in enumerate(td_i):
            cursor.execute("""
            INSERT INTO table_data (customized_item_id, column_number, value, index_1, index_2)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(customized_item_id, index_1, index_2) DO UPDATE SET
                column_number = excluded.column_number,
                value = excluded.value
            """, (customized_item_id, td_ij["column_number"], td_ij["value"], i, j))

            # get the last inserted row id
            cursor.execute("""
                SELECT id FROM table_data
                WHERE customized_item_id = ? AND index_1 = ? AND index_2 = ?""",
                (customized_item_id, i, j))
            td_ij_id = cursor.fetchone()[0]

            # update 'generic_masters' items
            if td_ij["generic_master"] is not None:
                g_list.add_generic_master(td_ij["generic_master"], None, td_ij_id)

        # TODO: remove i-th data from 'table_data' table if the number of items is less than before
    # TODO: remove items from 'generic_masters' table if the number of items is less than before


def _update_generic_masters(cursor:sqlite3.Cursor,
                            g_list:GenericMasterDataList):
    """Update 'generic_masters' and 'generic_master_additional_items' tables.

    Args:
        cursor: SQLite3 cursor object
        g_list: GenericMasterDataList object"""
    # update 'generic_masters' table
    gm_ids = []
    for gm_i in g_list.get_generic_master_data():
        # insert data into 'generic_masters' table
        # custom_item_id and table_data_id can be NULL, but must be unique
        rn, rc, ci, ti = gm_i
        # check if the record is already in the table
        cursor.execute("""
        SELECT id FROM generic_masters
        WHERE (
            customized_item_id IS ? OR
            (customized_item_id IS NULL AND ? IS NULL)
        ) AND (
            table_data_id IS ? OR
            (table_data_id IS NULL AND ? IS NULL)
        )
        """, (ci, ci, ti, ti))
        existing_id = cursor.fetchone()
        if existing_id is not None:
            cursor.execute(
                "UPDATE generic_masters SET record_name = ?, record_code = ? WHERE id = ?",
                (rn, rc, existing_id[0]))
            # get the last inserted row id
            gm_ids.append(existing_id[0])
        else:
            cursor.execute("""
            INSERT INTO generic_masters (record_name, record_code, customized_item_id, table_data_id)
            VALUES (?, ?, ?, ?)
            """, (rn, rc, ci, ti))
            # get the last inserted row id
            cursor.execute(
                "SELECT id FROM generic_masters WHERE record_name = ? AND record_code = ?",
                (gm_i[0], gm_i[1]))
            gm_ids.append(cursor.fetchone()[0])

    # update 'generic_master_additional_items' table
    g_list.add_additional_item_ids(gm_ids)
    for gm_id, ai_s in g_list.get_additional_items_data():
        for i, ai_i in enumerate(ai_s):
            cursor.execute("""
            INSERT INTO generic_master_additional_items (generic_master_id, item_value, item_index)
            VALUES (?, ?, ?)
            ON CONFLICT(generic_master_id, item_index) DO UPDATE SET
                item_value = excluded.item_value
            """, (gm_id, ai_i, i))
        # TODO: remove items from 'generic_master_additional_items' (where id=gm_id) table if the number of items is less than before


def update_customized_items(cursor:sqlite3.Cursor,
                            detail:dict,
                            request_id:str,
                            f_list:FileDataList) -> None:
    """Update 'customized_items' table.

    Args:
        cursor: SQLite3 cursor object
        detail: 'detail' element of the request
        request_id: Request ID
        f_list: FileDataList object"""

    g_list = GenericMasterDataList()

    _customized_items = dci if (dci:=detail['customized_items']) is not None else []
    for i, cd_i in enumerate(_customized_items):
        cursor.execute("""
        INSERT INTO customized_items (request_id, title, content, item_index)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(request_id, item_index) DO UPDATE SET
            title = excluded.title,
            content = excluded.content
        """, (request_id, cd_i["title"], cd_i["content"], i))
        # get the last inserted row id
        cursor.execute(
            "SELECT id FROM customized_items WHERE request_id = ? AND item_index = ?",
            (request_id, i))
        cd_i_id = cursor.fetchone()[0]

        # add file data
        _files = cdi_f if (cdi_f:=cd_i['files']) is not None else []
        for f_i in _files:
            f_list.add_file(f_i, 0, cd_i_id)

        # update 'generic_masters' items
        if cd_i["generic_master"] is not None:
            g_list.add_generic_master(cd_i['generic_master'], cd_i_id, None)

        # update 'table_data' table
        _update_customized_item_table(cursor, cd_i, cd_i_id, g_list)

    # update 'generic_masters' and 'generic_master_additional_items' tables
    _update_generic_masters(cursor, g_list)


def retrieve_customized_items(cursor:sqlite3.Cursor,
                              request_id:str) -> list[dict]:
    """Retrieve 'customized_items' data from the database.

    Args:
        cursor: SQLite3 cursor object
        request_id: Request ID

    Returns:
        Customized items data.
        The data structure is similar to the `detail`->`customized_items` element
        in the response of the `/v1/requests/{request_id}` API.
    """
    cursor.execute("""
    WITH customized_items_json AS (
        SELECT ci.id AS customized_item_id,
            JSON_OBJECT(
                'title', ci.title,
                'content', ci.content,
                'generic_master', JSON_OBJECT(
                    'record_name', gm.record_name,
                    'record_code', gm.record_code,
                    'additional_items', (
                        SELECT JSON_GROUP_ARRAY(gmai.item_value)
                        FROM generic_master_additional_items gmai
                        WHERE gmai.generic_master_id = gm.id
                        ORDER BY gmai.item_index
                    )
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
                    WHERE fa.customized_item_id = ci.id
                ),
                'table', (
                    SELECT JSON_GROUP_ARRAY(outer_json)
                    FROM (
                        SELECT JSON_GROUP_ARRAY(JSON(inner_json)) AS outer_json
                        FROM (
                            SELECT JSON_OBJECT(
                                'column_number', td.column_number,
                                'value', td.value,
                                'generic_master', JSON_OBJECT(
                                    'record_name', gm_td.record_name,
                                    'record_code', gm_td.record_code,
                                    'additional_items', (
                                        SELECT JSON_GROUP_ARRAY(gmai_td.item_value)
                                        FROM generic_master_additional_items gmai_td
                                        WHERE gmai_td.generic_master_id = gm_td.id
                                        ORDER BY gmai_td.item_index
                                    )
                                )
                            ) AS inner_json,
                            td.index_1, td.index_2
                            FROM table_data td
                            LEFT JOIN generic_masters gm_td ON td.id = gm_td.table_data_id
                            WHERE td.customized_item_id = 1
                        )
                        GROUP BY index_1
                    )
                )
            ) AS item_json
        FROM customized_items ci
        LEFT JOIN generic_masters gm ON ci.id = gm.customized_item_id
        WHERE ci.request_id = :request_id
        ORDER BY ci.item_index
    )
    SELECT JSON_GROUP_ARRAY(item_json) AS customized_items
    FROM customized_items_json;
    """, (request_id,))

    result = cursor.fetchone()
    if result is None:
        return []
    return json.loads(result[0])
