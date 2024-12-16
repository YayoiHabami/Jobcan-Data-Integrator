"""CSV -> JSON -> SQL 変換設定の解析モジュール

このモジュールは、CSVファイルをJSONファイルに変換する際の設定と、
JSONファイルをデータベースに挿入する際の設定を解析するための関数を提供する。

Classes
-------
- `ConversionSettings`: CSV -> JSON -> SQL 変換設定
  - `CsvToJsonSettings`: CSV -> JSON 変換設定
    - `CsvImportSettings`: CSVファイルのインポート設定
    - `FormItems`: 申請書ごとの項目
  - (`PipelineDefinition`: JSON -> SQL 変換設定、
    `jobcan_di.database.data_pipeline` モジュールからインポート)

Functions
---------
- `parse_toml_data`: TOMLデータ文字列から変換設定を解析する
- `parse_toml`: TOMLファイルから変換設定を解析する

Constants
---------
- `DEFAULT_CSV_ENCODING`: CSVファイルのデフォルトエンコーディング
- `DEFAULT_CSV_DELIMITER`: CSVファイルのデフォルト区切り文字
- `DEFAULT_CSV_QUOTECHAR`: CSVファイルのデフォルトクオート文字
"""
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Final, Optional

import tomlkit
import tomlkit.items as toml_items

from jobcan_di.database.data_pipeline import PipelineDefinition
from jobcan_di.database.data_pipeline.transformation import (
    validate_conversion_method_string, ParameterConversionMethod
)
from jobcan_di.database.data_pipeline.parser import (
    parse_table_definitions, parse_data_link
)



DEFAULT_CSV_ENCODING: Final[str] = "cp932"
"""CSVファイルのデフォルトエンコーディング"""
DEFAULT_CSV_DELIMITER: Final[str] = ","
"""CSVファイルのデフォルト区切り文字"""
DEFAULT_CSV_QUOTECHAR: Final[str] = '"'
"""CSVファイルのデフォルトクオート文字"""

@dataclass
class CsvImportSettings:
    """CSVファイルのインポート設定

    Attributes
    ----------
    folder : str
        読み込むCSVファイルの格納フォルダ
    file_name_regex : str
        読み込むCSVファイルのファイル名の正規表現
        $1 がフォーム名、$2 がフォルダ内での連番を示すような
        正規表現を指定する
    encoding : str
        CSVファイルのエンコーディング
    delimiter : str
        CSVファイルの区切り文字
    quotechar : str
        CSVファイルのクオート文字
    enable_auto_form_detection : bool
        CSVファイルの共通項目・追加項目等の自動判定を行うか
    """
    folder: str
    """読み込むCSVファイルの格納フォルダ"""
    file_name_regex: str
    """読み込むCSVファイルのファイル名の正規表現

    Notes
    -----
    - $1 がフォーム名、$2 がフォルダ内での連番を示すような
      正規表現を指定する
    """

    encoding: str = DEFAULT_CSV_ENCODING
    """CSVファイルのエンコーディング"""
    delimiter: str = DEFAULT_CSV_DELIMITER
    """CSVファイルの区切り文字"""
    quotechar: str = DEFAULT_CSV_QUOTECHAR
    """CSVファイルのクオート文字"""

    enable_auto_form_detection: bool = False
    """CSVファイルの共通項目・追加項目等の自動判定を行うか"""

