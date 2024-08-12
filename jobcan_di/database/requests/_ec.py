"""
This module provides functions to update and get EC data in the database.

Functions
---------
- `update_ec`: Update 'ec' table
- `retrieve_ec`: Retrieve 'ec' data from the database

Target
------
- `/v1/requests/{request_id}` API (GET)
  - `detail` -> `ec`
"""
import json
import sqlite3
from typing import Union



def _update_shipping_address(
        cursor:sqlite3.Cursor,
        ship:Union[dict,None]
    ) -> Union[int,None]:
    """Update 'shipping_address' table.

    Args:
        cursor: SQLite3 cursor object
        ship: 'detail'->'ec'->'shipping_address' element of the request

    Returns:
        Shipping address ID. If 'ship' is None, return None.
    """
    if ship is None:
        return None

    cursor.execute("""
    INSERT INTO shipping_address (
        shipping_address_name, zip_code, country, state, city, address1, address2,
        company_name, contact_name, tel, email
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(shipping_address_name, zip_code, country, state, city, address1, address2, company_name, contact_name, tel, email) DO UPDATE SET
        company_name = excluded.company_name,
        contact_name = excluded.contact_name,
        tel = excluded.tel,
        email = excluded.email
    """, (
        ship["shipping_address_name"], ship["zip_code"],
        ship["country"], ship["state"],
        ship["city"], ship["address1"],
        ship["address2"], ship["company_name"],
        ship["contact_name"], ship["tel"],
        ship["email"]
    ))
    # get the last inserted row id
    cursor.execute(
        "SELECT id FROM shipping_address WHERE shipping_address_name = ? AND zip_code = ?",
        (ship["shipping_address_name"], ship["zip_code"]))
    return cursor.fetchone()[0]


def _update_ec_specific_rows(cursor, ecs_rows:list[dict], ecs_id:int) -> None:
    """Update 'ec_specific_rows' table.

    Args:
        cursor: SQLite3 cursor object
        ecs: 'detail'->'ec'->'specifics'->'rows' element of the request
        ecs_id: EC specific ID
    """
    for i, esr_i in enumerate(ecs_rows):
        cursor.execute("""
        INSERT INTO ec_specific_rows (
            ec_specific_id, row_number, item_name, item_url, item_id, manufacturer_name,
            sold_by, fulfilled_by, unit_price, quantity, subtotal
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(ec_specific_id, row_number) DO UPDATE SET
            item_name = excluded.item_name,
            item_url = excluded.item_url,
            item_id = excluded.item_id,
            manufacturer_name = excluded.manufacturer_name,
            sold_by = excluded.sold_by,
            fulfilled_by = excluded.fulfilled_by,
            unit_price = excluded.unit_price,
            quantity = excluded.quantity,
            subtotal = excluded.subtotal
        """, (
            ecs_id, i, esr_i["item_name"], esr_i["item_url"], esr_i["item_id"],
            esr_i["manufacturer_name"], esr_i["sold_by"], esr_i["fulfilled_by"],
            esr_i["unit_price"], esr_i["quantity"], esr_i["subtotal"]
        ))

    # TODO: remove items from "ec_specific_rows" table if the number of items is less than before


def _update_ec_specifics(cursor, ecs:dict, ec_id:int) -> None:
    """Update 'ec_specifics' table.

    Args:
        cursor: SQLite3 cursor object
        ecs: 'detail'->'ec'->'specifics' element of the request
        ec_id: EC ID
    """
    cursor.execute("""
    INSERT INTO ec_specifics (
        ec_id, order_id, retention_deadline, tax_amount, shipping_amount, total_price, total_amount
    ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(ec_id) DO UPDATE SET
        order_id = excluded.order_id,
        retention_deadline = excluded.retention_deadline,
        tax_amount = excluded.tax_amount,
        shipping_amount = excluded.shipping_amount,
        total_price = excluded.total_price,
        total_amount = excluded.total_amount
    """, (
        ec_id, ecs["order_id"], ecs["retention_deadline"], ecs["tax_amount"],
        ecs["shipping_amount"], ecs["total_price"], ecs["total_amount"]
    ))
    # get the last inserted row id
    cursor.execute("SELECT id FROM ec_specifics WHERE ec_id = ?", (ec_id,))
    ecs_id = cursor.fetchone()[0]

    # update "ec_specific_rows" table
    if ecs["rows"] is not None:
        _update_ec_specific_rows(cursor, ecs["rows"], ecs_id)


