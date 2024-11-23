"""テーブル定義を解析するモジュールのテスト

Notes:
- 本テストはSQLiteを前提としたコードであり、他言語との以下の違いに注意すること
  - `PRIMARY KEY` が有効なカラムに対して、自動的に `NOT NULL` 制約は付与されない
"""
from typing import Any, Optional
import pytest

from jobcan_di.database.schema_toolkit import TableStructure
from jobcan_di.database.schema_toolkit.sql_parser import parse_sql, get_create_table_clauses



#
# 基礎のパーサーのテスト
#

@pytest.mark.parametrize("sql, expected", [
    # 基本的なCREATE TABLE文のテスト
    (
        "CREATE TABLE users (id INT, name VARCHAR(255));",
        ["CREATE TABLE users (id INT, name VARCHAR(255));"]
    ),
    # 複数のCREATE TABLE文を含むSQLのテスト
    (
        "CREATE TABLE users (id INT, name VARCHAR(255)); "\
            "CREATE TABLE posts (id INT, title VARCHAR(255));",
        ["CREATE TABLE users (id INT, name VARCHAR(255));",
         "CREATE TABLE posts (id INT, title VARCHAR(255));"]
    ),
    # IF NOT EXISTS句を含むCREATE TABLE文のテスト
    (
        "CREATE TABLE IF NOT EXISTS users (id INT, name VARCHAR(255));",
        ["CREATE TABLE IF NOT EXISTS users (id INT, name VARCHAR(255));"]
    ),
    # 文字列リテラルを含むCREATE TABLE文のテスト
    (
        "CREATE TABLE users (id INT, name VARCHAR(255), " \
            "description TEXT DEFAULT 'No description');",
        ["CREATE TABLE users (id INT, name VARCHAR(255), " \
         "description TEXT DEFAULT 'No description');"]
    ),
    # CREATE TABLE文以外のSQL文を含む場合のテスト
    (
        "SELECT * FROM users; CREATE TABLE posts (id INT, title VARCHAR(255));",
        ["CREATE TABLE posts (id INT, title VARCHAR(255));"]
    ),
    # 空の入力文字列のテスト
    (
        "",
        []
    ),
])
def test_ct_get_create_table_clauses(sql, expected) -> None:
    """
    get_create_table_clauses関数の基本的な動作をテストする。

    様々なSQL文のパターンに対して、関数が期待通りの結果を返すかを確認する。
    テストケースには以下が含まれる：
    - 単一のCREATE TABLE文
    - 複数のCREATE TABLE文
    - IF NOT EXISTS句を含むCREATE TABLE文
    - 文字列リテラルを含むCREATE TABLE文
    - CREATE TABLE文以外のSQL文を含む場合
    - 空の入力文字列
    """
    assert get_create_table_clauses(sql) == expected

def test_ct_case_insensitivity() -> None:
    """
    CREATE TABLE句の大文字小文字の区別がないことをテストする。

    関数がCREATE TABLE句を大文字小文字を区別せずに正しく識別できることを確認する。
    """
    sql = "create table users (id INT, name VARCHAR(255));"
    expected = ["create table users (id INT, name VARCHAR(255));"]
    assert get_create_table_clauses(sql) == expected

def test_ct_nested_parentheses() -> None:
    """
    ネストされた括弧を含むCREATE TABLE文を正しく処理できることをテストする。

    関数が複雑な構造を持つCREATE TABLE文を正しく解析できることを確認する。
    """
    sql = "CREATE TABLE complex (id INT, data JSON CHECK (JSON_VALID(data)));"
    expected = ["CREATE TABLE complex (id INT, data JSON CHECK (JSON_VALID(data)));"]
    assert get_create_table_clauses(sql) == expected

