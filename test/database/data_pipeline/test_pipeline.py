"""data_pipelineモジュールのテスト"""
from os import path
import sqlite3

import pytest

from jobcan_di.database.data_pipeline import (
    PipelineDefinition, SQLiteDBDefinition
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



def init_test_db(db_path:str) -> None:
    """テスト用のDBファイルを初期化する
    """
    conn = sqlite3.connect(db_path)

    # 事前準備用データを挿入
    conn.executescript(CREATE_PRE_USERS_TABLE)
    conn.executescript(INSERT_INTO_PRE_USERS)
    conn.commit()
    conn.close()

@pytest.fixture
def data_pipeline_for_sqlite(tmp_path: str) -> tuple[PipelineDefinition, str]:
    """SQLite用のデータパイプラインのテスト
    (挿入するデータベースを毎回別の一時ファイルとして作成)

    Returns
    -------
    tuple[PipelineDefinition, str]
        データパイプライン定義とDBファイルのパス
    """
    db_path = path.join(tmp_path, 'test-pipeline.sqlite')
    td = parse_toml_data(DB_DEFINITION_TOML)

    if isinstance(td.table_definition, SQLiteDBDefinition):
        td.table_definition.path = db_path
    else:
        raise ValueError("Invalid DB definition")

    return td, db_path

def test_execute_data_pipeline(
        data_pipeline_for_sqlite: tuple[PipelineDefinition, str]
    ) -> None:
    """execute_data_pipelineのテスト"""
    td, db_path = data_pipeline_for_sqlite
    init_test_db(db_path)
    execute_data_pipeline(td)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT * FROM users")
    rows = cur.fetchall()
    assert len(rows) == 10

    conn.close()
