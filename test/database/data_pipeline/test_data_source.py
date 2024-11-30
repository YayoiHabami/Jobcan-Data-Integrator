"""
DataSourceクラスおよびその派生クラスのテスト
"""
import os.path as path
import sqlite3
from typing import Final

import pytest
import tomlkit
import tomlkit.items as toml_items

from jobcan_di.database.data_pipeline import (
    SQLiteDataSource, SourceResultFormat
)
from jobcan_di.database.data_pipeline.parser import (
    parse_data_source
)



#
# Test cases for SQLiteDataSource
#

SQLITE_CREATE_TEST_DB_QUERY: Final[str] = """
-- users テーブルの作成
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    email TEXT NOT NULL,
    created_at DATETIME NOT NULL
);

-- roles テーブルの作成
CREATE TABLE roles (
    role_id INTEGER PRIMARY KEY,
    role_name TEXT NOT NULL,
    description TEXT
);

-- user_roles テーブルの作成
CREATE TABLE user_roles (
    user_id INTEGER,
    role_id INTEGER,
    assigned_at DATETIME NOT NULL,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (role_id) REFERENCES roles(role_id)
);

-- users テーブルへのデータ挿入
INSERT INTO users (user_id, username, email, created_at) VALUES
(1, 'john_doe', 'john.doe@example.com', '2020-03-15 14:23:45'),
(2, 'jane_smith', 'jane.smith@example.com', '2020-08-22 09:12:33'),
(3, 'mike_johnson', 'mike.johnson@example.com', '2021-02-11 16:45:21'),
(4, 'emily_brown', 'emily.brown@example.com', '2021-07-30 11:34:56'),
(5, 'david_lee', 'david.lee@example.com', '2022-01-05 08:17:42'),
(25, 'timothy_clark', 'timothy.clark@example.com', '2022-06-18 13:55:28'),
(26, 'rebecca_lewis', 'rebecca.lewis@example.com', '2022-11-29 15:41:19'),
(27, 'jeff_hall', 'jeff.hall@example.com', '2023-04-07 10:28:37'),
(28, 'karen_allen', 'karen.allen@example.com', '2023-09-14 12:39:44'),
(29, 'gary_young', 'gary.young@example.com', '2024-02-25 17:22:51'),
(30, 'sandra_king', 'sandra.king@example.com', '2024-08-03 07:56:13');

-- roles テーブルへのデータ挿入
INSERT INTO roles (role_id, role_name, description) VALUES
(1, 'Admin', 'Full system access and control'),
(2, 'Manager', 'Department-level access and control'),
(3, 'Developer', 'Access to development tools and environments'),
(4, 'Designer', 'Access to design tools and assets'),
(5, 'Support', 'Customer support and ticket management'),
(6, 'Analyst', 'Data analysis and reporting capabilities'),
(7, 'Marketing', 'Access to marketing tools and campaigns'),
(8, 'HR', 'Human resources management access'),
(9, 'Finance', 'Financial data and reporting access'),
(10, 'Sales', 'Sales data and customer management access');

-- user_roles テーブルへのデータ挿入
INSERT INTO user_roles (user_id, role_id, assigned_at) VALUES
(1, 1, '2020-04-01 10:15:22'),
(2, 2, '2020-09-12 14:33:47'),
(3, 3, '2021-03-25 09:44:18'),
(4, 4, '2021-08-16 16:27:55'),
(5, 5, '2022-02-08 11:52:39'),
(25, 2, '2022-07-19 13:41:26'),
(25, 9, '2022-12-30 08:19:45'),
(26, 4, '2023-05-11 15:36:58'),
(26, 7, '2023-10-22 12:48:33'),
(27, 3, '2024-03-07 17:14:27'),
(27, 5, '2024-08-18 10:25:41'),
(27, 6, '2020-05-29 14:57:16'),
(28, 8, '2020-11-09 09:38:52'),
(28, 9, '2021-04-20 16:13:45'),
(28, 10, '2021-09-01 11:45:23'),
(29, 2, '2022-03-12 15:29:37'),
(29, 7, '2022-08-23 08:54:19'),
(29, 10, '2023-01-04 13:17:42'),
(30, 1, '2023-06-15 17:43:28'),
(30, 2, '2023-11-26 10:31:56'),
(30, 9, '2024-04-08 15:59:34');
"""
"""SQLiteのテスト用データベースを作成するクエリ

- users テーブル: ユーザー情報 (11件)
- roles テーブル: ユーザーのロール情報 (10件)
- user_roles テーブル: ユーザーとロールの関連付け情報、1ユーザあたり1役職以上
"""

