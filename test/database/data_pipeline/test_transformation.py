"""データ変換モジュールのテストコード (ETLのTransform部分)"""
from copy import deepcopy
from typing import Any, Final

import pytest

from jobcan_di.database.data_pipeline import ParameterConversionMethod
from jobcan_di.database.data_pipeline.transformation import (
    ErrorHandlingOptions, recursive_get, get_indices,
    transform_named_data, transform_positional_data,
    convert_data_type
)



#
# recursive_get
#

# Test data
test_data = {
    "user": {"name": "John", "age": 30},
    "groups": [
        {"name": "Group 1", "members": ["Alice", "Bob"]},
        {"name": "Group 2", "members": ["Charlie", "David"]}
    ],
    "settings": {
        "theme": "dark",
        "notifications": True,
        "nested": {
            "key": "value"
        }
    },
    "tags": ["python", "testing", "recursion"]
}

def test_basic_dictionary_access():
    """辞書のみで構成されたデータに対して、正しいキーを指定してアクセスできることを確認する"""
    assert recursive_get(test_data, ["user", "name"]) == "John"
    assert recursive_get(test_data, ["user", "age"]) == 30
    assert recursive_get(test_data, ["settings", "nested", "key"]) == "value"

def test_basic_list_access():
    """辞書とリストから構成されたデータに対して、正しいキーを指定してアクセスできることを確認する"""
    assert recursive_get(test_data, ["groups", 0, "name"]) == "Group 1"
    assert recursive_get(test_data, ["groups", 1, "members", 0]) == "Charlie"

def test_negative_list_indices():
    """リストに対し負数を指定した場合に、戻り値がリストになることを確認する"""
    assert recursive_get(test_data, ["groups", -1, "name"]) == ["Group 1", "Group 2"]
    assert recursive_get(test_data, ["tags", -1]) == ["python", "testing", "recursion"]

    # 負数であればどの数値であっても同じ結果が返ることを確認
    assert recursive_get(test_data, ["groups", -2, "name"]) == ["Group 1", "Group 2"]
    assert recursive_get(test_data, ["tags", -100]) == ["python", "testing", "recursion"]

    # 複数の負数インデックスを指定した場合、多重リストになることを確認
    assert recursive_get(
        test_data, ["groups", -1, "members", -1]
    ) == [["Alice", "Bob"], ["Charlie", "David"]]

def test_non_existing_key():
    """存在しないキーを指定した場合に、Noneを返すことを確認する

    また、エラーハンドリングオプションを指定した場合に、例外を発生させることを確認する"""
    assert recursive_get(test_data, ["user", "email"]) is None

    with pytest.raises(KeyError):
        recursive_get(test_data, ["user", "email"],
                      error_handling=ErrorHandlingOptions.NON_EXISTING_DICT_KEY
                     )

def test_non_string_dict_key():
    """辞書のキーに文字列以外を指定した場合に、TypeErrorを発生させることを確認する

    また、エラーハンドリングオプションを指定した場合に、例外を発生させることを確認する"""
    with pytest.raises(TypeError):
        recursive_get(test_data, ["user", 123],
                      error_handling=ErrorHandlingOptions.NON_STRING_DICT_KEY)

    assert recursive_get(test_data, ["user", 123],
                         error_handling=ErrorHandlingOptions.NONE) is None

def test_non_integer_list_index():
    """リストのインデックスに整数以外を指定した場合に、TypeErrorを発生させることを確認する

    また、エラーハンドリングオプションを指定した場合に、例外を発生させることを確認する"""
    with pytest.raises(TypeError):
        recursive_get(test_data, ["groups", "invalid"],
                      error_handling=ErrorHandlingOptions.NON_INTEGER_LIST_INDEX)

    assert recursive_get(test_data, ["groups", 0, "invalid"],
                         error_handling=ErrorHandlingOptions.NONE) is None

def test_list_index_out_of_range():
    """リストのインデックスが範囲外の場合に、IndexErrorを発生させることを確認する

    また、エラーハンドリングオプションを指定した場合に、例外を発生させることを確認する"""
    with pytest.raises(IndexError):
        recursive_get(test_data, ["groups", 5],
                      error_handling=ErrorHandlingOptions.LIST_INDEX_OUT_OF_RANGE)

    assert recursive_get(test_data, ["groups", 5],
                         error_handling=ErrorHandlingOptions.NONE) is None

