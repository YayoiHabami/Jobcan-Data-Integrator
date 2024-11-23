"""
This module provides functions to store and retrieve the response
of the `/v1/fix_journal/` API.

The data is stored in a SQLite database and is retrieved
as a dict object (like the API response).

Functions
---------
- `create_tables`: Create `journals` table in the database
- `update`: Update the `journals` table with the API response
- `retrieve`: Retrieve journal data from the `journals` table
"""
import json
import sqlite3
from typing import Optional



def create_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist.

    Note:
        This function creates the following tables:
            - fix_journals
            - custom_journal_items
    """
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fix_journals (
        journal_id INTEGER PRIMARY KEY,
        journal_type TEXT,
        journal_date TEXT,
        req_date TEXT,
        journal_summary TEXT,
        view_id TEXT,
        specifics_row_number INTEGER,
        company_code TEXT,
        company_name TEXT,
        user_code TEXT,
        user_name TEXT,
        debit_account_title_code TEXT,
        debit_account_title_name TEXT,
        debit_account_sub_title_code TEXT,
        debit_account_sub_title_name TEXT,
        debit_tax_category_code TEXT,
        debit_tax_category_name TEXT,
        debit_amount INTEGER,
        debit_tax_amount INTEGER,
        debit_amount_without_tax INTEGER,
        debit_group_code TEXT,
        debit_group_name TEXT,
        debit_accounting_group_code TEXT,
        debit_project_code TEXT,
        debit_project_name TEXT,
        credit_account_title_code TEXT,
        credit_account_title_name TEXT,
        credit_account_sub_title_code TEXT,
        credit_account_sub_title_name TEXT,
        credit_tax_category_code TEXT,
        credit_tax_category_name TEXT,
        credit_amount INTEGER,
        credit_tax_amount INTEGER,
        credit_amount_without_tax INTEGER,
        credit_group_code TEXT,
        credit_group_name TEXT,
        credit_accounting_group_code TEXT,
        credit_project_code TEXT,
        credit_project_name TEXT,
        invoice_registrated_number TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS custom_journal_items (
        journal_id INTEGER,
        key TEXT,
        value TEXT,
        generic_master_record_code TEXT
    )
    """)

    conn.commit()

def update(conn: sqlite3.Connection,
           data: dict) -> None:
    """Update data in the fix_journals table.

    Args:
        conn: SQLite3 connection object
        data: Journal data to be inserted or updated.
              The data should be the response from the '/v1/fix_journal/' API.
    """
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO fix_journals (
        journal_id, journal_type, journal_date, req_date, journal_summary,
        view_id, specifics_row_number, company_code, company_name,
        user_code, user_name, debit_account_title_code, debit_account_title_name,
        debit_account_sub_title_code, debit_account_sub_title_name,
        debit_tax_category_code, debit_tax_category_name, debit_amount,
        debit_tax_amount, debit_amount_without_tax, debit_group_code,
        debit_group_name, debit_accounting_group_code, debit_project_code,
        debit_project_name, credit_account_title_code, credit_account_title_name,
        credit_account_sub_title_code, credit_account_sub_title_name,
        credit_tax_category_code, credit_tax_category_name, credit_amount,
        credit_tax_amount, credit_amount_without_tax, credit_group_code,
        credit_group_name, credit_accounting_group_code, credit_project_code,
        credit_project_name, invoice_registrated_number
    ) VALUES (
        :journal_id, :journal_type, :journal_date, :req_date, :journal_summary,
        :view_id, :specifics_row_number, :company_code, :company_name,
        :user_code, :user_name, :debit_account_title_code, :debit_account_title_name,
        :debit_account_sub_title_code, :debit_account_sub_title_name,
        :debit_tax_category_code, :debit_tax_category_name, :debit_amount,
        :debit_tax_amount, :debit_amount_without_tax, :debit_group_code,
        :debit_group_name, :debit_accounting_group_code, :debit_project_code,
        :debit_project_name, :credit_account_title_code, :credit_account_title_name,
        :credit_account_sub_title_code, :credit_account_sub_title_name,
        :credit_tax_category_code, :credit_tax_category_name, :credit_amount,
        :credit_tax_amount, :credit_amount_without_tax, :credit_group_code,
        :credit_group_name, :credit_accounting_group_code, :credit_project_code,
        :credit_project_name, :invoice_registrated_number
    )
    """, data)

    for item in data['custom_journal_item_list']:
        cursor.execute("""
        INSERT OR REPLACE INTO custom_journal_items (journal_id, key, value, generic_master_record_code)
        VALUES (?, ?, ?, ?)
        """, (data['journal_id'], item['key'], item['value'], item['generic_master_record_code']))

    conn.commit()

def retrieve(conn: sqlite3.Connection,
             journal_id: Optional[list[int]] = None) -> list[Optional[dict]]:
    """Retrieve journal data from the database.

    Args:
        conn: SQLite3 connection object
        journal_id: Journal ID(s) to retrieve data for
                    If None, all journal data is retrieved

    Returns:
        dict: Journal data
              None if the journal ID is not found
    """
    cursor = conn.cursor()

    query = """
    SELECT json_object(
        'journal_id', journal_id,
        'journal_type', journal_type,
        'journal_date', journal_date,
        'req_date', req_date,
        'journal_summary', journal_summary,
        'view_id', view_id,
        'specifics_row_number', specifics_row_number,
        'company_code', company_code,
        'company_name', company_name,
        'user_code', user_code,
        'user_name', user_name,
        'debit_account_title_code', debit_account_title_code,
        'debit_account_title_name', debit_account_title_name,
        'debit_account_sub_title_code', debit_account_sub_title_code,
        'debit_account_sub_title_name', debit_account_sub_title_name,
        'debit_tax_category_code', debit_tax_category_code,
        'debit_tax_category_name', debit_tax_category_name,
        'debit_amount', debit_amount,
        'debit_tax_amount', debit_tax_amount,
        'debit_amount_without_tax', debit_amount_without_tax,
        'debit_group_code', debit_group_code,
        'debit_group_name', debit_group_name,
        'debit_accounting_group_code', debit_accounting_group_code,
        'debit_project_code', debit_project_code,
        'debit_project_name', debit_project_name,
        'credit_account_title_code', credit_account_title_code,
        'credit_account_title_name', credit_account_title_name,
        'credit_account_sub_title_code', credit_account_sub_title_code,
        'credit_account_sub_title_name', credit_account_sub_title_name,
        'credit_tax_category_code', credit_tax_category_code,
        'credit_tax_category_name', credit_tax_category_name,
        'credit_amount', credit_amount,
        'credit_tax_amount', credit_tax_amount,
        'credit_amount_without_tax', credit_amount_without_tax,
        'credit_group_code', credit_group_code,
        'credit_group_name', credit_group_name,
        'credit_accounting_group_code', credit_accounting_group_code,
        'credit_project_code', credit_project_code,
        'credit_project_name', credit_project_name,
        'invoice_registrated_number', invoice_registrated_number,
        'custom_journal_item_list', (
            SELECT json_group_array(json_object(
                'key', key,
                'value', value,
                'generic_master_record_code', generic_master_record_code
            ))
            FROM custom_journal_items
            WHERE journal_id = fix_journals.journal_id
        )
    ) AS journal_json
    FROM fix_journals
    """

    if journal_id is None:
        cursor.execute(query)
    else:
        where_clause = f"WHERE journal_id IN ({','.join(['?']*len(journal_id))})"
        cursor.execute(query + where_clause,
                       journal_id)

    return [json.loads(row[0]) for row in cursor.fetchall()]
