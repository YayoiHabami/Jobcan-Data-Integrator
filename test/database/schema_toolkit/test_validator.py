"""Unit tests for the `check_table_structure` function in the `validator` module."""
import sqlite3
import pytest

from jobcan_di.database.schema_toolkit import SQLDialect
from jobcan_di.database.schema_toolkit.validator import check_table_structure
from jobcan_di.database.schema_toolkit.sql_parser import parse_sql

@pytest.fixture
def sqlite_connection():
    """Create an in-memory SQLite connection."""
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()

@pytest.fixture
def create_table(sqlite_connection):
    """Create a table in the SQLite database."""
    def _create_table(sql: str):
        cursor = sqlite_connection.cursor()
        cursor.execute(sql)
        sqlite_connection.commit()
    return _create_table

def test_correct_table_structure(sqlite_connection, create_table):
    """正しいテーブル構造の場合のテスト"""
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER CHECK (age >= 18),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    create_table(sql)
    table_structures = parse_sql(sql)
    assert len(table_structures) == 1
    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is None, f"Unexpected error: {result}"

def test_missing_column(sqlite_connection, create_table):
    """カラムが不足している場合のテスト

    TableStructureに含まれるカラムがテーブルに存在しない場合にエラーが発生することを確認する。
    """
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE
    );
    """
    create_table(sql)
    expected_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER
    );
    """
    table_structures = parse_sql(expected_sql)
    assert len(table_structures) == 1
    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is not None
    assert "Column 'age' does not exist" in result

def test_extra_column(sqlite_connection, create_table):
    """余分なカラムが存在する場合のテスト

    TableStructureに含まれないカラムがテーブルに存在する場合にエラーが発生することを確認する。
    """
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER,
        extra_column TEXT
    );
    """
    create_table(sql)
    expected_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER
    );
    """
    table_structures = parse_sql(expected_sql)
    assert len(table_structures) == 1
    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is not None
    assert "Unexpected column(s): 'extra_column'" in result

def test_wrong_column_type(sqlite_connection, create_table):
    """カラムの型が異なる場合のテスト"""
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age TEXT
    );
    """
    create_table(sql)
    expected_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER
    );
    """
    table_structures = parse_sql(expected_sql)
    assert len(table_structures) == 1
    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is not None
    assert "Column 'age' in table 'users' type mismatch" in result

def test_missing_primary_key(sqlite_connection, create_table):
    """主キーが不足している場合のテスト

    TableStructureで指定された主キーと、テーブルの主キーが一致しない場合に
    エラーが発生することを確認する。
    """
    sql = """
    CREATE TABLE users (
        id INTEGER,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER
    );
    """
    create_table(sql)
    expected_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER
    );
    """
    table_structures = parse_sql(expected_sql)
    assert len(table_structures) == 1
    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is not None
    assert "Primary key mismatch" in result

def test_missing_unique_constraint(sqlite_connection, create_table):
    """UNIQUE制約が不足している場合のテスト

    TableStructureで指定されたUNIQUE制約とテーブルのUNIQUE制約が一致しない場合に
    エラーが発生することを確認する。
    """
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        age INTEGER
    );
    """
    create_table(sql)
    expected_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER
    );
    """
    table_structures = parse_sql(expected_sql)
    assert len(table_structures) == 1
    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is not None
    assert "Unique keys mismatch or not present in table 'users'" in result

def test_missing_not_null_constraint(sqlite_connection, create_table):
    """NOT NULL制約が不足している場合のテスト

    TableStructureにNOT NULL制約が含まれているが、
    テーブルにNOT NULL制約が存在しない場合にエラーが発生することを確認する。
    """
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER
    );
    """
    create_table(sql)
    expected_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER
    );
    """
    table_structures = parse_sql(expected_sql)
    assert len(table_structures) == 1
    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is not None
    assert "Column 'username' in table 'users' NOT NULL constraint mismatch" in result

def test_extra_not_null_constraint(sqlite_connection, create_table):
    """余分なNOT NULL制約が存在する場合のテスト

    TableStructureにNOT NULL制約が含まれていないが、
    テーブルにNOT NULL制約が存在する場合にエラーが発生することを確認する。
    """
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER NOT NULL
    );
    """
    create_table(sql)
    expected_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER
    );
    """
    table_structures = parse_sql(expected_sql)
    assert len(table_structures) == 1
    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is not None
    assert "Column 'age' in table 'users' NOT NULL constraint mismatch" in result

def test_missing_default_value(sqlite_connection, create_table):
    """DEFAULT値が不足している場合のテスト

    TableStructureにDEFAULT値が含まれているが、
    テーブルにDEFAULT値が存在しない場合にエラーが発生することを確認する。
    """
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER,
        created_at TIMESTAMP
    );
    """
    create_table(sql)
    expected_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    table_structures = parse_sql(expected_sql)
    assert len(table_structures) == 1
    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is not None
    assert "Column 'created_at' in table 'users' DEFAULT value mismatch" in result

