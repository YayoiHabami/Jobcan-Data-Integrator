"""
コンフィグファイルの内容を読み込み、変更、保存するためのモジュール

Classes
-------
- ConfigVariable
  - コンフィグファイルの変数を格納するクラス
- ConfigSection
  - コンフィグファイルのセクションを格納するクラス
- ConfigData
  - コンフィグファイルの内容を格納するクラス
- ConfigEditor
  - コンフィグファイルの内容を読み込み、変更、保存するためのクラス。
    configparser にコメントの読み書き、
    および変数の型、範囲、デフォルト値の読み書きを追加したもの。

Functions
---------
- parse_config_file
  - コンフィグファイルのセクションと内容、およびその型や説明を辞書に変換する
- get_range_string
  - 範囲の種類と値を文字列に変換する
- check_range
  - 値が範囲内に収まっているか確認

Attributes
----------
ConfigValueType : Union[bool, int, float, str]
    ConfigVariable の value, default の型

Usage
-----
1. コンフィグファイルの読み込み

```python
from jobcan_di.config.config_editor import ConfigEditor

editor = ConfigEditor("config.ini")
```

2a. コンフィグファイルの内容の取得

```python
var1 = editor["section1"]["variable1"]
```

2b. コンフィグファイルの内容の設定

```python
editor["section1"]["variable1"] = "new_value"
```

3. コンフィグファイルの保存

```python
# 元のファイルに上書き
editor.save()

# 別のファイルに保存
editor.save("config2.ini")
```
"""
import configparser
from enum import Enum, auto
import re
from typing import Tuple, Dict, Union, overload, Optional


ConfigValueType = Union[bool, int, float, str]
"""ConfigVariable の value, default の型"""


VARIABLE_TYPES = {
    "bool": bool,
    "int": int,
    "float": float,
    "string": str
}
"""変数の型を辞書に変換する"""


TYPE_TO_STR = {
    bool: "bool",
    int: "int",
    float: "float",
    str: "string"
}
"""変数の型を文字列に変換する辞書"""


class RangeType(Enum):
    """変数の範囲の種類"""
    NONE = auto()
    """範囲指定なし"""
    LIST_NE_NE = auto()
    """(min, max)"""
    LIST_NE_E = auto()
    """(min, max]"""
    LIST_E_NE = auto()
    """[min, max)"""
    LIST_E_E = auto()
    """[min, max]"""
    SET = auto()
    """{value1, value2, ...}"""

class ConfigVariable:
    """コンフィグファイルの変数を格納するクラス

    Attributes
    ----------
    value : any
        変数の値、bool, int, float, str のいずれかの型の値
    description : list[str]
        変数の説明
    type : any
        変数の型、bool, int, float, str のいずれか
    range_type : RangeType
        変数の範囲の種類
    range : list
        変数の範囲、または集合。集合以外の場合は [min, max] の形式、bool の場合は [False, True]。
        指定されていない場合は空リスト
    default: any
        変数のデフォルト値、bool, int, float, str のいずれかの型の値
        デフォルト値が指定されていない場合は None
    tags : dict[str, Union[str, float]]
        変数のタグ
    """
    def __init__(self):
        self.value: ConfigValueType = None
        """変数の値"""
        self.description: list[str] = []
        """変数の説明"""
        self.type: ConfigValueType = None
        """変数の型"""
        self.range_type: RangeType = None
        """変数の範囲の種類"""
        self.range: list[ConfigValueType] = []
        """変数の範囲、または集合"""
        self.default: Optional[ConfigValueType] = None
        """変数のデフォルト値"""
        self.tags: Dict[str, Union[str, float]] = {}
        """変数のタグ"""