def test_ct_multiple_string_delimiters() -> None:
    """
    異なる文字列デリミタ（シングルクォートとダブルクォート）を含むSQL文を正しく処理できることをテストする。

    関数が異なる種類の文字列リテラルを正しく認識し、処理できることを確認する。
    """
    sql = "CREATE TABLE users (name VARCHAR(255) DEFAULT 'John', " \
          "quote TEXT DEFAULT \"It's a quote\");"
    expected = ["CREATE TABLE users (name VARCHAR(255) DEFAULT 'John', " \
                "quote TEXT DEFAULT \"It's a quote\");"]
    assert get_create_table_clauses(sql) == expected

def test_ct_error_handling() -> None:
    """
    不完全なSQL文に対するエラー処理をテストする。

    関数が不完全なSQL文（閉じられていない括弧など）に対して適切に動作することを確認する。
    この場合、関数は空のリストを返すべきである。
    """
    sql = "CREATE TABLE users (id INT, name VARCHAR(255);"  # 閉じ括弧が欠けている
    assert get_create_table_clauses(sql) == []

def test_ct_whitespace_handling() -> None:
    """
    様々な空白文字の扱いをテストする。

    関数が異なる種類の空白文字（スペース、タブ、改行）を含むSQL文を正しく処理できることを確認する。
    """
    sql = """
    CREATE TABLE
        users (
            id INT,
            name VARCHAR(255)
        );
    """
    expected = ["""CREATE TABLE
        users (
            id INT,
            name VARCHAR(255)
        );"""]
    assert get_create_table_clauses(sql) == expected

#
# SQL文解析のテスト
#

def assert_column(
    table: TableStructure, column_name: str, ttype: str, not_null: bool,
    autoincrement: bool, default: Any,
    foreign_key: Optional[tuple[str, str]] = None,
    unique_keys: Optional[list[list[str]]] = None,
    primary_keys: Optional[list[str]] = None
    ) -> None:
    """Check if a column in a table has the expected properties."""
    column = next((c for c in table.columns if c.name == column_name), None)
    assert column is not None

    assert column.ttype == ttype
    assert column.not_null == not_null
    assert column.autoincrement == autoincrement
    assert column.default == default
    assert column.foreign_key == foreign_key

    if unique_keys is not None:
        assert any(column_name in uk for uk in table.unique_keys)

    if primary_keys is not None:
        assert column_name in table.primary_keys

def test_parse_sql_basic() -> None:
    """基本的なSQL文を解析するテスト

    テスト内容:
    - テーブル名が正しいこと
    - カラム数が正しいこと
    - カラムのプロパティが正しいこと
    """
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL
    );
    """
    tables = parse_sql(sql)
    assert len(tables) == 1
    assert tables[0].name == "users"
    assert len(tables[0].columns) == 3

    assert_column(tables[0], "id", "INTEGER", False, True, None,
                  primary_keys=["id"])
    assert_column(tables[0], "username", "TEXT", True, False, None,
                  unique_keys=[["username"]])
    assert_column(tables[0], "email", "TEXT", True, False, None)

def test_parse_sql_multiple_tables() -> None:
    """複数のテーブルを含むSQL文を解析するテスト

    テスト内容:
    - テーブルの数が正しいこと
    - 各テーブルのカラム数が正しいこと
    - 各テーブルのカラムのプロパティが正しいこと
    """
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL
    );
    CREATE TABLE posts (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        content TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """
    tables = parse_sql(sql)
    assert len(tables) == 2
    assert tables[0].name == "users"
    assert tables[1].name == "posts"
    assert_column(tables[1], "user_id", "INTEGER", False, False, None,
                  foreign_key=("users", "id"))

def test_parse_sql_default_values() -> None:
    """デフォルト値を含むSQL文を解析するテスト

    テスト内容:
    - デフォルト値が正しいこと
    """
    sql = """
    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL DEFAULT 0.0,
        in_stock BOOLEAN DEFAULT TRUE,
        added_at DATE DEFAULT CURRENT_DATE
    );
    """
    tables = parse_sql(sql)
    assert len(tables) == 1
    assert_column(tables[0], "price", "REAL", False, False, "0.0")
    assert_column(tables[0], "in_stock", "BOOLEAN", False, False, "TRUE")
    assert_column(tables[0], "added_at", "DATE", False, False, "CURRENT_DATE")