def test_nested_access_on_non_container():
    """コンテナでないオブジェクトに対してネストされたアクセスを行った場合に、TypeErrorを発生させることを確認する

    また、エラーハンドリングオプションを指定した場合に、例外を発生させることを確認する"""
    with pytest.raises(TypeError):
        recursive_get(test_data, ["user", "name", "invalid"],
                      error_handling=ErrorHandlingOptions.NESTED_ACCESS_ON_NON_CONTAINER)

    assert recursive_get(test_data, ["user", "name", "invalid"],
                         error_handling=ErrorHandlingOptions.NONE) is None

def test_empty_keys():
    """空のキーを指定した場合に、元のデータが返ることを確認する"""
    assert recursive_get(test_data, []) == test_data

def test_none_data():
    """Noneを指定した場合に、Noneが返ることを確認する"""
    with pytest.raises(TypeError):
        recursive_get(None, ["key"],
                      error_handling=ErrorHandlingOptions.NESTED_ACCESS_ON_NON_CONTAINER)

    assert recursive_get(None, ["key"],
                         error_handling=ErrorHandlingOptions.NONE) is None

def test_multiple_error_handling_options():
    """複数のエラーハンドリングオプションを指定した場合に、
    それぞれのエラーに対して例外を発生させることを確認する"""
    error_handling = ErrorHandlingOptions.NON_STRING_DICT_KEY | \
                     ErrorHandlingOptions.LIST_INDEX_OUT_OF_RANGE

    with pytest.raises(TypeError):
        recursive_get(test_data, ["user", 123], error_handling=error_handling)

    with pytest.raises(IndexError):
        recursive_get(test_data, ["groups", 5], error_handling=error_handling)

    assert recursive_get(test_data, ["groups", 0, "invalid"], error_handling=error_handling) is None

def test_default_error_handling():
    """デフォルトのエラーハンドリングオプションを指定した場合に、例外を発生させることを確認する"""
    with pytest.raises(TypeError):
        recursive_get(test_data, ["user", 123])

    with pytest.raises(TypeError):
        recursive_get(test_data, ["groups", "invalid"])

    with pytest.raises(IndexError):
        recursive_get(test_data, ["groups", 5])

    with pytest.raises(TypeError):
        recursive_get(test_data, ["user", "name", "invalid"])

    assert recursive_get(test_data, ["user", "email"]) is None

def test_all_error_handling_disabled():
    """全てのエラーハンドリングオプションを無効にした場合に、Noneを返すことを確認する"""
    error_handling = ErrorHandlingOptions.NONE
    assert recursive_get(test_data, ["user", 123], error_handling=error_handling) is None
    assert recursive_get(test_data, ["groups", 0, "invalid"],
                         error_handling=error_handling) is None
    assert recursive_get(test_data, ["groups", 5], error_handling=error_handling) is None
    assert recursive_get(test_data, ["user", "name", "invalid"],
                         error_handling=error_handling) is None
    assert recursive_get(test_data, ["user", "email"], error_handling=error_handling) is None

#
# get_indices
#

@pytest.mark.parametrize("data, value, expected", [
    ([1, 2, 3, 2, 4, 2], 2, [1, 3, 5]), # 2が3つ含まれている
    ([1, 2, 3, 4, 5], 6, []),           # 6は含まれていない
    (["a", "b", "c", "b", "d"], "b", [1, 3]), # 文字列の場合
    ([1.1, 2.2, 3.3, 2.2, 4.4], 2.2, [1, 3]), # 浮動小数点数の場合
    ([], 1, []),                              # 空のリストの場合は空のリストを返す
    ([1, 1, 1, 1], 1, [0, 1, 2, 3]),          # 全ての要素が同じ場合
    ([None, 1, None, 2, None], None, [0, 2, 4]), # Noneが含まれている場合
    ([42], 42, [0]),                             # 要素が1つだけのリスト
    (["42"], 42, []),                            # 異なる型の要素を持つリスト
    ([1, "2", 3, "2", 5], "2", [1, 3]),          # 異なる型の要素を持つリスト
    (list(range(10000)) + [42] + list(range(10000, 20000)) + [42],
     42, [42, 10000, 20001])                     # 大きなリスト
])
def test_get_indices(data: list[Any], value: Any, expected: list[int]):
    """リストから指定した値のインデックスを取得できることを確認する"""
    assert get_indices(data, value) == expected

#
# transform_named_data / transform_positional_data
#

