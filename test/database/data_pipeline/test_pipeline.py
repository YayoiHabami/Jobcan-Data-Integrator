import os
from os import path
import sqlite3

import pytest

from jobcan_di.database.data_pipeline import (
    PipelineDefinition
)
from jobcan_di.database.data_pipeline.parser import parse_toml_data
from jobcan_di.database.data_pipeline.pipeline import (
    execute_data_pipeline
)


TEST_DB_PATH = path.join(path.dirname(__file__), 'test-pipeline.sqlite')
"""テスト用のDBファイルのパス"""
TEST_DB_PATH_WITH_ESCAPE = TEST_DB_PATH.replace('\\', '/')
"""エスケープされたテスト用のDBファイルのパス"""

CREATE_PRE_USERS_TABLE = """
CREATE TABLE IF NOT EXISTS pre_users (
    user_code TEXT PRIMARY KEY,
    email TEXT UNIQUE,
    first_name TEXT NOT NULL,
    position_code TEXT NOT NULL
);
"""
"""pre_usersテーブルの作成SQL"""
INSERT_INTO_PRE_USERS = """
INSERT INTO pre_users
    (user_code, email, first_name, position_code)
VALUES
    ("1", "john.doe@example.com", "John", "DEV"),
    ("2", "jane.doe@example.com", "Jane", "HR"),
    ("3", "alice.smith@example.com", "Alice", "FIN"),
    ("4", "bob.jones@example.com", "Bob", "IT"),
    ("5", "charlie.brown@example.com", "Charlie", "MKT"),
    ("6", "david.wilson@example.com", "David", "SALES"),
    ("7", "eve.davis@example.com", "Eve", "ENG"),
    ("8", "frank.miller@example.com", "Frank", "QA"),
    ("9", "grace.lee@example.com", "Grace", "SUPPORT"),
    ("10", "henry.moore@example.com", "Henry", "ADMIN");
"""
"""pre_usersテーブルへのデータ挿入SQL"""

DB_DEFINITION_TOML = f'''
[table_definitions]
type = "SQLite"
path = "{TEST_DB_PATH_WITH_ESCAPE}"
tables = [
"""
CREATE TABLE IF NOT EXISTS users (
    user_code INTEGER PRIMARY KEY,
    email TEXT UNIQUE,
    first_name TEXT NOT NULL
);
""",
"""
CREATE TABLE IF NOT EXISTS user_positions (
    user_code INTEGER NOT NULL,
    position_code TEXT NOT NULL,
    UNIQUE(user_code, position_code)
);
"""
]

[[data_link.sources]]
name = "source-sqlite"
type = "SQLite"
result_format = "json-object-results"
path = "{TEST_DB_PATH_WITH_ESCAPE}"
query = """
SELECT json_object(
    'user_code', user_code,
    'email', email,
    'first_name', first_name,
    'position_code', position_code
) FROM pre_users;
"""

[data_link.insertion_profile.users]
query = """
INSERT INTO users (user_code, email, first_name)
VALUES (:user_code, :email, :first_name);
"""
source = "source-sqlite"
named_parameters = [
    "user_code", ["user_code"],
    "email", ["email"],
    "first_name", ["first_name"]
]
conversion_method = [
    "user_code", "to-int"
]
'''

def get_connection() -> sqlite3.Connection:
    """SQLiteのConnectionオブジェクトを取得する
    Returns
    -------
    sqlite3.Connection
        Connection object
    """
    # 既に存在するDBファイルを削除
    if path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    conn = sqlite3.connect(TEST_DB_PATH)

    # 事前準備用データを挿入
    conn.executescript(CREATE_PRE_USERS_TABLE)
    conn.executescript(INSERT_INTO_PRE_USERS)

@pytest.fixture
def pipeline_def() -> PipelineDefinition:
    """PipelineDefinitionオブジェクトを返す"""
    return parse_toml_data(DB_DEFINITION_TOML)

def test_execute_data_pipeline(pipeline_def:PipelineDefinition):
    """execute_data_pipelineのテスト"""
    get_connection()
    execute_data_pipeline(pipeline_def)

    conn = sqlite3.connect(TEST_DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT * FROM users")
    rows = cur.fetchall()
    assert len(rows) == 10