def test_parse_sql_with_default_with_semicolon() -> None:
    """セミコロンを含むデフォルト値を持つSQL文を解析するテスト

    デフォルト値にセミコロンを含む場合の解析を確認する。
    """
    sql = """
    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL DEFAULT '0.0;',
        description TEXT DEFAULT 'No description;'
    );
    """
    tables = parse_sql(sql)
    assert len(tables) == 1
    assert_column(tables[0], "price", "REAL", False, False, "'0.0;'")
    assert_column(tables[0], "description", "TEXT", False, False, "'No description;'")

def test_parse_sql_with_default_with_comma() -> None:
    """カンマを含むデフォルト値を持つSQL文を解析するテスト

    デフォルト値にカンマを含む場合の解析を確認する。
    """
    sql = """
    CREATE TABLE products (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL DEFAULT '0,0',
        description TEXT DEFAULT 'No, description'
    );
    """
    tables = parse_sql(sql)
    assert len(tables) == 1
    assert_column(tables[0], "price", "REAL", False, False, "'0,0'")
    assert_column(tables[0], "description", "TEXT", False, False, "'No, description'")

def test_parse_sql_composite_primary_key() -> None:
    """複合主キーを含むSQL文を解析するテスト

    テスト内容:
    - 複合主キーが正しいこと
    """
    sql = """
    CREATE TABLE orders (
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        PRIMARY KEY (order_id, product_id)
    );
    """
    tables = parse_sql(sql)
    assert len(tables) == 1
    assert tables[0].primary_keys == ["order_id", "product_id"]

def test_parse_sql_unique_constraint() -> None:
    """UNIQUE制約を含むSQL文を解析するテスト

    テスト内容:
    - UNIQUE制約が正しいこと
    - 複合/単一のUNIQUE制約がともに正しいこと
    """
    sql = """
    CREATE TABLE employees (
        id INTEGER PRIMARY KEY,
        email TEXT,
        phone TEXT,
        UNIQUE (email, phone),
        UNIQUE (phone)
    );
    """
    tables = parse_sql(sql)
    assert len(tables) == 1
    assert ["email", "phone"] in tables[0].unique_keys
    assert ["phone"] in tables[0].unique_keys

def test_parse_sql_multiple_foreign_keys() -> None:
    """複数の外部キーを含むSQL文を解析するテスト

    テスト内容:
    - 外部キーが正しいこと
    """
    sql = """
    CREATE TABLE orders (
        id INTEGER PRIMARY KEY,
        customer_id INTEGER,
        product_id INTEGER,
        FOREIGN KEY (customer_id) REFERENCES customers(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    );
    """
    tables = parse_sql(sql)
    assert len(tables) == 1
    assert_column(tables[0], "customer_id", "INTEGER", False, False, None,
                  foreign_key=("customers", "id"))
    assert_column(tables[0], "product_id", "INTEGER", False, False, None,
                  foreign_key=("products", "id"))

def test_parse_sql_case_insensitivity() -> None:
    """大文字小文字を区別しないSQL文を解析するテスト

    テスト内容:
    - 大文字小文字を区別せずに解析できること
    """
    sql = """
    create TABLE mixed_case (
        ID integer PRIMARY key,
        Name TEXT not NULL,
        Value REAL default 0.0
    );
    """
    tables = parse_sql(sql)
    assert len(tables) == 1
    assert tables[0].name == "mixed_case"
    assert_column(tables[0], "ID", "INTEGER", False, False, None, primary_keys=["ID"])
    assert_column(tables[0], "Name", "TEXT", True, False, None)
    assert_column(tables[0], "Value", "REAL", False, False, "0.0")