class ConfigSection:
    """コンフィグファイルのセクションを格納するクラス

    Attributes
    ----------
    description : list[str]
        セクションの説明
    tags : dict[str, Union[str, float]]
        セクションのタグ

    Usage
    -----
    - データの取得
      - section["variable_name"] -> ConfigVariable オブジェクト
      - section["variable_name"].value -> ConfigValueType
      - section["variable_name"].description -> list[str]
      - section["variable_name"].type -> ConfigValueType
      - section["variable_name"].range_type -> RangeType
      - section["variable_name"].range -> list[ConfigValueType]
      - section["variable_name"].default -> ConfigValueType
    - データの設定
      - section["variable_name"] = value (value: ConfigVariable オブジェクト)
      - section["variable_name"] = value (value: ConfigValueType)
      - section["variable_name"].value = value (value: ConfigValueType)
    - データの削除: del section["variable_name"]
    - キーの存在確認: "variable_name" in section
    - イテレーション: for key in section
    - キーのリスト: section.keys()
    - 値のリスト: section.values()
    - キーと値のリスト: section.items()
    """
    def __init__(self):
        self._variables: Dict[str, ConfigVariable] = {}
        self.description: list[str] = []
        """セクションの説明"""
        self.tags: Dict[str, Union[str, float]] = {}
        """セクションのタグ"""

    def __getitem__(self, key:str) -> ConfigVariable:
        return self._variables[key.upper()]

    def __setitem__(self, key:str, value:Union[ConfigVariable, ConfigValueType]):
        if isinstance(value, ConfigVariable):
            self._variables[key.upper()] = value
        else:
            self._variables[key.upper()].value = value

    def __delitem__(self, key:str):
        if key.upper() not in self._variables:
            raise KeyError(f"KeyError: {key}")
        del self._variables[key.upper()]

    def __contains__(self, key:str) -> bool:
        return key.upper() in self._variables

    def __iter__(self):
        return iter(self._variables)

    def __len__(self) -> int:
        return len(self._variables)

    def keys(self):
        """セクション内の変数名を取得する

        Returns
        -------
        keys : dict_keys[str, ConfigVariable]
            変数名の view
        """
        return self._variables.keys()

    def values(self):
        """セクション内の変数を取得する

        Returns
        -------
        values : dict_values[str, ConfigVariable]
            変数 (ConfigVariable) の view
        """
        return self._variables.values()

    def items(self):
        """セクション内の変数名と変数を取得する

        Returns
        -------
        items : dict_items[str, ConfigVariable]
            変数名と値 (ConfigVariable) のペアの view
        """
        return self._variables.items()


class ConfigData:
    """コンフィグファイルの内容を格納するクラス

    Attributes
    ----------
    description : list[str]
        コンフィグファイルの冒頭部分のコメント
    tags : dict[str, Union[str, float]]
        コンフィグファイルのタグ

    Usage
    -----
    - データの取得
      - data["section_name"]["variable_name"] -> ConfigVariable オブジェクト
      - data["section_name"]["variable_name"].value -> ConfigValueType
    - データの設定
      - data["section_name"]["variable_name"] = value (value: ConfigVariable オブジェクト)
      - data["section_name"]["variable_name"] = value (value: ConfigValueType)
      - data["section_name"]["variable_name"].value = value (value: ConfigValueType)
    - データの削除: del data["section_name"]["variable_name"]
    - キーの存在確認: "section_name" in data
    - イテレーション: for key in data
    - キーのリスト: data.keys()
    - 値のリスト: data.values()
    - キーと値のリスト: data.items()
    """
    def __init__(self):
        self._sections: Dict[str, ConfigSection] = {}
        self.description: list[str] = []
        """コンフィグファイルの冒頭部分のコメント"""
        self.tags: Dict[str, Union[str, float]] = {}
        """コンフィグファイルのタグ"""

    def __getitem__(self, key:str) -> ConfigSection:
        return self._sections[key.upper()]

    def __setitem__(self, key:str, value:ConfigSection):
        self._sections[key.upper()] = value

    def __delitem__(self, key:str):
        if key.upper() not in self._sections:
            raise KeyError(f"KeyError: {key}")
        del self._sections[key.upper()]

    def __contains__(self, key:str) -> bool:
        return key.upper() in self._sections

    def __iter__(self):
        return iter(self._sections)

    def __len__(self) -> int:
        return len(self._sections)

    def keys(self):
        """セクション名を取得する

        Returns
        -------
        keys : dict_keys[str, ConfigSection]
            セクション名の view
        """
        return self._sections.keys()

    def values(self):
        """セクションを取得する

        Returns
        -------
        values : dict_values[str, ConfigSection]
            セクション (ConfigSection) の view
        """
        return self._sections.values()

    def items(self):
        """セクション名とセクションを取得する

        Returns
        -------
        items : dict_items[str, ConfigSection]
            セクション名とセクション (ConfigSection) のペアの view
        """
        return self._sections.items()