@dataclass
class FormItems:
    """申請書ごとの項目

    Attributes
    ----------
    form_type : str
        フォームの種類
        - 'general_form': 汎用フォーム
        - 'expense_form': 経費精算フォーム
        - 'payment_form': 支払依頼フォーム
    form_unique_key : Optional[str]
        フォームを指定する固有のキー (form_idなど)
    common : list[list[str]]
        各form_typeごとに共通の項目
    extended : list[list[str]]
        (フォームごと(=form_idごと)ごとに固有の) 追加項目、申請書作成時に追加した項目
    detail : list[list[str]]
        (フォームごと(=form_idごと)ごとに固有の) 明細項目
    optional_items : dict[str, list[str]]
        フォームの項目のうち任意項目 (その項目が存在しない場合もある)

    Notes
    -----
    - いずれのリストも、`list[str]`は長さ4のリストで、[表示名、JSONキー、データ型、説明]
      を表す。また、データ型はフォーマットされたもの (大文字、`-`を`_`に変換) となる。
      ただし、空文字列も許容されることに注意する。
    """
    form_type: str
    """フォームの種類
    - 'general_form': 汎用フォーム
    - 'expense_form': 経費精算フォーム
    - 'payment_form': 支払依頼フォーム"""
    form_unique_key: Optional[str] = None
    """フォームを指定する固有のキー (form_idなど)
    tomlファイルの [csv2json.form_items.<form_type>.<form_unique_key>] に対応する"""

    form_name: Optional[str] = None
    """フォームの名前 (完全一致)"""

    common: list[list[str]] = field(default_factory=list)
    """各form_typeごとに共通の項目

    - `list[str]`は長さ4のリストで、[表示名、JSONキー、データ型、説明]を表す"""

    extended: list[list[str]] = field(default_factory=list)
    """(フォームごと(=form_idごと)に固有の) 追加項目、申請書作成時に追加した項目

    - `list[str]`は長さ4のリストで、[表示名、JSONキー、データ型、説明]を表す
    - form_unique_keyが指定されている場合のみ使用される"""

    detail: list[list[str]] = field(default_factory=list)
    """(フォームごと(=form_idごと)ごとに固有の) 明細項目

    - `list[str]`は長さ4のリストで、[表示名、JSONキー、データ型、説明]を表す
    - form_unique_keyが指定されている場合のみ使用される"""

    optional_items: dict[str, list[str]] = field(default_factory=lambda: {
        "common": [], "extends": [], "details": []
    })
    """フォームの項目のうち任意項目 (その項目が存在しない場合もある)

    - キーは "common", "extends", "details"
      - 例) optional_items["common"] = ["表示名1", "表示名2", ...]
    """

