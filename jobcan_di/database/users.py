"""
This module provides functions to store and retrieve the response
of the `/v3/users/` API.

The data is stored in a SQLite database and is retrieved
as a dict object (like the API response).

Functions
---------
- `create_tables`: Create `users` tables and relationships in the database
- `update`: Insert or update `users` data in the database
- `retrieve`: Retrieve `users` data from the database
"""
import json
import sqlite3
from typing import Optional



def create_tables(conn: sqlite3.Connection) -> None:
    """Create tables if they do not exist.

    Note:
        This function creates the following tables:
            - users
            - user_groups
            - user_positions
            - user_bank_accounts
    """
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        user_code TEXT,
        email TEXT,
        last_name TEXT,
        first_name TEXT,
        is_approver INTEGER,
        user_role INTEGER,
        memo TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_groups (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        group_code TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (group_code) REFERENCES groups (group_code),
        UNIQUE (user_id, group_code)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_positions (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        position_code TEXT,
        group_code TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id),
        FOREIGN KEY (position_code) REFERENCES positions (position_code),
        FOREIGN KEY (group_code) REFERENCES groups (group_code),
        UNIQUE (user_id, position_code, group_code)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_bank_accounts (
        user_id INTEGER,
        bank_code TEXT,
        bank_name TEXT,
        bank_name_kana TEXT,
        branch_code TEXT,
        branch_name TEXT,
        branch_name_kana TEXT,
        bank_account_type_code TEXT,
        bank_account_code TEXT,
        bank_account_name_kana TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    """)

    conn.commit()


def update(conn: sqlite3.Connection,
           data:dict) -> None:
    """Insert or update user data to the database.

    Args:
        conn: sqlite3.Connection
        data: dict
            User data to be inserted or updated.
            The data should be the 'results' element of the result from the '/v3/users/' API.
    """
    cursor = conn.cursor()

    # Insert or update user data
    cursor.execute("""
    INSERT OR REPLACE INTO users (
        id, user_code, email, last_name, first_name, is_approver, user_role, memo
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (data["id"], data["user_code"], data["email"], data["last_name"], data["first_name"],
          int(data["is_approver"]), data["user_role"], data["memo"]))

    # Insert or update user groups
    old_groups = cursor.execute(
        "SELECT user_id, group_code FROM user_groups WHERE user_id = ?",
        (data["id"],)
    ).fetchall()
    new_groups = [(data["id"], group_code) for group_code in data["user_groups"]]
    for u_id, g_code in new_groups:
        cursor.execute("""
        INSERT INTO user_groups (user_id, group_code)
        SELECT ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM user_groups
            WHERE user_id = ? AND
                  (
                      (? IS NULL AND group_code IS NULL) OR
                      (? IS NOT NULL AND group_code = ?)
                  )
        );
        """, (u_id, g_code, u_id, g_code, g_code, g_code))

    # Delete groups that are not in the new data
    for group in old_groups:
        if group not in new_groups:
            cursor.execute(
                "DELETE FROM user_groups WHERE user_id = ? AND group_code = ?",
                (data["id"], group[0])
            )

    # Insert or update user positions
    old_positions = cursor.execute(
        "SELECT user_id, position_code, group_code FROM user_positions WHERE user_id = ?",
        (data["id"],)
    ).fetchall()
    position_data = [(data["id"], p["position_code"], p["group_code"])
                     for p in data["user_positions"]]
    for u_id, p_code, g_code in position_data:
        cursor.execute("""
        INSERT INTO user_positions (user_id, position_code, group_code)
        SELECT ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM user_positions
            WHERE user_id = ? AND position_code = ? AND
                (
                    (? IS NULL AND group_code IS NULL) OR
                    (? IS NOT NULL AND group_code = ?)
                )
        );
        """, (u_id, p_code, g_code, u_id, p_code, g_code, g_code, g_code))

    # Delete positions that are not in the new data
    for position in old_positions:
        if position not in position_data:
            cursor.execute(
                """DELETE FROM user_positions
                   WHERE user_id = ? AND position_code = ? AND group_code = ?""",
                (data["id"], position[0], position[1])
            )

    # Insert or update user bank account
    bank_account = data["user_bank_account"]
    if bank_account:
        cursor.execute("DELETE FROM user_bank_accounts WHERE user_id = ?", (data["id"],))
        cursor.execute("""
        INSERT OR REPLACE INTO user_bank_accounts (
            user_id, bank_code, bank_name, bank_name_kana, branch_code,
            branch_name, branch_name_kana, bank_account_type_code,
            bank_account_code, bank_account_name_kana)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (data["id"], bank_account["bank_code"], bank_account["bank_name"],
            bank_account["bank_name_kana"], bank_account["branch_code"],
            bank_account["branch_name"], bank_account["branch_name_kana"],
            bank_account["bank_account_type_code"], bank_account["bank_account_code"],
            bank_account["bank_account_name_kana"]))

    conn.commit()


def retrieve(
        conn: sqlite3.Connection,
        user_ids:Optional[list[int]] = None) -> list:
    """Retrieve user data from the database.

    Args:
        conn: sqlite3.Connection
        user_ids: list[int]
            List of user IDs to be read.
            If None or empty, all user data will be read.

    Returns:
        list: List of user data."""
    # If user_ids is None, set it to an empty list
    if user_ids is None:
        user_ids = []

    cursor = conn.cursor()

    where_statement = ""
    if user_ids:
        where_statement = "WHERE id IN (" + ", ".join(["?"] * len(user_ids)) + ")"

    sql = f"""
    SELECT u.*,
            CASE
                WHEN COUNT(DISTINCT ug.group_code) > 0 THEN
                    GROUP_CONCAT(DISTINCT CASE
                            WHEN ug.group_code IS NULL THEN 'NULL'
                            ELSE ug.group_code
                            END )
                ELSE NULL
            END as groups,
            CASE
                WHEN COUNT(DISTINCT up.position_code) > 0 THEN
                    GROUP_CONCAT(DISTINCT json_object('position_code', up.position_code, 'group_code', up.group_code))
                ELSE NULL
            END as positions,
            CASE
                WHEN ba.user_id IS NOT NULL THEN
                    json_object('bank_code', ba.bank_code, 'bank_name', ba.bank_name, 'bank_name_kana', ba.bank_name_kana,
                                'branch_code', ba.branch_code, 'branch_name', ba.branch_name, 'branch_name_kana', ba.branch_name_kana,
                                'bank_account_type_code', ba.bank_account_type_code, 'bank_account_code', ba.bank_account_code,
                                'bank_account_name_kana', ba.bank_account_name_kana)
                ELSE NULL
            END as bank_account
    FROM users u
    LEFT JOIN user_groups ug ON u.id = ug.user_id
    LEFT JOIN user_positions up ON u.id = up.user_id
    LEFT JOIN user_bank_accounts ba ON u.id = ba.user_id
    {where_statement}
    GROUP BY u.id
    """
    if user_ids:
        cursor.execute(sql, user_ids)
    else:
        cursor.execute(sql)

    users = cursor.fetchall()
    results = []

    for user in users:
        user_dict = {
            "id": user[0],
            "user_code": user[1],
            "email": user[2],
            "last_name": user[3],
            "first_name": user[4],
            "is_approver": bool(user[5]),
            "user_role": user[6],
            "memo": user[7],
            "user_groups": user[8].split(",") if user[8] else [],
            "user_positions": json.loads("[" + user[9] + "]") if user[9] else [],
            "user_bank_account": json.loads(user[10]) if user[10] else None
        }
        # Replace "NULL" with None
        user_dict["user_groups"] = [None if group == "NULL" else group
                                    for group in user_dict["user_groups"]]

        results.append(user_dict)

    return results