SAMPLE_DATA: Final = {
    "user_api": [
        {
            "user_code": "foo",
            "last_name": "Doe",
            "first_name": "John",
            "user_positions": [
                {"position_code": "manager", "group_code": "100"},
                {"position_code": "officer", "group_code": "200"}
            ],
            "extra_items": [{"key": "value1"}, {"key": "value2"}]
        },
        {
            "user_code": "bar",
            "last_name": "Smith",
            "first_name": "Jane",
            "user_positions": [
                {"position_code": "manager", "group_code": "200"}
            ],
            "extra_items": [{"key": "value3"}]
        }
    ]
}

NAMED_PARAMETERS: Final = {
    "user_code": ["user_code"],
    "position_code": ["user_positions", -1, "position_code"],
    "group_code": ["user_positions", -1, "group_code"],
    "extra_key": ["extra_items", -1, "key"]
}

POSITIONAL_PARAMETERS: Final = [
    ["user_code"],
    ["user_positions", -1, "position_code"],
    ["user_positions", -1, "group_code"],
    ["extra_items", -1, "key"]
]

def test_transform_named_data_success():
    """名前付きパラメータを使用してデータを変換できることを確認する"""
    result = transform_named_data(SAMPLE_DATA, "user_api", NAMED_PARAMETERS)
    assert len(result) == 5
    assert result[0] == {"user_code": "foo", "position_code": "manager",
                         "group_code": "100", "extra_key": "value1"}
    assert result[-1] == {"user_code": "bar", "position_code": "manager",
                          "group_code": "200", "extra_key": "value3"}

def test_transform_positional_data_success():
    """位置パラメータを使用してデータを変換できることを確認する"""
    result = transform_positional_data(SAMPLE_DATA, "user_api", POSITIONAL_PARAMETERS)
    assert len(result) == 5
    assert result[0] == ("foo", "manager", "100", "value1")
    assert result[-1] == ("bar", "manager", "200", "value3")

def test_transform_named_data_missing_key():
    """存在しないキー/インデックスを指定した場合のエラーハンドリングを確認する"""
    # 辞書に対して存在しないキーを指定した場合、Noneが返ることを確認する
    _named_parameters = deepcopy(NAMED_PARAMETERS)
    _named_parameters["non_existent"] = ["non_existent_key"]
    res = transform_named_data(SAMPLE_DATA, "user_api", _named_parameters)
    assert len(res) == 5
    assert res[0]["non_existent"] is None

    # リストに対して存在しないインデックスを指定した場合、IndexErrorが発生することを確認する
    _named_parameters["position_code"] = ["user_positions", 10, "position_code"]
    with pytest.raises(IndexError):
        transform_named_data(SAMPLE_DATA, "user_api", _named_parameters)

def test_transform_positional_data_missing_key():
    """存在しないキー/インデックスを指定した場合のエラーハンドリングを確認する"""
    # 辞書に対して存在しないキーを指定した場合、Noneが返ることを確認する
    _positional_parameters = deepcopy(POSITIONAL_PARAMETERS)
    _positional_parameters.append(["non_existent_key"])
    res = transform_positional_data(SAMPLE_DATA, "user_api", _positional_parameters)
    assert len(res) == 5
    assert res[0][-1] is None

    # リストに対して存在しないインデックスを指定した場合、IndexErrorが発生することを確認する
    _positional_parameters[-1] = ["user_positions", 10, "position_code"]
    with pytest.raises(IndexError):
        transform_positional_data(SAMPLE_DATA, "user_api", _positional_parameters)

def test_transform_named_data_invalid_source():
    """存在しないソースを指定した場合に、空のリストが返ることを確認する"""
    assert transform_named_data(SAMPLE_DATA, "invalid_source", NAMED_PARAMETERS) == []

    assert transform_positional_data(SAMPLE_DATA, "invalid_source", POSITIONAL_PARAMETERS) == []

def test_transform_named_data_empty_data():
    """空のデータを指定した場合に、空のリストが返ることを確認する"""
    assert transform_named_data({}, "user_api", {}) == []

    assert transform_positional_data({}, "user_api", []) == []

def test_transform_named_data_nested_list():
    """ネストされたリストを指定した場合に、正しくデータを変換できることを確認する"""
    _named_parameters = deepcopy(NAMED_PARAMETERS)
    _named_parameters["nested"] = ["user_positions", -1, "position_code"]
    result = transform_named_data(SAMPLE_DATA, "user_api", _named_parameters)
    assert len(result) == 5
    assert result[0]["nested"] == "manager"
    assert result[1]["nested"] == "manager"
    assert result[2]["nested"] == "officer"