@dataclass
class CsvToJsonSettings:
    """CSVファイルをJSONファイルに変換する際の設定"""
    csv_import_settings: CsvImportSettings
    """CSVファイルのインポート設定"""

    form_items: dict[str, list[FormItems]] = field(default_factory=dict)
    """申請書ごとの項目

    - キーはフォームの種類: 'general_form', 'expense_form', 'payment_form'
    - 値はFormItemsのリスト"""

    def get_form_types(self) -> list[str]:
        """読込中のフォームの種類を取得する

        Returns
        -------
        list[str]
            フォームの種類のリスト
        """
        return list(self.form_items.keys())

    def get_form_type(self, *,
                      form_unique_key: Optional[str] = None,
                      form_name: Optional[str] = None) -> Optional[str]:
        """form_unique_keyまたはform_nameに対応するフォームの種類を取得する

        Parameters
        ----------
        form_unique_key : str
            form_unique_keyかform_nameのいずれかを指定する
            フォームを特定するためのキー (form_idなど).
            conversion_settings.toml の [csv2json.form_items.<form_type>.<form_unique_key>] に対応する
        form_name : str
            form_unique_keyかform_nameのいずれかを指定する
            フォームの名前 (完全一致)

        Returns
        -------
        Optional[str]
            form_unique_keyまたはform_nameに対応するフォームの種類
            (見つからない場合はNone)

        Notes
        -----
        - form_unique_keyとform_nameの両方が指定されている場合は`form_unique_key`を優先する
        """
        for form_type, forms in self.form_items.items():
            for form in forms:
                if ((form_unique_key is not None)
                        and (form.form_unique_key == form_unique_key)):
                    return form_type
                if ((form_name is not None)
                        and (form.form_name == form_name)):
                    return form_type

        return None

    def get_form_unique_keys(self, form_type:str) -> list[str]:
        """form_typeに対応するフォーム

        Parameters
        ----------
        form_type : str
            フォームの種類、'general_form', 'expense_form', 'payment_form'

        Returns
        -------
        list[str]
            form_typeに対応するフォームのform_unique_keyのリスト.
            各form_unique_keyはtomlファイルの [csv2json.form_items.<form_type>.<form_uk>] に対応する
        """
        if form_type not in self.form_items:
            return []
        return [form.form_unique_key for form in self.form_items[form_type]
                if form.form_unique_key is not None]

    def get_form_unique_key(self, form_name: str) -> Optional[str]:
        """form_nameに対応するフォームのform_unique_keyを取得する

        Parameters
        ----------
        form_name : str
            フォームの名前 (完全一致)

        Returns
        -------
        Optional[str]
            form_nameに対応するフォームのform_unique_key
            (見つからない場合はNone)
        """
        for form_type in self.form_items:
            for form in self.form_items[form_type]:
                if form.form_name == form_name:
                    return form.form_unique_key
        return None

    def get_form_items(self, form_type:str,
                       remove_specifics:bool=False) -> list[FormItems]:
        """form_typeに対応するFormItemsを取得する

        Parameters
        ----------
        form_type : str
            フォームの種類、'general_form', 'expense_form', 'payment_form'
        remove_specifics : bool
            Trueの場合、form_unique_keyが指定されているFormItemsを除外する
            (このため、戻り値リストの要素数は1となる)

        Returns
        -------
        list[FormItems]
            form_typeに対応するFormItemsのリスト
        """
        if form_type not in self.form_items:
            return []
        if remove_specifics:
            return [form for form in self.form_items[form_type]
                    if form.form_unique_key is None]
        return self.form_items[form_type]

    def get_form_item(self, form_type:str,
                      *,
                      form_unique_key:Optional[str] = None,
                      form_name: Optional[str] = None) -> Optional[FormItems]:
        """form_type, form_ukに対応するFormItemsを取得する

        Parameters
        ----------
        form_type : str
            フォームの種類、'general_form', 'expense_form', 'payment_form'
        form_unique_key : str
            form_unique_keyかform_nameのいずれかを指定する
            フォームを特定するためのキー (form_idなど).
            conversion_settings.toml の [csv2json.form_items.<form_type>.<form_unique_key>] に対応する
        form_name : str
            form_ukかform_nameのいずれかを指定する
            フォームの名前 (完全一致)

        Returns
        -------
        Optional[FormItems]
            form_type, form_ukに対応するFormItems
            (見つからない場合はNone)

        Raises
        ------
        ValueError
            - form_unique_keyとform_nameのどちらも指定されていない場合
        """
        if form_unique_key is None and form_name is None:
            raise ValueError("Either form_unique_key or form_name must be specified")

        if form_type not in self.form_items:
            return None

        for form in self.form_items[form_type]:
            # 各要素について指定されたキー/名前が一致するか確認
            # 両方指定されている場合は両方一致するものを返す
            if ((form_unique_key is not None)
                    and (form.form_unique_key != form_unique_key)):
                continue
            if ((form_name is not None)
                    and (form.form_name != form_name)):
                continue
            return form
        return None

@dataclass
class ConversionSettings:
    """変換設定

    Attributes
    ----------
    csv2json : CsvToJsonSettings
        CSVファイルをJSONファイルに変換する際の設定
    json2sql : PipelineDefinition
        JSONファイルをデータベースに挿入する際の設定
    """
    csv2json: CsvToJsonSettings
    """CSVファイルをJSONファイルに変換する際の設定"""

    json2sql: PipelineDefinition
    """JSONファイルをデータベースに挿入する際の設定"""


#
# パーサー
#