SQLITE_TEST_DB_PATH: Final[str] = path.join(path.dirname(__file__),
                                            "test_db.sqlite")
"""SQLiteのテスト用データベースのパス"""
SQLITE_TEST_DB_PATH_WITH_ESCAPE: Final[str] = SQLITE_TEST_DB_PATH.replace("\\", "/")

@pytest.fixture
def sqlite_ro_conn():
    """SQLite テスト用データベースの読み取り専用接続を作成する"""
    # テスト用データベースを作成
    if not path.exists(SQLITE_TEST_DB_PATH):
        with sqlite3.connect(SQLITE_TEST_DB_PATH) as conn:
            conn.executescript(SQLITE_CREATE_TEST_DB_QUERY)
            conn.commit()

    # 読み取り専用の接続を作成
    conn = sqlite3.connect(f"file:{SQLITE_TEST_DB_PATH}?mode=ro", uri=True)
    yield conn

    # 接続を閉じる
    conn.close()

def test_sqlite_data_source(sqlite_ro_conn):
    """テスト用データベースのデータテスト"""
    # テスト用データベースの users テーブルからデータを取得
    data = sqlite_ro_conn.execute("SELECT * FROM users").fetchall()

    # データの検証
    assert len(data) == 11

SQLITE_DATA_SOURCE_TEXT: Final[str] = f'''
[source]
name = "user_and_role"
type = "sqlite"
result_format = "json-object-results"
path = "{SQLITE_TEST_DB_PATH_WITH_ESCAPE}"
query = """
SELECT json_object(
    'user_id', user_id,
    'username', username,
    'user_roles', (
        SELECT json_group_array(
            json_object(
                'role_name', role_name
            )
        ) FROM user_roles
          LEFT JOIN roles ON user_roles.role_id = roles.role_id
          WHERE user_id = users.user_id
    )
) FROM users;
"""
'''

@pytest.fixture
def sqlite_data_source_table() -> toml_items.Table:
    """SQLite データソースのためのTableオブジェクトを作成する"""
    item = tomlkit.parse(SQLITE_DATA_SOURCE_TEXT)["source"]
    if not isinstance(item, toml_items.Table):
        raise ValueError("Invalid TOML structure")

    return item

def test_parse_sqlite_data_source(sqlite_data_source_table):
    """SQLite データソースのパーステスト"""
    # データソースのパース
    data_source = parse_data_source(sqlite_data_source_table)

    # データソースの検証
    assert isinstance(data_source, SQLiteDataSource)
    assert data_source.name == "user_and_role"
    assert data_source.path == SQLITE_TEST_DB_PATH_WITH_ESCAPE

def test_sqlite_data_source_extract(sqlite_ro_conn, sqlite_data_source_table):
    """SQLite データソースのデータ取得テスト"""
    # データソースのパース
    data_source = parse_data_source(sqlite_data_source_table)
    assert isinstance(data_source, SQLiteDataSource)

    # データの取得
    data = data_source.extract_data()

    # データの検証
    assert len(data) == 11
    assert all("user_id" in item and "username" in item
                                 and "user_roles" in item
               for item in data)
    assert all(isinstance(item["user_id"], int)
               and isinstance(item["username"], str)
               and isinstance(item["user_roles"], list)
               for item in data)
