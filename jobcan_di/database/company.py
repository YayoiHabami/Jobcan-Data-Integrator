"""
This module provides functions to store and retrieve the response
of the `/v1/company/` API.

The data is stored in a SQLite database and is retrieved
as a dict object (like the API response).

Functions
---------
- `create_tables`: Create `companies` table in the database
- `update`: Update the `companies` table with the API response
- `retrieve`: Retrieve company data from the `companies` table
"""
import json
import sqlite3
from typing import Optional



def create_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist.

    Note:
        This function creates the following tables:
            - companies
    """
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS companies (
        company_code TEXT PRIMARY KEY,
        company_name TEXT,
        zip_code TEXT,
        address TEXT,
        bank_code TEXT,
        bank_name TEXT,
        branch_code TEXT,
        branch_name TEXT,
        bank_account_type_code TEXT,
        bank_account_code TEXT,
        bank_account_name_kana TEXT,
        invoice_registrated_number TEXT)
    """)

    conn.commit()

def update(conn: sqlite3.Connection,
           data: dict):
    """Update data in the companies table.

    Args:
        conn: SQLite3 connection object
        data: Company data to be inserted or updated.
              The data should be the 'results' element of the result from the '/v1/company/' API.
    """
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR REPLACE INTO companies (
        company_code, company_name, zip_code, address,
        bank_code, bank_name, branch_code, branch_name,
        bank_account_type_code, bank_account_code, bank_account_name_kana,
        invoice_registrated_number
    ) VALUES (
        :company_code, :company_name, :zip_code, :address,
        :bank_code, :bank_name, :branch_code, :branch_name,
        :bank_account_type_code, :bank_account_code, :bank_account_name_kana,
        :invoice_registrated_number
    )""", data)

    conn.commit()

def retrieve(conn: sqlite3.Connection,
             company_code: Optional[list[str]] = None) -> list[dict]:
    """Retrieve company data from the database.

    Args:
        conn: SQLite3 connection object
        company_code: Company code(s) to retrieve data for
                      If None, all company data is retrieved

    Returns:
        dict: Company data
              None if no data is found
    """
    cursor = conn.cursor()

    query = """
    SELECT json_object(
        'company_code', company_code,
        'company_name', company_name,
        'zip_code', zip_code,
        'address', address,
        'bank_code', bank_code,
        'bank_name', bank_name,
        'branch_code', branch_code,
        'branch_name', branch_name,
        'bank_account_type_code', bank_account_type_code,
        'bank_account_code', bank_account_code,
        'bank_account_name_kana', bank_account_name_kana,
        'invoice_registrated_number', invoice_registrated_number
    ) AS company_json
    FROM companies
    """

    if company_code is None:
        cursor.execute(query)
    else:
        where_clause = f"WHERE company_code IN ({','.join(['?']*len(company_code))})"
        cursor.execute(query + where_clause,
                       company_code)

    return [json.loads(row[0]) for row in cursor.fetchall()]