def _parse_config_range_hint(range_hint:str, value_type: ConfigValueType) -> Tuple[RangeType, list]:
    """コンフィグファイルの範囲指定のヒントを解析する

    Args
    ----
    range_hint : str
        コンフィグファイルの範囲指定のヒント
    value_type
        変数の型、bool, int, float, str のいずれか

    Returns
    -------
    range_type_hint : RangeType
        範囲の種類
    range_hint : list
        範囲の値
    """
    # 範囲の種類を取得
    if range_hint.startswith("{"):
        range_type_hint = RangeType.SET
    elif range_hint.startswith("[") and range_hint.endswith("]"):
        range_type_hint = RangeType.LIST_E_E
    elif range_hint.startswith("[") and range_hint.endswith(")"):
        range_type_hint = RangeType.LIST_E_NE
    elif range_hint.startswith("(") and range_hint.endswith("]"):
        range_type_hint = RangeType.LIST_NE_E
    elif range_hint.startswith("(") and range_hint.endswith(")"):
        range_type_hint = RangeType.LIST_NE_NE
    else:
        range_type_hint = RangeType.NONE

    # 範囲の値を取得
    range_hint = range_hint.strip("{}[]()").split(",")
    # 無限を置換
    if range_type_hint not in [RangeType.SET, RangeType.NONE]:
        range_hint[0] = range_hint[0] if range_hint[0] != "" else "-inf"
        range_hint[1] = range_hint[1] if range_hint[1] != "" else "inf"
    elif range_type_hint == RangeType.SET:
        # 文字列のサイドの"を削除
        range_hint = [value.strip().strip('"') for value in range_hint]
    range_hint = [value_type(value.strip()) for value in range_hint]

    return range_type_hint, range_hint


def _parse_config_type_hint(comment:str) -> Tuple[str, RangeType, list, ConfigValueType]:
    """コンフィグファイルのコメントから型、範囲、デフォルト値を取得する

    Args
    ----
    comment : str
        コンフィグファイルのコメント

    Returns
    -------
    type_hint : str
        変数の型
    range_type_hint : str
        変数の範囲の種類
    range_hint : list
        変数の範囲
    default_hint : str
        変数のデフォルト値
    """
    # コメントから型、範囲、デフォルト値を取得
    _type = str
    r_type_hint = None
    range_hint = []
    default_hint = None
    # 型を取得
    if (result:=re.search(r"type: ([\w]+);", comment)) is not None:
        assert result.group(1) in VARIABLE_TYPES, f"Invalid type: {result.group(1)}"
        _type = VARIABLE_TYPES[result.group(1)]
    # 型が指定されていない場合は str とする（_typeの初期値）

    # 範囲、デフォルト値を取得
    if _type == bool:
        r_type_hint = RangeType.SET
        range_hint = [False, True]
    elif (result:=re.search(r'range: *([\{\[\(][-"\w, ]*[\}\]\)])[;\n]', comment)) is not None:
        r_type_hint, range_hint = _parse_config_range_hint(result.group(1), _type)
    else:
        r_type_hint = RangeType.NONE
    if (result:=re.search(r'default: *([Tt]rue|[Ff]alse|0|1)[;\n]', comment)) is not None:
        # デフォルト値 (bool) を取得
        default_hint = result.group(1).lower() == "true"
    elif (result:=re.search(r'default: *([-\d\.\,]*)[;\n]', comment)) is not None:
        # デフォルト値 (非文字列) を取得
        default_hint = _type(result.group(1))
    elif (result:=re.search(r'default: *"(.*)"[;\n]', comment)) is not None:
        # デフォルト値 (任意文字列) を取得
        default_hint = result.group(1)

    return _type, r_type_hint, range_hint, default_hint