def _parse_csv_import_settings(data: toml_items.Item) -> CsvImportSettings:
    """CSVファイルのインポート設定を解析する

    Parameters
    ----------
    data : toml_items.Item
        CSVファイルのインポート設定のTOMLデータ
        [csv2json.import_settings] セクションのデータ

    Returns
    -------
    CsvImportSettings
        CSVファイルのインポート設定

    Raises
    ------
    ValueError
        - CSVファイルの格納フォルダが存在しないか文字列でない場合
        - CSVファイルのファイル名の正規表現が存在しないか文字列でない場合
        - エンコーディングが文字列でない場合
        - 区切り文字が文字列でない場合
        - クオート文字が文字列でない場合
    """
    if not isinstance(data, toml_items.Table):
        raise ValueError("CSV import settings must be a table")

    # 読み込むCSVファイルの格納フォルダ
    if ((folder := data.get("csv_folder_path", None)) is None
            or (not isinstance(folder, toml_items.String))):
        raise ValueError("The `csv_folder_path` does not exist or is not a string")
    folder = folder.value

    # 読み込むCSVファイルのファイル名の正規表現
    if ((file_name_regex := data.get("csv_file_name", None)) is None
            or (not isinstance(file_name_regex, toml_items.String))):
        raise ValueError("The `csv_file_name` does not exist or is not a string")
    file_name_regex = file_name_regex.value

    # CSVファイルのエンコーディング方式
    encoding = data.get("csv_encoding")
    if encoding is not None:
        if not isinstance(encoding, toml_items.String):
            raise ValueError("The encoding must be a string")
        encoding = encoding.value
    else:
        encoding = DEFAULT_CSV_ENCODING

    # CSVファイルの区切り文字
    delimiter = data.get("delimiter")
    if delimiter is not None:
        if not isinstance(delimiter, toml_items.String):
            raise ValueError("The delimiter must be a string")
        delimiter = delimiter.value
    else:
        delimiter = DEFAULT_CSV_DELIMITER

    # CSVファイルのクオート文字
    quotechar = data.get("quotechar")
    if quotechar is not None:
        if not isinstance(quotechar, toml_items.String):
            raise ValueError("The quotechar must be a string")
        quotechar = quotechar.value
    else:
        quotechar = DEFAULT_CSV_QUOTECHAR

    # CSVファイルの共通項目・追加項目等の自動判定を行うか
    enable_auto_detect = data.get("enable_auto_form_detection", False)

    return CsvImportSettings(
        folder, file_name_regex,
        encoding, delimiter, quotechar,
        enable_auto_detect
    )

def _assert_form_item_conversion_method(method: str) -> str:
    """フォーム項目の変換方法の文字列が正しいか検証する

    Parameters
    ----------
    method : str
        フォーム項目の変換方法の文字列

    Returns
    -------
    str
        フォーム項目の変換方法のフォーマットされた文字列
        (大文字、`-`を`_`に変換、空文字列は許容)

    Raises
    ------
    ValueError
        フォーム項目の変換方法の文字列が正しくない場合
    """
    if method == "":
        # 空文字列は許容する
        return method

    formatted = method.replace("-", "_").upper()

    if not validate_conversion_method_string(formatted):
        # アンダーバーによる名称とハイフンによる名称を候補として表示する
        candidates_ub = [m.name.lower() for m in ParameterConversionMethod]
        candidates_hp = [mn.replace("_", "-") for mn in candidates_ub]
        raise ValueError(f"Invalid conversion method: {method}"
                         f" Candidates: {candidates_hp} or ({candidates_hp})")

    return formatted