def test_extra_default_value(sqlite_connection, create_table):
    """余分なDEFAULT値が存在する場合のテスト

    TableStructureにDEFAULT値が含まれていないが、テーブルにDEFAULT値が存在する場合にエラーが発生することを確認する。
    """
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    create_table(sql)
    expected_sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER,
        created_at TIMESTAMP
    );
    """
    table_structures = parse_sql(expected_sql)
    assert len(table_structures) == 1
    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is not None
    assert "Column 'created_at' in table 'users' DEFAULT value mismatch" in result

def test_table_not_exists(sqlite_connection):
    """テーブルが存在しない場合のテスト

    TableStructureに含まれるテーブルが存在しない場合にエラーが発生することを確認する。
    """
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        age INTEGER
    );
    """
    table_structures = parse_sql(sql)
    assert len(table_structures) == 1
    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is not None
    assert "Table 'users' does not exist" in result

def test_multiple_tables(sqlite_connection, create_table):
    """複数のテーブルを検証する場合のテスト"""
    sql1 = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE
    );
    """
    sql2 = """
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        title TEXT NOT NULL,
        content TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """
    create_table(sql1)
    create_table(sql2)

    table_structures = parse_sql(sql1 + sql2)
    assert len(table_structures) == 2

    for table_structure in table_structures:
        result = check_table_structure(sqlite_connection, table_structure)
        assert result is None, f"Unexpected error: {result}"

def test_foreign_key_constraint_disabled(sqlite_connection, create_table):
    """FOREIGN KEY制約が無効化されている場合のテスト

    TableStructureおよびテーブルにFOREIGN KEY制約が含まれているが、
    DBのFOREIGN KEY制約が無効化されている場合にエラーが発生することを確認する。
    """
    sql1 = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE
    );
    """
    sql2 = """
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        title TEXT NOT NULL,
        content TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """
    create_table(sql1)
    create_table(sql2)

    table_structures = parse_sql(sql2)
    assert len(table_structures) == 1

    # FOREIGN KEYを無効化
    cursor = sqlite_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")

    # SQLiteの場合FK制約が無効化されている場合にエラーを無視するため、
    # SQLDialect.OTHERを指定してエラーチェックを行う
    result = check_table_structure(sqlite_connection, table_structures[0],
                                   dialect=SQLDialect.OTHER)
    assert result is not None
    assert "Foreign keys are not enabled" in result

def test_foreign_key_constraint(sqlite_connection, create_table):
    """FOREIGN KEY制約が不足している場合のテスト

    TableStructureにFOREIGN KEY制約が含まれているが、
    テーブルにFOREIGN KEY制約が存在しない場合にエラーが発生することを確認する。
    """
    sql1 = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE
    );
    """
    sql2 = """
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        title TEXT NOT NULL,
        content TEXT
    );
    """
    create_table(sql1)
    create_table(sql2)

    expected_sql = """
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        title TEXT NOT NULL,
        content TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id)
    );
    """
    table_structures = parse_sql(expected_sql)
    assert len(table_structures) == 1

    # FOREIGN KEYを有効化
    cursor = sqlite_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    result = check_table_structure(sqlite_connection, table_structures[0])
    assert result is not None
    assert "FOREIGN KEY constraint mismatch" in result
