"""
This module contains the function to create tables in the database.

Functions
---------
- `create_tables`: Create tables if they do not exist.
"""
import sqlite3

def create_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist.

    Args:
        conn: SQLite3 connection object

    Note:
        This function creates the following tables:
            - requests
            - customized_items
            - generic_masters
            - additional_items
            - table_data
            - expense
            - expense_specifics
            - expense_specific_rows
            - custom_items
            - payment
            - payment_specifics
            - payment_specific_rows
            - ec
            - shipping_address
            - ec_specifics
            - ec_specific_rows
            - approval_process
            - approval_route_modify_logs
            - approval_steps
            - approvers
            - comments
            - comment_associations
            - viewers
            - modify_logs
            - modify_log_details
            - files
            - file_associations
    """
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS requests (
        id TEXT PRIMARY KEY,
        title TEXT,
        status TEXT,
        form_id INTEGER,
        form_name TEXT,
        form_type TEXT,
        settlement_type TEXT,
        applied_date DATETIME,
        applicant_code TEXT,
        applicant_last_name TEXT,
        applicant_first_name TEXT,
        applicant_group_name TEXT,
        applicant_group_code TEXT,
        applicant_position_name TEXT,
        proxy_applicant_last_name TEXT,
        proxy_applicant_first_name TEXT,
        group_name TEXT,
        group_code TEXT,
        project_name TEXT,
        project_code TEXT,
        flow_step_name TEXT,
        is_content_changed BOOLEAN,
        total_amount INTEGER,
        pay_at DATETIME,
        final_approval_period DATETIME,
        final_approved_date DATETIME
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customized_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT,
        title TEXT,
        content TEXT,
        item_index INTEGER,
        UNIQUE (request_id, item_index),
        FOREIGN KEY (request_id) REFERENCES requests(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS table_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customized_item_id INTEGER,
        column_number INTEGER,
        value TEXT,
        index_1 INTEGER,
        index_2 INTEGER,
        UNIQUE (customized_item_id, index_1, index_2),
        FOREIGN KEY (customized_item_id) REFERENCES customized_items(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS generic_masters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_name TEXT,
        record_code TEXT,
        customized_item_id INTEGER,
        table_data_id INTEGER,
        UNIQUE (customized_item_id, table_data_id),
        FOREIGN KEY (customized_item_id) REFERENCES customized_items(id),
        FOREIGN KEY (table_data_id) REFERENCES table_data(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS generic_master_additional_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        generic_master_id INTEGER,
        item_value TEXT,
        item_index INTEGER,
        UNIQUE (generic_master_id, item_index),
        FOREIGN KEY (generic_master_id) REFERENCES generic_masters(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expense (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT UNIQUE,
        amount INTEGER,
        related_request_title TEXT,
        related_request_id TEXT,
        use_suspense_payment BOOLEAN,
        content_description TEXT,
        advanced_payment INTEGER,
        suspense_payment_amount INTEGER,
        FOREIGN KEY (request_id) REFERENCES requests(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expense_specifics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_id INTEGER,
        type TEXT,
        col_number INTEGER,
        UNIQUE (expense_id, col_number),
        FOREIGN KEY (expense_id) REFERENCES expense(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS expense_specific_rows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_specific_id INTEGER,
        row_number TEXT,
        use_date DATE,
        group_name TEXT,
        project_name TEXT,
        content_description TEXT,
        breakdown TEXT,
        amount INTEGER,
        UNIQUE (expense_specific_id, row_number),
        FOREIGN KEY (expense_specific_id) REFERENCES expense_specifics(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        expense_specific_row_id INTEGER,
        name TEXT,
        item_type TEXT,
        value TEXT,
        item_index INTEGER,
        UNIQUE (expense_specific_row_id, item_index),
        FOREIGN KEY (expense_specific_row_id) REFERENCES expense_specific_rows(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_item_values (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        custom_item_id INTEGER UNIQUE,
        generic_master_code TEXT,
        generic_master_record_name TEXT,
        generic_master_record_code TEXT,
        content TEXT,
        memo TEXT,
        FOREIGN KEY (custom_item_id) REFERENCES custom_items(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_item_value_extension_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        custom_item_value_id INTEGER,
        name TEXT,
        value TEXT,
        item_index INTEGER,
        UNIQUE (custom_item_value_id, item_index),
        FOREIGN KEY (custom_item_value_id) REFERENCES custom_item_values(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT UNIQUE,
        amount INTEGER,
        related_request_title TEXT,
        related_request_id TEXT,
        content_description TEXT,
        FOREIGN KEY (request_id) REFERENCES requests(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payment_specifics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_id INTEGER,
        type TEXT,
        col_number INTEGER,
        UNIQUE (payment_id, col_number),
        FOREIGN KEY (payment_id) REFERENCES payment(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS payment_specific_rows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_specific_id INTEGER,
        company_name TEXT,
        zip_code TEXT,
        address TEXT,
        bank_name TEXT,
        bank_name_kana TEXT,
        bank_account_name_kana TEXT,
        bank_code INTEGER,
        branch_code INTEGER,
        row_number TEXT,
        use_date DATE,
        group_name TEXT,
        project_name TEXT,
        content_description TEXT,
        breakdown TEXT,
        amount INTEGER,
        UNIQUE (payment_specific_id, row_number),
        FOREIGN KEY (payment_specific_id) REFERENCES payment_specific(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS shipping_address (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shipping_address_name TEXT,
        zip_code TEXT,
        country TEXT,
        state TEXT,
        city TEXT,
        address1 TEXT,
        address2 TEXT,
        company_name TEXT,
        contact_name TEXT,
        tel TEXT,
        email TEXT,
        UNIQUE (shipping_address_name, zip_code, country, state, city, address1, address2, company_name, contact_name, tel, email)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ec (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT UNIQUE,
        related_request_id TEXT,
        related_request_title TEXT,
        content_description TEXT,
        billing_destination TEXT,
        shipping_address_id INTEGER,
        FOREIGN KEY (request_id) REFERENCES requests(id)
        FOREIGN KEY (shipping_address_id) REFERENCES shipping_address(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ec_specifics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ec_id INTEGER UNIQUE,
        order_id TEXT,
        retention_deadline DATETIME,
        tax_amount INTEGER,
        shipping_amount INTEGER,
        total_price INTEGER,
        total_amount INTEGER,
        FOREIGN KEY (ec_id) REFERENCES ec(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ec_specific_rows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ec_specific_id INTEGER,
        row_number INTEGER,
        item_name TEXT,
        item_url TEXT,
        item_id TEXT,
        manufacturer_name TEXT,
        sold_by TEXT,
        fulfilled_by TEXT,
        unit_price INTEGER,
        quantity TEXT,
        subtotal INTEGER,
        UNIQUE (ec_specific_id, row_number),
        FOREIGN KEY (ec_specific_id) REFERENCES ec_specifics(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS approval_process (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT UNIQUE,
        is_route_changed_by_applicant BOOLEAN,
        FOREIGN KEY (request_id) REFERENCES requests(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS approval_route_modify_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        approval_process_id INTEGER,
        date DATETIME,
        user_name TEXT,
        log_index INTEGER,
        UNIQUE (approval_process_id, log_index),
        FOREIGN KEY (approval_process_id) REFERENCES approval_process(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS approval_steps (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        approval_process_id INTEGER,
        name TEXT,
        condition TEXT,
        status TEXT,
        step_index INTEGER,
        UNIQUE (approval_process_id, step_index),
        FOREIGN KEY (approval_process_id) REFERENCES approval_process(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS approvers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        approval_step_id INTEGER,
        status TEXT,
        approved_date DATETIME,
        approver_name TEXT,
        approver_code TEXT,
        proxy_approver_name TEXT,
        proxy_approver_code TEXT,
        approver_index INTEGER,
        UNIQUE (approval_step_id, approver_index),
        FOREIGN KEY (approval_step_id) REFERENCES approval_steps(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT,
        date DATETIME,
        text TEXT,
        deleted BOOLEAN,
        UNIQUE (user_name, date, text)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS comment_associations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        comment_id INTEGER UNIQUE,
        approval_step_id INTEGER,
        approval_after_completion_id INTEGER,
        FOREIGN KEY (comment_id) REFERENCES comments(id),
        FOREIGN KEY (approval_step_id) REFERENCES approval_steps(id),
        FOREIGN KEY (approval_after_completion_id) REFERENCES approval_process(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS viewers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT,
        user_name TEXT,
        status TEXT,
        group_name TEXT,
        position TEXT,
        viewer_index INTEGER,
        UNIQUE (request_id, viewer_index),
        FOREIGN KEY (request_id) REFERENCES requests(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS modify_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT,
        date DATETIME,
        user_name TEXT,
        log_index INTEGER,
        UNIQUE (request_id, log_index),
        FOREIGN KEY (request_id) REFERENCES requests(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS modify_log_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modify_log_id INTEGER,
        title TEXT,
        old_value TEXT,
        new_value TEXT,
        log_type TEXT,
        log_detail_index INTEGER,
        UNIQUE (modify_log_id, log_detail_index),
        FOREIGN KEY (modify_log_id) REFERENCES modify_logs(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS modify_log_detail_specifics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modify_log_detail_id INTEGER,
        status TEXT,
        difference TEXT,
        specific_index INTEGER,
        UNIQUE (modify_log_detail_id, specific_index),
        FOREIGN KEY (modify_log_detail_id) REFERENCES modify_log_details(id)
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS files (
        id TEXT PRIMARY KEY,
        name TEXT,
        type TEXT,
        user_name TEXT,
        date DATETIME,
        deleted BOOLEAN
    );''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS file_associations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id TEXT,
        file_id TEXT,
        customized_item_id INTEGER,
        expense_specific_row_id INTEGER,
        payment_specific_row_id INTEGER,
        approval_step_id INTEGER,
        approval_after_completion_id INTEGER,
        default_attachment INTEGER,
        UNIQUE (request_id, file_id),
        FOREIGN KEY (request_id) REFERENCES requests(id),
        FOREIGN KEY (file_id) REFERENCES files(id),
        FOREIGN KEY (customized_item_id) REFERENCES customized_items(id),
        FOREIGN KEY (expense_specific_row_id) REFERENCES expense_specific_rows(id),
        FOREIGN KEY (payment_specific_row_id) REFERENCES payment_specific_rows(id),
        FOREIGN KEY (approval_step_id) REFERENCES approval_steps(id),
        FOREIGN KEY (approval_after_completion_id) REFERENCES approval_process(id)
    );''')

    conn.commit()