def _parse_config_file_descriptions(
        lines:list[str]
    ) -> Tuple[list[str], dict[str, Union[str, float]]]:
    """コンフィグファイルのコメントを読み込む

    Args
    ----
    lines : list
        コンフィグファイルの内容を行ごとに分割したリスト、
        対象の説明の範囲のみを渡す（変数の場合、変数の型ヒントの行は含めない）
    result : ConfigVariable
        コンフィグファイルの変数を格納するオブジェクト

    Returns
    -------
    description : list[str]
        説明部分
    tags : dict[str, Union[str, float]]
        タグ
    """
    description = []
    tags = {}

    for line in lines[:]:
        # "; #tags# "から始まる行はタグとして扱う
        if (result:=re.match(r"; #tags# (.*)", line)) is not None:
            tag_kv = [tag.strip().split("=") for tag in result.group(1).split(";") if "=" in tag]
            tags = {kv[0]: kv[1][1:-1] if kv[1].startswith('"') else float(kv[1])
                    for kv in tag_kv}
        else:
            description.append(line.lstrip(";").rstrip())

    return description, tags

def _parse_config_file_value(lines:list[str], value_name:str) -> ConfigVariable:
    """コンフィグファイルの各変数ごとのコメントを読み込む

    Args
    ----
    lines : list
        コンフィグファイルの内容を行ごとに分割したリスト、
        対象のセクションの範囲のみを渡す
    value_name : str
        変数名
    """
    start_with = 0
    end_with = len(lines) - 1
    for i, line in enumerate(lines):
        if (result:=re.match(r"([\w]+)=.*", line)) is not None:
            # 大文字・小文字を区別せずに変数名を比較
            if result.group(1).casefold() == value_name.casefold():
                end_with = i - 1
                break
            else:
                start_with = i + 1

    # 変数のコメントを読み込む
    result = ConfigVariable()
    desc, tags = _parse_config_file_descriptions(lines[start_with:end_with])
    result.description = desc
    result.tags = tags

    # 変数の型、範囲、デフォルト値を取得
    hints = _parse_config_type_hint(lines[end_with])
    result.type = hints[0]
    result.range_type = hints[1]
    result.range = hints[2]
    result.default = hints[3]

    return result


def _parse_config_file_section(
        lines:list[str], section:str, variable_names:list[str]
    ) -> ConfigSection:
    """コンフィグファイルのセクションを辞書に変換する

    Args
    ----
    lines : list
        コンフィグファイルの内容を行ごとに分割したリスト
    section : str
        セクション名
    variable_names : list
        変数名のリスト
    """
    start_with = -1
    for i, line in enumerate(lines):
        if (result:=re.match(r"\[([\w]+)\]", line)) is not None:
            if result.group(1) == section:
                start_with = i
            else:
                # 対象のセクションの次のセクションが見つかったら終了
                if start_with != -1:
                    break
    end_with = i - 1 if i+1 < len(lines) else i

    # 各変数のコメントを読み込む
    result = ConfigSection()
    for name in variable_names:
        result[name] = _parse_config_file_value(lines[start_with+1:end_with], name)

    # セクションのコメントを読み込む（セクション名よりも前の、連続したコメント行）
    comment_start_with = -1
    for i in range(start_with-1, -1, -1):
        if not lines[i].startswith(";"):
            comment_start_with = i + 1
            break
    if comment_start_with < (comment_end_with:=start_with):
        result.description, result.tags = _parse_config_file_descriptions(
            lines[comment_start_with:comment_end_with]
        )

    return result


def parse_config_file(config_path:str, encoding:str = "utf-8") -> Union[ConfigData, None]:
    """コンフィグファイルのセクションと内容、およびその型や説明を辞書に変換する

    Args
    ----
    config : str
        コンフィグファイルのパス
    encoding : str
        コンフィグファイルのエンコーディング

    Returns
    -------
    data : ConfigData
        コンフィグファイルの内容を格納したオブジェクト
        指定したファイルが存在しない/読み込めない場合は None
    """
    config = configparser.ConfigParser()
    config.read(config_path, encoding=encoding)

    # コンフィグファイルを読み込む
    try:
        with open(config_path, 'r', encoding=encoding) as f:
            lines = f.readlines()
    except FileNotFoundError:
        return None
    except UnicodeDecodeError:
        return None
    except PermissionError:
        # 指定されたパスがフォルダを指している場合
        return None

    data = ConfigData()

    # 冒頭部分のコメントをファイルの説明として格納
    end_with = 0
    for i, line in enumerate(lines):
        if not line.startswith(";"):
            end_with = i
            break
    data.description, data.tags = _parse_config_file_descriptions(lines[:end_with])

    # 冒頭部分のコメントを削除
    lines = lines[end_with:]

    # コンフィグファイルのコメントを反映
    for section in config.sections():
        val_names = list(config[section].keys())
        data[section] = _parse_config_file_section(lines, section, val_names)

        # 各コンフィグ値の型を反映
        # （型情報はコメントから、値はconfigparserから取得しているためここで反映）
        for key in val_names:
            if (_type:=data[section][key].type) != bool:
                # bool 以外の型
                data[section][key].value = _type(config[section][key])
            else:
                # bool 型
                data[section][key].value = config[section].getboolean(key)

    return data


