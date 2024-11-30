"""data_pipeline.parserモジュールのテストコード"""
import pytest
from tomlkit import exceptions as toml_exceptions

from jobcan_di.database.data_pipeline.parser import parse_toml, parse_toml_data, PipelineDefinition
from jobcan_di.database.schema_toolkit import SQLDialect, TableStructure
from jobcan_di.database.data_pipeline._source_result_format import (
    SourceResultFormat, DEFAULT_RESULTS_KEY
)
from jobcan_di.database.data_pipeline._data_source import APIDataSource
from jobcan_di.database.data_pipeline._pipeline_sqlite import SQLiteDataSource
from jobcan_di.database.data_pipeline._db_definition import SQLiteDBDefinition
from jobcan_di.database.data_pipeline._insertion_profile import (
    PositionalInsertionProfile, NamedInsertionProfile, ParameterConversionMethod
)

#
# テストフィクスチャ等 （共通の設定やデータ）
#

@pytest.fixture
def valid_toml_data():
    return """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = [
        '''
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
        ''',
        '''
        CREATE TABLE other_table (
            id INTEGER PRIMARY KEY,
            value REAL NOT NULL
        )
        '''
    ]

    [[data_link.sources]]
    name = "api_source"
    type = "API"
    result_format = "nested-json"
    endpoint = "https://api.example.com/data"
    headers = { "Authorization" = "Bearer token" }
    params = { "limit" = "100" }

    [[data_link.sources]]
    name = "sqlite_source"
    type = "SQLITE"
    result_format = "DB-flat-rows"
    path = "/path/to/source.sqlite"
    query = "SELECT * FROM source_table"

    [data_link.insertion_profile.test_table]
    query = "INSERT INTO test_table (id, name) VALUES (?, ?)"
    source = "sqlite_source"
    positional_parameters = [
        ["id"],
        ["name"]
    ]
    conversion_method = [0, "to-int", 1, "to-string"]

    [data_link.insertion_profile.other_table]
    query = "INSERT INTO other_table (id, value) VALUES (:id, :value)"
    source = "sqlite_source"
    named_parameters = [
        "id", ["id"],
        "value", ["value"]
    ]
    """

@pytest.fixture
def temp_toml_file(tmp_path, valid_toml_data):
    """(一時)TOMLファイルを作成してパスを返す"""
    file_path = tmp_path / "test_config.toml"
    file_path.write_text(valid_toml_data)
    return file_path

#
# 基本的な読み込みのテスト
#

def test_parse_toml(temp_toml_file):
    """TOMLファイルをパースして取得したPipelineDefinitionオブジェクトの属性を検証"""
    result = parse_toml(str(temp_toml_file))
    assert isinstance(result, PipelineDefinition)
    assert isinstance(result.table_definition, SQLiteDBDefinition)

    # Data link > sources
    assert len(result.data_link.sources) == 2
    source0 = result.data_link.sources[0]
    assert isinstance(source0, APIDataSource)
    assert source0.name == "api_source"
    assert source0.result_format == SourceResultFormat.NESTED_JSON
    assert source0.endpoint == "https://api.example.com/data"
    source1 = result.data_link.sources[1]
    assert isinstance(source1, SQLiteDataSource)
    assert source1.name == "sqlite_source"
    assert source1.result_format == SourceResultFormat.DB_FLAT_ROWS
    assert source1.results_key == DEFAULT_RESULTS_KEY
    assert source1.path == "/path/to/source.sqlite"
    assert source1.query == "SELECT * FROM source_table"

    # Data link > Insertion profiles
    assert len(result.data_link.insertion_profiles) == 2
    insertion_profile_tt = result.data_link.insertion_profiles['test_table']
    assert insertion_profile_tt.source == "sqlite_source"
    assert isinstance(insertion_profile_tt, PositionalInsertionProfile)
    assert insertion_profile_tt.conversion_method(0) == ParameterConversionMethod.TO_INT
    assert insertion_profile_tt.conversion_method(1) == ParameterConversionMethod.TO_STRING
    insertion_profile_ot = result.data_link.insertion_profiles['other_table']
    assert isinstance(insertion_profile_ot, NamedInsertionProfile)
    assert insertion_profile_ot.conversion_method('id') is None

def test_parse_toml_data(valid_toml_data):
    """TOMLデータをパースして取得したPipelineDefinitionオブジェクトの属性を検証"""
    result = parse_toml_data(valid_toml_data)
    assert isinstance(result, PipelineDefinition)
    # Similar assertions as in test_parse_toml

def test_invalid_toml_file():
    """存在しないTOMLファイルを指定した場合のエラー処理を検証"""
    with pytest.raises(FileNotFoundError):
        parse_toml("non_existent_file.toml")

def test_invalid_toml_data():
    """不正なTOMLデータを指定した場合のエラー処理を検証"""
    invalid_data = "This is not valid TOML data"
    with pytest.raises(toml_exceptions.TOMLKitError):
        parse_toml_data(invalid_data)

#
# Table Definitionsセクションのテスト
#

def test_missing_table_definitions():
    """table_definitionsセクションが存在しない場合のエラー処理を検証"""
    invalid_data = """
    [data_link]
    # Missing table_definitions section
    """
    with pytest.raises(ValueError, match="Table definition .* not found"):
        parse_toml_data(invalid_data)