def test_transform_positional_data_nested_list():
    """ネストされたリストを指定した場合に、正しくデータを変換できることを確認する"""
    _positional_parameters = deepcopy(POSITIONAL_PARAMETERS)
    _positional_parameters.append(["user_positions", -1, "position_code"])
    result = transform_positional_data(SAMPLE_DATA, "user_api", _positional_parameters)
    assert len(result) == 5
    assert result[0][4] == "manager"
    assert result[1][4] == "manager"
    assert result[2][4] == "officer"

def test_nested_aggregate_keys():
    """2重にネストされたリストを指定した場合に、正しくデータを変換できることを確認する"""
    _sample_data = deepcopy(SAMPLE_DATA)
    _sample_data["user_api"][0]["user_positions"][0]["nested"] = [{"key": "value1"},
                                                                  {"key": "value2"}]
    _sample_data["user_api"][0]["user_positions"][1]["nested"] = [{"key": "value3"},
                                                                  {"key": "value4"}]
    _sample_data["user_api"][1]["user_positions"][0]["nested"] = [{"key": "value5"},
                                                                  {"key": "value6"}]
    _named_parameters = {
        "user_code": ["user_code"],
        "position_code": ["user_positions", -1, "position_code"],
        "group_code": ["user_positions", -1, "group_code"],
        "nested": ["user_positions", -1, "nested", -1, "key"]  # 2重にネストされたリスト
    }
    result = transform_named_data(_sample_data, "user_api", _named_parameters)
    assert len(result) == 6
    assert result[0] == {"user_code": "foo", "position_code": "manager",
                         "group_code": "100", "nested": "value1"}
    assert result[1] == {"user_code": "foo", "position_code": "manager",
                         "group_code": "100", "nested": "value2"}
    assert result[2] == {"user_code": "foo", "position_code": "officer",
                         "group_code": "200", "nested": "value3"}
    assert result[-2] == {"user_code": "bar", "position_code": "manager",
                          "group_code": "200", "nested": "value5"}
    assert result[-1] == {"user_code": "bar", "position_code": "manager",
                          "group_code": "200", "nested": "value6"}

#
# convert_data_type
#

PCM = ParameterConversionMethod
@pytest.mark.parametrize("description, data, method, expected", [
    (   "基本パターン1: 整数、浮動小数点数、真偽値、文字列の変換",
        [{"a": "1", "b": "2.5", "c": "true", "d": "hello"}],
        {"a": PCM.TO_INT, "b": PCM.TO_FLOAT, "c": PCM.TO_BOOL, "d": PCM.TO_STRING},
        [{"a": 1, "b": 2.5, "c": True, "d": "hello"}]
    ), (
        "基本パターン2: 整数、浮動小数点数、真偽値、文字列の変換",
        [{"a": "2", "b": "3.7", "c": "false", "d": "world"}],
        {"a": PCM.TO_INT, "b": PCM.TO_FLOAT, "c": PCM.TO_BOOL, "d": PCM.TO_STRING},
        [{"a": 2, "b": 3.7, "c": False, "d": "world"}]
    ), (
        "dataが空の場合: 空のリストを返す",
        [],
        {"a": PCM.TO_INT, "b": PCM.TO_FLOAT, "c": PCM.TO_BOOL, "d": PCM.TO_STRING},
        []
    ), (
        "methodが空の場合: 元のデータをそのまま返す",
        [{"a": "1", "b": "2.5", "c": "true", "d": "hello"}],
        {},
        [{"a": "1", "b": "2.5", "c": "true", "d": "hello"}]
    ), (
        "methodに存在しないキーを指定した場合: 元のデータをそのまま返す",
        [{"a": "1", "b": "2.5", "c": "true", "d": "hello"}],
        {"a": PCM.TO_INT, "b": PCM.TO_FLOAT, "e": PCM.TO_STRING},
        [{"a": 1, "b": 2.5, "c": "true", "d": "hello"}]
    )
])
def test_convert_data_type_basic(description: str,
                                 data: list[dict[str, str]],
                                 method: dict[str, ParameterConversionMethod],
                                 expected: dict[str, Any]):
    """基本的なデータ型変換が正しく行われることを確認する"""
    assert convert_data_type(data, method) == expected, description

@pytest.mark.parametrize("data, method", [
    (   # 整数
        [{"a": "not_a_number"}], {"a": PCM.TO_INT}
    ), (# 浮動小数点数
        [{"a": "not_a_number"}], {"a": PCM.TO_FLOAT}
    )
])
def test_convert_data_type_type_error(data: list[dict[str, str]],
                                      method: dict[str, ParameterConversionMethod]):
    """変換できないデータ型を指定した場合に、ValueErrorを発生させることを確認する"""
    with pytest.raises(ValueError):
        convert_data_type(data, method)