def _parse_form_items_array(data: toml_items.Item) -> list[list[str]]:
    """フォームの項目 (`common_items`等) を解析する

    Parameters
    ----------
    data : toml_items.Item
        フォームの項目のTOMLデータ
        `common_items`, `extended_items`, `detail_items` のデータ

    Returns
    -------
    list[list[str]]
        フォームの項目のリスト; [表示名, JSONキー, データ型, 説明]
        このうちデータ型は`-`を`_`に変換し、大文字に変換される (e.g. `to-int` -> `TO_INT`)

    Raises
    ------
    ValueError
        - フォームの項目が配列でない場合
        - 各フォーム項目が配列でない場合
        - フォーム項目の要素数が3または4でない場合
        - フォーム項目の要素が文字列でない場合
        - JSONキーが重複している場合
        - データ型が正しくない場合
    """
    if not isinstance(data, toml_items.Array):
        raise ValueError("Specific form items must be an array")

    form_items: list[list[str]] = []
    form_item_json_keys: list[str] = []

    for i, item in enumerate(data):
        if not isinstance(item, toml_items.Array):
            raise ValueError("Each specific form item must be an array (index: {i})")
        if len(item) not in [3, 4]:
            # [表示名, JSONキー, データ型, 説明] or [表示名, JSONキー, データ型] ではない場合
            # (説明は省略可とする)
            raise ValueError("Each specific form item must have 3 or 4 elements" \
                             f"(index: {i})")
        unwrapped = item.unwrap()
        if not all(isinstance(i, str) for i in unwrapped):
            raise ValueError("Each element of specific form item must be a string" \
                             f"(index: {i})")

        # JSONキーの重複を検証 (重複していることを許容しない)
        json_key: str = unwrapped[1]
        if json_key in form_item_json_keys:
            raise ValueError(f"Duplicated JSON key: {json_key} in specific form item (index: {i})")

        # データ型の検証
        try:
            d_type = _assert_form_item_conversion_method(unwrapped[2])
        except ValueError as e:
            raise ValueError(f"{e.args[0]} in specific form item (index: {i})") from e

        # 要素を追加
        item_name: str = unwrapped[0]
        description: str = "" if len(unwrapped) == 3 else unwrapped[3]
        form_items.append([item_name, json_key, d_type, description])
        form_item_json_keys.append(json_key)

    return form_items

def _parse_specific_form_items(
        data: toml_items.Item, common_form: FormItems,
        form_type: str, form_unique_key: str
    ) -> FormItems:
    """特定のフォームの項目を解析する

    Parameters
    ----------
    data : toml_items.Item
        特定のフォームの項目のTOMLデータ
        [csv2json.form_items.<form_type>.<form_unique_key>] セクションのデータ
    common_items : list[list[str]]
        各form_typeごとに共通の項目、
        [csv2json.form_items.<form_type>] の common_items のデータ
    form_type : str
        フォームの種類、'general_form', 'expense_form', 'payment_form'
    form_unique_key : str
        フォームを特定するためのキー

    Returns
    -------
    FormItems
        特定のフォームの項目
    """
    if not isinstance(data, toml_items.Table):
        raise ValueError(f"Specific form items (id: {form_unique_key}) must be a table")

    # フォームの名前を取得する
    if ((form_name := data.get("form_name", None)) is not None
            and isinstance(form_name, toml_items.String)):
        form_name = form_name.value
    else:
        # フォームの名前が存在しない場合はエラー
        raise ValueError(f"The `form_name` does not exist or is not a string " \
                            f"(id: {form_unique_key})")

    # フォームの追加項目を取得する
    extended_items = []
    if (_extended := data.get("extended_items", None)) is not None:
        try:
            extended_items = _parse_form_items_array(_extended)
        except ValueError as e:
            raise ValueError(f"{e.args[0]} in `extended_items` section " \
                             f"(id: {form_unique_key})") from e

    # フォームの明細項目を取得する
    detail_items = []
    if (_detail := data.get("detail_items", None)) is not None:
        try:
            detail_items = _parse_form_items_array(_detail)
        except ValueError as e:
            raise ValueError(f"{e.args[0]} in `detail_items` section " \
                             f"(id: {form_unique_key})") from e

    return FormItems(form_type,
                     form_unique_key=form_unique_key,
                     form_name=form_name,
                     common=deepcopy(common_form.common),
                     extended=extended_items, detail=detail_items,
                     optional_items=deepcopy(common_form.optional_items))