def test_missing_data_link():
    """data_linkセクションが存在しない場合のエラー処理を検証"""
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = ["CREATE TABLE test (id INTEGER PRIMARY KEY)"]

    # Missing data_link section
    """
    with pytest.raises(ValueError, match="Data link .* not found"):
        parse_toml_data(invalid_data)

def test_unsupported_sql_dialect():
    """サポートされていないSQL方言を指定した場合のエラー処理を検証"""
    invalid_data = """
    [table_definitions]
    type = "MYSQL"
    # MySQL is not supported
    """
    with pytest.raises(NotImplementedError, match="SQL dialect 'MYSQL' not supported"):
        parse_toml_data(invalid_data)

def test_missing_sqlite_path():
    """SQLiteデータベースのパスが指定されていない場合のエラー処理を検証"""
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    # Missing path
    """
    with pytest.raises(ValueError, match="Path to the SQLite database .* not found"):
        parse_toml_data(invalid_data)

def test_invalid_table_structure():
    """不正なCREATE TABLE文を指定した場合のエラー処理を検証"""
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = [
        "This is not a valid CREATE TABLE statement"
    ]
    """
    with pytest.raises(ValueError):  # Exact error message depends on the SQL parser implementation
        parse_toml_data(invalid_data)

#
# Data Link セクションのテスト
#

#
# Data Link セクションのテスト > Data Sources
#

def test_invalid_data_source_type():
    """不正なデータソースタイプを指定した場合のエラー処理を検証"""
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = ["CREATE TABLE test (id INTEGER PRIMARY KEY)"]

    [[data_link.sources]]
    name = "api_source"
    type = "INVALID_TYPE"
    """
    with pytest.raises(ValueError, match="Source type 'INVALID_TYPE' not supported"):
        parse_toml_data(invalid_data)

def test_unimplemented_data_source_type():
    """未実装のデータソースタイプを指定した場合のエラー処理を検証"""
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = ["CREATE TABLE test (id INTEGER PRIMARY KEY)"]

    [[data_link.sources]]
    name = "api_source"
    type = "OTHER" # API source that is not implemented
    result_type = "JSON"
    result_format = "nested-json"
    """
    with pytest.raises(NotImplementedError, match="Data source type 'OTHER' not implemented"):
        parse_toml_data(invalid_data)

def test_missing_result_format():
    """結果フォーマットが指定されていない場合のエラー処理を検証"""
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = ["CREATE TABLE test (id INTEGER PRIMARY KEY)"]

    [[data_link.sources]]
    name = "api_source"
    type = "API"
    result_type = "JSON"
    # Missing result_format
    """
    with pytest.raises(ValueError, match="Result format of .+ not found"):
        parse_toml_data(invalid_data)

def test_invalid_result_format():
    """不正な結果フォーマットを指定した場合のエラー処理を検証"""
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = ["CREATE TABLE test (id INTEGER PRIMARY KEY)"]

    [[data_link.sources]]
    name = "api_source"
    type = "API"
    result_type = "JSON"
    result_format = "INVALID_FORMAT"
    """
    with pytest.raises(ValueError, match="Result format 'INVALID_FORMAT' not supported"):
        parse_toml_data(invalid_data)

#
# Data Link セクションのテスト > Data Sources > API固有
#

def test_missing_api_endpoint():
    """APIエンドポイントが指定されていない場合のエラー処理を検証"""
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = ["CREATE TABLE test (id INTEGER PRIMARY KEY)"]

    [[data_link.sources]]
    name = "api_source"
    type = "API"
    result_type = "JSON"
    result_format = "nested-json"
    # Missing endpoint
    """
    with pytest.raises(ValueError, match="API endpoint not found"):
        parse_toml_data(invalid_data)

#
# Data Link セクションのテスト > Data Sources > SQLite固有
#

def test_missing_sqlite_path_in_data_source():
    """SQLiteデータソースのパスが指定されていない場合のエラー処理を検証"""
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = ["CREATE TABLE test (id INTEGER PRIMARY KEY)"]

    [[data_link.sources]]
    name = "sqlite_source"
    type = "SQLITE"
    result_type = "JSON"
    result_format = "json-object-results"
    # Missing path
    """
    with pytest.raises(ValueError, match="Path to the SQLite database .*not found"):
        parse_toml_data(invalid_data)

def test_missing_sqlite_query_in_data_source():
    """SQLiteデータソースのクエリが指定されていない場合のエラー処理を検証"""
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = ["CREATE TABLE test (id INTEGER PRIMARY KEY)"]

    [[data_link.sources]]
    name = "sqlite_source"
    type = "SQLITE"
    result_type = "JSON"
    result_format = "json-object-results"
    path = "/path/to/source.sqlite"
    # Missing query
    """
    with pytest.raises(ValueError, match="SQL query not found"):
        parse_toml_data(invalid_data)

#
# Data Link セクションのテスト > Insertion Profiles
#

def test_invalid_insertion_profile():
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = ["CREATE TABLE test (id INTEGER PRIMARY KEY)"]

    [[data_link.sources]]
    name = "api_source"
    type = "API"
    result_type = "JSON"
    result_format = "nested-json"
    endpoint = "https://api.example.com/data"

    [data_link.insertion_profile.test]
    # Missing query
    """
    with pytest.raises(ValueError, match="SQL query not found"):
        parse_toml_data(invalid_data)

def test_invalid_parameter_conversion_method():
    invalid_data = """
    [table_definitions]
    type = "SQLITE"
    path = "/path/to/db.sqlite"
    tables = ["CREATE TABLE test (id INTEGER PRIMARY KEY)"]

    [[data_link.sources]]
    name = "api_source"
    type = "API"
    result_type = "JSON"
    result_format = "nested-json"
    endpoint = "https://api.example.com/data"

    [data_link.insertion_profile.test]
    query = "INSERT INTO test (id) VALUES (?)"
    source = "api_source"
    positional_parameters = [["$.id"]]
    conversion_method = [0, "INVALID_METHOD"]
    """
    with pytest.raises(ValueError, match="Invalid conversion method"):
        parse_toml_data(invalid_data)