def get_range_string(range_type:RangeType, range_:list) -> str:
    """範囲の種類と値を文字列に変換する

    Args
    ----
    range_type : RangeType
        範囲の種類
    range_ : list
        範囲の値

    Returns
    -------
    range_str : str
        範囲の種類と値を表す文字列
    """
    if range_type == RangeType.NONE:
        return ""
    if range_type == RangeType.SET:
        if range == [False, True]:
            return "{0, 1}"
        else:
            for i, value in enumerate(range):
                if isinstance(value, str):
                    range_[i] = f'"{value}"'
        return "{" + ", ".join([str(value) for value in range_]) + "}"
    if range_type == RangeType.LIST_NE_NE:
        return f"({range_[0]}, {range_[1]})"
    if range_type == RangeType.LIST_NE_E:
        return f"({range_[0]}, {range_[1]}]"
    if range_type == RangeType.LIST_E_NE:
        return f"[{range_[0]}, {range_[1]})"
    if range_type == RangeType.LIST_E_E:
        return f"[{range_[0]}, {range_[1]}]"
    return ""


# 値が範囲内に収まっているか確認
@overload
def check_range(value:ConfigValueType, range_type:RangeType, range_:list) -> bool:
    ...
@overload
def check_range(config:ConfigVariable) -> bool:
    ...


def check_range(value:Union[ConfigValueType, ConfigVariable],
                range_type:Optional[RangeType] = None,
                range_:Optional[list] = None) -> bool:
    """値が範囲内に収まっているか確認

    Args
    ----
    value : Union[bool, ConfigVariable]
        値
    range_type : RangeType
        範囲の種類
    range : list
        範囲の値

    Returns
    -------
    result : bool
        範囲内に収まっている場合は True、それ以外は False
    """
    if isinstance(value, ConfigVariable):
        return _check_range(value.value, value.range_type, value.range)
    return _check_range(value, range_type, range_)


def _check_range(value:ConfigValueType, range_type:RangeType, range_:list) -> bool:
    """値が範囲内に収まっているか確認

    Args
    ----
    value : ConfigValueType
        値
    range_type : RangeType
        範囲の種類
    range : list
        範囲の値

    Returns
    -------
    result : bool
        範囲内に収まっている場合は True、それ以外は False
    """
    if range_type == RangeType.NONE:
        return True
    if range_type == RangeType.SET:
        return value in range_
    if range_type == RangeType.LIST_NE_NE:
        return range_[0] < value < range_[1]
    if range_type == RangeType.LIST_NE_E:
        return range_[0] < value <= range_[1]
    if range_type == RangeType.LIST_E_NE:
        return range_[0] <= value < range_[1]
    if range_type == RangeType.LIST_E_E:
        return range_[0] <= value <= range_[1]
    return False