def test_parse_sql_empty_input() -> None:
    """空のSQL文を解析するテスト

    テスト内容:
    - 空のリストが返されること
    """
    sql = ""
    tables = parse_sql(sql)
    assert len(tables) == 0

def test_parse_sql_invalid_input() -> None:
    """不正なSQL文を解析するテスト

    テスト内容:
    - 空のリストが返されること
    """
    sql = "This is not a valid SQL statement;"
    tables = parse_sql(sql)
    assert len(tables) == 0

def test_parse_sql_complex_schema() -> None:
    """複雑なスキーマを含むSQL文を解析するテスト

    テスト内容:
    - 複数のテーブルが正しく解析されること
    - 各テーブルのカラム数が正しいこと
    - 各テーブルのカラムのプロパティが正しいこと
    """
    sql = """
    CREATE TABLE departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        hire_date DATE NOT NULL DEFAULT CURRENT_DATE,
        department_id INTEGER,
        salary REAL NOT NULL DEFAULT 0.0,
        FOREIGN KEY (department_id) REFERENCES departments(id)
    );

    CREATE TABLE projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        name TEXT NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE,
        budget REAL NOT NULL DEFAULT 0.0,
        UNIQUE (name, start_date)
    );

    CREATE TABLE employee_projects (
        employee_id INTEGER,
        project_id INTEGER,
        role TEXT NOT NULL,
        PRIMARY KEY (employee_id, project_id),
        FOREIGN KEY (employee_id) REFERENCES employees(id),
        FOREIGN KEY (project_id) REFERENCES projects(id)
    );
    """
    tables = parse_sql(sql)
    assert len(tables) == 4

    # Check departments table
    departments = next(t for t in tables if t.name == "departments")
    assert_column(departments, "id", "INTEGER", False, True, None, primary_keys=["id"])
    assert_column(departments, "name", "TEXT", True, False, None, unique_keys=[["name"]])

    # Check employees table
    employees = next(t for t in tables if t.name == "employees")
    assert_column(employees, "id", "INTEGER", False, True, None, primary_keys=["id"])
    assert_column(employees, "email", "TEXT", True, False, None, unique_keys=[["email"]])
    assert_column(employees, "hire_date", "DATE", True, False, "CURRENT_DATE")
    assert_column(employees, "department_id", "INTEGER", False, False, None,
                  foreign_key=("departments", "id"))
    assert_column(employees, "salary", "REAL", True, False, "0.0")

    # Check projects table
    projects = next(t for t in tables if t.name == "projects")
    assert_column(projects, "id", "INTEGER", True, True, None, primary_keys=["id"])
    assert_column(projects, "budget", "REAL", True, False, "0.0")
    assert ["name", "start_date"] in projects.unique_keys

    # Check employee_projects table
    employee_projects = next(t for t in tables if t.name == "employee_projects")
    assert employee_projects.primary_keys == ["employee_id", "project_id"]
    assert_column(employee_projects, "employee_id", "INTEGER", False, False, None,
                  foreign_key=("employees", "id"))
    assert_column(employee_projects, "project_id", "INTEGER", False, False, None,
                  foreign_key=("projects", "id"))
    assert_column(employee_projects, "role", "TEXT", True, False, None)

def test_parse_sql_with_table_options() -> None:
    """テーブルオプションを含むSQL文を解析するテスト

    SQLiteの `WITHOUT ROWID` オプションを含むSQL文を解析する。
    """
    # SQLiteの `WITHOUT ROWID` オプション
    sql = """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE
    ) WITHOUT ROWID;
    """
    tables = parse_sql(sql)
    assert len(tables) == 1
    assert tables[0].name == "users"
    assert len(tables[0].columns) == 2
    assert_column(tables[0], "id", "INTEGER", False, True, None,
                  primary_keys=["id"])
    assert_column(tables[0], "username", "TEXT", True, False, None,
                  unique_keys=[["username"]])