def _parse_form_items(data: toml_items.Item, form_type: str) -> list[FormItems]:
    """フォームの項目を解析する

    Parameters
    ----------
    data : toml_items.Item
        フォームの項目のTOMLデータ
        [csv2json.form_items.<form_type>] セクションのデータ
    form_type : str
        フォームの種類、'general_form', 'expense_form', 'payment_form'

    Returns
    -------
    list[FormItems]
        フォームの項目のリスト

    Raises
    ------
    ValueError
        - フォームの項目が配列でない場合
        - 各フォーム項目が配列でない場合
        - フォーム項目の要素数が3または4でない場合
        - フォーム項目の要素が文字列でない場合
        - JSONキーが重複している場合
        - データ型が正しくない場合
    """
    if not isinstance(data, toml_items.Table):
        raise ValueError("Form items must be a table")

    # フォームの全IDを取得する
    form_unique_keys: list[str] = [k for k in data.keys()
                                   if (k != "common_items") and (k.isnumeric())]

    # フォームの共通項目 (`common_items`) を取得する
    if (_common_items := data.get("common_items", None)) is None:
        raise ValueError("The `common_items` does not exist")
    try:
        common_items = _parse_form_items_array(_common_items)
    except ValueError as e:
        raise ValueError(f"{e.args[0]} in `common_items` section") from e

    # フォームの共通項目のうち任意項目を取得する
    if (_optional_common_items := data.get("optional_items", None)) is not None:
        # list[str] に変換
        if not isinstance(_optional_common_items, toml_items.Array):
            raise ValueError("Optional common items must be an array")
        optional_common_items = [i.value for i in _optional_common_items
                                 if isinstance(i, toml_items.String)]
    else:
        optional_common_items: list[str] = []

    form_items = [FormItems(form_type, common=common_items)]
    form_items[0].optional_items["common"] = optional_common_items

    for form_uk in form_unique_keys:
        # 特定のform_unique_keyのフォームの項目を取得する
        specific_form = data[form_uk]
        try:
            form_items.append(
                _parse_specific_form_items(specific_form, form_items[0], form_type, form_uk)
            )
        except ValueError as e:
            raise ValueError(f"{e.args[0]} in `{form_uk}` section") from e

    return form_items

def _parse_csv_to_json_settings(data: toml_items.Item) -> CsvToJsonSettings:
    """CSV to JSON変換設定を解析する

    Parameters
    ----------
    data : toml_items.Item
        CSV to JSON変換設定のTOMLデータ

    Returns
    -------
    CsvToJsonSettings
        CSV to JSON変換設定

    Raises
    ------
    ValueError
        - CSV to JSON変換設定がテーブルでない場合
        - `import_settings` セクションが存在しないかテーブルでない場合
        - `form_items` セクションが存在しないかテーブルでない場合
        - フォームの項目が解析できない場合
    """
    if not isinstance(data, toml_items.Table):
        raise ValueError("CSV to JSON conversion settings must be a table")

    try:
        # CSVファイルのインポート設定
        if ((csv_import_settings := data.get("import_settings", None)) is None
                or (not isinstance(csv_import_settings, toml_items.Table))):
            raise ValueError("The `import_settings` does not exist or is not a table")
        csv_import_settings = _parse_csv_import_settings(csv_import_settings)
    except ValueError as e:
        raise ValueError(f"{e.args[0]} in `import_settings` section") from e

    # フォームの項目を取得する
    form_items = {}
    form_types = [t for t in data.keys() if t.endswith("_form")]
    for form_type in form_types:
        try:
            form_items[form_type] = _parse_form_items(data[form_type], form_type)
        except ValueError as e:
            raise ValueError(f"{e.args[0]} in `{form_type}` section") from e

    return CsvToJsonSettings(csv_import_settings, form_items)