class ConfigEditor:
    """コンフィグファイルの内容を読み込み、変更、保存するためのクラス

    Usage
    -----
    - データの読込
      - `editor = ConfigEditor("config.ini")`
      - `editor.load("config.ini")`
    - データの取得
      - `editor["section_name"]["variable_name"] -> ConfigVariable オブジェクト`
      - `editor["section_name"]["variable_name"].value -> ConfigValueType`
    - データの設定
      - `editor["section_name"]["variable_name"] = value (value: ConfigVariable オブジェクト)`
      - `editor["section_name"]["variable_name"] = value (value: ConfigValueType)`
      - `editor["section_name"]["variable_name"].value = value (value: ConfigValueType)`
    - データの削除: `del editor["section_name"]["variable_name"]`
    - データの保存
      - `editor.save("config2.ini")` (別のファイルに保存)
      - `editor.save()` (元のファイルに上書き)
    """

    def __init__(self, path: Optional[str] = None, encoding: str = "utf-8"):
        self._path = path
        self._encoding = encoding
        self._data = None if path is None else parse_config_file(path, encoding)
        """コンフィグファイルの内容を格納したオブジェクト"""

    def __getitem__(self, key:str) -> ConfigSection:
        return self._data[key]

    def __setitem__(self, key:str, value:ConfigSection):
        self._data[key] = value

    def __delitem__(self, key:str):
        if key not in self._data:
            raise KeyError(f"KeyError: {key}")
        del self._data[key]

    def __contains__(self, key:str) -> bool:
        return key in self._data

    def __iter__(self):
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)

    def load(self, path: Optional[str] = None,
                   encoding: str = "utf-8"):
        """コンフィグファイルを読み込む

        Args
        ----
        path : str
            コンフィグファイルのパス、
            指定しなかった場合は初期化時に指定したパスを再度読み込む
        encoding : str
        """
        if path is None:
            path = self._path

        self._path = path
        self._encoding = encoding
        self._data = parse_config_file(path, encoding)

    def is_loaded(self) -> bool:
        """コンフィグファイルが読み込まれているか確認する"""
        return self._data is not None

    def keys(self):
        """セクション名を取得する

        Returns
        -------
        keys : dict_keys[str, ConfigSection]
            セクション名の view
        """
        return self._data.keys()

    def values(self):
        """セクションを取得する

        Returns
        -------
        values : dict_values[str, ConfigSection]
            セクション (ConfigSection) の view
        """
        return self._data.values()

    def items(self):
        """セクション名とセクションを取得する

        Returns
        -------
        items : dict_items[str, ConfigSection]
            セクション名とセクション (ConfigSection) のペアの view
        """
        return self._data.items()

    def set(self, section:str, key:str, value:str):
        """コンフィグの値を設定する

        Args
        ----
        section : str
            セクション名
        key : str
            変数名
        value : str
            変数の値
        """
        self._data[section][key].value = value

    def get(self, section:str, key:str) -> str:
        """コンフィグの値を取得する

        Args
        ----
        section : str
            セクション名
        key : str
            変数名

        Returns
        -------
        value : str
            変数の値
        """
        return self._data[section][key].value

    def _get_comment(self, description:list, tags:dict) -> str:
        """説明とタグからコメントをテキストとして取得する"""
        comment = ""
        for line in description:
            comment += f";{line}\n"
        if len(tags) > 0:
            comment += "; #tags#"
            for key, value in tags.items():
                if isinstance(value, str):
                    comment += f" {key}=\"{value}\";"
                else:
                    comment += f" {key}={value};"
            comment += "\n"
        return comment

    def _save(self, f):
        """コンフィグをコメント付きで保存する
        Args
        ----
        f : file
            ファイルオブジェクト
        """

        # 冒頭部分のコメント・タグを保存
        f.write(self._get_comment(self._data.description, self._data.tags))

        # セクションごとに変数を保存
        for section, section_data in self._data.items():
            f.write("\n")

            # セクションの説明・タグを保存
            f.write(self._get_comment(section_data.description, section_data.tags))

            f.write(f"[{section}]\n")
            for key, value in section_data.items():
                # 変数の説明・タグを保存
                f.write(self._get_comment(value.description, value.tags))

                # 変数の型、範囲、デフォルト値を保存)
                f.write(f"; type: {TYPE_TO_STR[value.type]};")
                if value.range_type != RangeType.NONE:
                    f.write(f" range: {get_range_string(value.range_type, value.range)};")
                if value.default is not None:
                    if value.type == str:
                        f.write(f" default: \"{value.default}\";")
                    elif value.type == bool:
                        f.write(f" default: {int(value.default)};")
                    else:
                        f.write(f" default: {value.default};")
                f.write("\n")

                # 変数の値を保存
                if value.type == bool:
                    f.write(f"{key}={int(value.value)}\n")
                else:
                    f.write(f"{key}={value.value}\n")

    def save(self, path: Optional[str] = None, encoding: Optional[str] = None):
        """コンフィグをコメント付きで保存する

        Args
        ----
        path : str
            保存先のパス、指定しなかった場合は元のファイルに上書き
        """
        path = path if path is not None else self._path
        encoding = encoding if encoding is not None else self._encoding
        with open(path, "w", encoding=encoding) as f:
            self._save(f)