def update_ec(cursor, ec:Union[dict,None], request_id:str) -> None:
    """Update 'ec' table.

    Args:
        cursor: SQLite3 cursor object
        ec: 'detail'->'ec' element of the request
        request_id: Request ID
        f_list: FileDataList object
    """
    if ec is None:
        return

    # update "shipping_address" table
    ship_id = _update_shipping_address(cursor, ec["shipping_address"])

    cursor.execute("""
    INSERT INTO ec (
        request_id, related_request_id, related_request_title, content_description, billing_destination, shipping_address_id
    ) VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(request_id) DO UPDATE SET
        related_request_id = excluded.related_request_id,
        related_request_title = excluded.related_request_title,
        content_description = excluded.content_description,
        billing_destination = excluded.billing_destination,
        shipping_address_id = excluded.shipping_address_id
    """, (
        request_id, ec["related_request_id"], ec["related_request_title"],
        ec["content_description"], ec["billing_destination"], ship_id
    ))
    # get the last inserted row id
    cursor.execute("SELECT id FROM ec WHERE request_id = ?", (request_id,))
    ec_id = cursor.fetchone()[0]

    # update "ec_specifics" table
    if ec["specifics"] is not None:
        _update_ec_specifics(cursor, ec["specifics"], ec_id)


def retrieve_ec(cursor:sqlite3.Cursor,
                request_id:str) -> dict:
    """Retrieve 'ec' data from the database.

    Args:
        cursor: SQLite3 cursor object
        request_id: Request ID

    Returns:
        EC data.
        The data structure is similar to the `detail`->`ec` element
        in the response of the `/v1/requests/{request_id}` API.
    """
    cursor.execute("""
    SELECT JSON_OBJECT(
        'related_request_id', ec.related_request_id,
        'related_request_title', ec.related_request_title,
        'content_description', ec.content_description,
        'billing_destination', ec.billing_destination,
        'shipping_address', (
            SELECT JSON_OBJECT(
                'shipping_address_name', sa.shipping_address_name,
                'zip_code', sa.zip_code,
                'country', sa.country,
                'state', sa.state,
                'city', sa.city,
                'address1', sa.address1,
                'address2', sa.address2,
                'company_name', sa.company_name,
                'contact_name', sa.contact_name,
                'tel', sa.tel,
                'email', sa.email
            )
            FROM shipping_address sa
            WHERE sa.id = ec.shipping_address_id
        ),
        'specifics', (
            SELECT JSON_OBJECT(
                'order_id', ecs.order_id,
                'retention_deadline', ecs.retention_deadline,
                'tax_amount', ecs.tax_amount,
                'shipping_amount', ecs.shipping_amount,
                'total_price', ecs.total_price,
                'total_amount', ecs.total_amount,
                'rows', (
                    SELECT JSON_GROUP_ARRAY(
                        JSON_OBJECT(
                            'row_number', esr.row_number,
                            'item_name', esr.item_name,
                            'item_url', esr.item_url,
                            'item_id', esr.item_id,
                            'manufacturer_name', esr.manufacturer_name,
                            'sold_by', esr.sold_by,
                            'fulfilled_by', esr.fulfilled_by,
                            'unit_price', esr.unit_price,
                            'quantity', esr.quantity,
                            'subtotal', esr.subtotal
                        )
                    )
                    FROM ec_specific_rows esr
                    WHERE esr.ec_specific_id = ecs.id
                    ORDER BY esr.row_number
                )
            )
            FROM ec_specifics ecs
            WHERE ecs.ec_id = ec.id
        )
    )
    FROM ec
    WHERE request_id = ?;
    """, (request_id,))

    result = cursor.fetchone()
    if result is None:
        return None

    return json.loads(result[0])