def _parse_json_to_sql_settings(data: toml_items.Item) -> PipelineDefinition:
    """JSON to SQL変換設定を解析する

    Parameters
    ----------
    data : toml_items.Item
        JSON to SQL変換設定のTOMLデータ

    Returns
    -------
    PipelineDefinition
        JSON to SQL変換設定

    Raises
    ------
    ValueError
        - JSON to SQL変換設定がテーブルでない場合
        - `output` セクションが存在しないかテーブルでない場合
        - `pipeline` セクションが存在しないかテーブルでない場合
        - テーブル定義が解析できない場合
        - データリンクが解析できない場合

    Notes
    -----
    - 実装内容的には `jobcan_di.database.data_pipeline.parser` の
      `parse_toml_data` とほぼ同じ内容ではあるが、引数および変数名の定義
      が異なるため別の関数として定義している
    """
    if not isinstance(data, toml_items.Table):
        raise ValueError("JSON to SQL conversion settings must be a table")

    # 挿入先のDB・テーブル定義
    if (((td := data.get("output", None)) is None)
            or (not isinstance(td, toml_items.Table))):
        raise ValueError("The `output` does not exist or is not a table")
    try:
        table_definition = parse_table_definitions(td)
    except ValueError as e:
        raise ValueError(f"{e.args[0]} in `output` section") from e

    # JSON -> DB への変換・挿入の設定
    if (((dl := data.get("pipeline", None)) is None)
            or (not isinstance(dl, toml_items.Table))):
        raise ValueError("The `pipeline` does not exist or is not a table")
    try:
        data_link = parse_data_link(dl)
    except ValueError as e:
        raise ValueError(f"{e.args[0]} in `pipeline` section") from e

    return PipelineDefinition(table_definition, data_link)

def parse_toml_data(data: str) -> ConversionSettings:
    """TOMLデータから変換設定を解析する

    Parameters
    ----------
    data : str
        TOMLデータ

    Returns
    -------
    ConversionSettings
        変換設定

    Raises
    ------
    ValueError
        - TOMLデータが解析できない場合
        - CSV to JSON変換設定が解析できない場合
        - JSON to SQL変換設定が解析できない場合
    """
    try:
        toml_data = tomlkit.loads(data)
    except Exception as e:
        raise ValueError("Failed to parse TOML data") from e

    # CSV to JSON変換設定
    if ((csv2json := toml_data.get("csv2json", None)) is None
            or (not isinstance(csv2json, toml_items.Table))):
        raise ValueError("The `csv2json` does not exist or is not a table")
    try:
        csv2json = _parse_csv_to_json_settings(csv2json)
    except ValueError as e:
        raise ValueError(f"{e.args[0]} in `csv2json` section") from e

    # JSON to SQL変換設定
    if ((json2sql := toml_data.get("json2sql", None)) is None
            or (not isinstance(json2sql, toml_items.Table))):
        raise ValueError("The `json2sql` does not exist or is not a table")
    try:
        json2sql = _parse_json_to_sql_settings(json2sql)
    except ValueError as e:
        raise ValueError(f"{e.args[0]} in `json2sql` section") from e

    return ConversionSettings(csv2json, json2sql)

def parse_toml(file_path: str) -> ConversionSettings:
    """TOMLファイルから変換設定を解析する

    Parameters
    ----------
    file_path : str
        TOMLファイルのパス

    Returns
    -------
    ConversionSettings
        変換設定

    Raises
    ------
    FileNotFoundError
        TOMLファイルが存在しない場合
    ValueError
        - TOMLファイルが解析できない場合
        - CSV to JSON変換設定が解析できない場合
        - JSON to SQL変換設定が解析できない場合
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return parse_toml_data(f.read())
