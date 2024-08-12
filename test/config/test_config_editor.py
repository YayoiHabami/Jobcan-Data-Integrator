import pytest

from config.config_editor import ConfigEditor, RangeType

@pytest.fixture
def config() -> ConfigEditor:
    config_editor = ConfigEditor("test/data/simple_config.ini")
    return config_editor

# 正しいファイルを指定した場合の読み込みテスト
def test_load_valid_file():
    config_editor = ConfigEditor()
    config_editor.load("test/data/simple_config.ini")
    assert config_editor.is_loaded() is True

# 正しくないファイル/ディレクトリを指定した場合の読み込みテスト
def test_load_invalid_file():
    # ファイルを指定した場合の読み込みテスト
    config_editor = ConfigEditor()
    config_editor.load("invalid_file")
    assert config_editor.is_loaded() is False

    # ディレクトリを指定した場合の読み込みテスト
    config_editor.load("test/data")
    assert config_editor.is_loaded() is False

# 各セクションへのコメントの取得テスト
def test_load_section_comments(config):
    comments = {
        "SECTION1": {
            "description": [" セクション1のコメント1"],
            "tags": {"icon": "api"}
        },
        "SECTION2": {
            "description": [],
            "tags": {}
        }
    }
    assert config["SECTION1"].description == comments["SECTION1"]["description"]
    assert config["SECTION1"].tags == comments["SECTION1"]["tags"]

    assert config["SECTION2"].description == comments["SECTION2"]["description"]
    assert config["SECTION2"].tags == comments["SECTION2"]["tags"]

# 各キーへのコメントの取得テスト
def test_load_variable_comments(config):
    comments = {
        "SECTION1": {
            "VAR_1": {
                "description": [" 変数1のコメント1", " 変数1のコメント2"],
                "tags": {"tag1": "value1", "tag2":0}
            },
            "VAR_2": {
                "description": [" 変数2のコメント1", " 変数2のコメント2"],
                "tags": {}
            }
        },
        "SECTION2": {
            "VAR_3": {
                "description": [" 変数3のコメント1"],
                "tags": {}
            }
        }
    }
    assert config["SECTION1"]["VAR_1"].description == comments["SECTION1"]["VAR_1"]["description"]
    assert config["SECTION1"]["VAR_1"].tags == comments["SECTION1"]["VAR_1"]["tags"]

    assert config["SECTION1"]["VAR_2"].description == comments["SECTION1"]["VAR_2"]["description"]
    assert config["SECTION1"]["VAR_2"].tags == comments["SECTION1"]["VAR_2"]["tags"]

    assert config["SECTION2"]["VAR_3"].description == comments["SECTION2"]["VAR_3"]["description"]
    assert config["SECTION2"]["VAR_3"].tags == comments["SECTION2"]["VAR_3"]["tags"]

# コメントによる型ヒントの取得テスト
def test_load_variable_type_hint(config):
    assert config["SECTION1"]["VAR_1"].type == str
    assert config["SECTION1"]["VAR_2"].type == int
    assert config["SECTION2"]["VAR_3"].type == float
    assert config["SECTION2"]["VAR_4"].type == bool

# コメントによるデフォルト値の取得テスト
def test_load_variable_default_value(config):
    assert config["SECTION1"]["VAR_1"].default == None
    assert config["SECTION1"]["VAR_2"].default == 10
    assert config["SECTION2"]["VAR_3"].default == 10.0
    assert config["SECTION2"]["VAR_4"].default == None

# コメントによる範囲の取得テスト
def test_load_variable_range(config):
    assert config["SECTION1"]["VAR_1"].range_type == RangeType.NONE
    assert config["SECTION1"]["VAR_2"].range_type == RangeType.LIST_NE_E
    assert config["SECTION2"]["VAR_3"].range_type == RangeType.LIST_NE_NE
    assert config["SECTION2"]["VAR_4"].range_type == RangeType.SET

# コメントによる範囲の取得テスト
def test_load_variable_range_value(config):
    assert config["SECTION1"]["VAR_1"].range == []
    assert config["SECTION1"]["VAR_2"].range == [0, 100]
    assert config["SECTION2"]["VAR_3"].range == [0, float("inf")]
    assert config["SECTION2"]["VAR_4"].range == [False, True]
