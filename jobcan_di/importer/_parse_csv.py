"""CSVファイルのデータを読み込み、JSONとして出力可能な形式に整形する

Classes
-------
- `ParsedCSVData`: CSVファイルのデータを整形したもの
  `.to_dict()`でdictに変換可能

Functions
---------
- ヘルパー
  - `classify_form_type`: フォームの種類を判定する
  - `excel_type_column_name`: 列番号からExcelの列名を取得する
  - `extract_additional_items`: 追加・明細項目を自動判定・取得する
- `parse_csv_data`: CSVファイルのデータを整形する
- `parse_csv`: CSVファイルを読み込み、データを整形する
- `csv_to_raw_data_source`: 整形されたCSVデータをRawDataSourceに変換する

Examples
--------
CSVファイルを読み込み、データを整形する例を以下に示します。

ここで上記CSVに対応するフォームの詳細な記述がconversion_settings.tomlに存在しない場合、
すなわち対応する`[form_items.<form_type>.<form_unique_key>]`が存在しない場合、
項目の自動判定・取得を行います。このため、`extended_items`と`detail_items`は自動判定された
項目 (例: `[["追加項目1", "W", "", ""], ...]`) が格納されます。この際、データ型とコメントは
空文字列で初期化され、JSONキーはExcelにCSVを読み込んだ際の列名 (A, B, C, ..., AA, AB, ...)
となります。

```python
from jobcan_di.importer import parse_csv, parse_toml

# conversion_settings.tomlから設定を読み込む
settings = parse_toml("conversion_settings.toml")

# CSVファイルを読み込み、データを整形する
csv_path = "path/to/csv_file.csv"
data, extended_items, detail_items = parse_csv(csv_path, settings)
```
"""
from collections import OrderedDict
import csv
from dataclasses import dataclass, field
import os
from typing import Any, Optional

from jobcan_di.database.data_pipeline import (
    ParameterConversionMethod,
    RawDataSource, SourceResultFormat
)
from jobcan_di.database.data_pipeline.transformation import convert_data_type_specific

from ._conversion_settings import CsvToJsonSettings



@dataclass
class ParsedCSVData:
    """CSVファイルのデータを整形したもの

    Attributes
    ----------
    form_type : str
        フォームの種類; "general_form", "expense_form", "payment_form"のいずれか
    common : OrderedDict[str, Any]
        共通項目 (フォームの種類ごとに共通)
    extends : OrderedDict[str, Any]
        追加項目 (フォームのIDごとに異なる)
    details : list[OrderedDict[str, Any]]
        明細項目 (経費精算・支払依頼フォームのみ)
    """
    form_type: str = ""
    """フォームの種類; "general_form", "expense_form", "payment_form"のいずれか"""
    common: OrderedDict[str, Any] = field(default_factory=OrderedDict)
    """共通項目 (フォームの種類ごとに共通)"""
    extends: OrderedDict[str, Any] = field(default_factory=OrderedDict)
    """追加項目 (フォームのIDごとに異なる)"""
    details: list[OrderedDict[str, Any]] = field(default_factory=list)
    """明細項目 (経費精算・支払依頼フォームのみ)"""

    titles: dict[str, dict[str, str]] = field(
        default_factory=lambda: {"common": dict(), "extends": dict(), "details": dict()}
    )
    """各項目の表示名、"common", "extends", "details"の各項目に対して表示名を格納

    titles["common"]["json_key"] = "表示名"
    """
    dtypes: dict[str, dict[str, ParameterConversionMethod]] = field(
        default_factory=lambda: {"common": dict(), "extends": dict(), "details": dict()}
    )
    """各項目のデータ型、"common", "extends", "details"の各項目に対してデータ型を格納

    dtypes["common"]["json_key"] = ParameterConversionMethod
    """

    def to_dict(self) -> dict[str, Any]:
        """dictに変換する

        Returns
        -------
        dict[str, Any]
            dictに変換されたデータ, OrderedDictをdictに変換したもの
        """
        return {
            "common": dict(self.common),
            "extends": dict(self.extends),
            "details": [dict(d) for d in self.details]
        }

#
# ヘルパー関数
#

def classify_form_type(
        titles: list[str], settings: CsvToJsonSettings,
        *,
        form_name: Optional[str] = None,
        auto_detect: bool = True
    ) -> Optional[str]:
    """フォームの種類を判定する

    Parameters
    ----------
    titles : list[str]
        CSVファイルのタイトル行
    settings : CsvToJsonSettings
        CSV->JSON読込・変換設定、`conversion_setting.toml`から読み込む
        この`get_form_types`メソッドで取得できるフォームの種類を判定する
    form_name : Optional[str]
        フォーム名、指定された名称がsettingsに存在する場合はそのフォームの種類を返す
    auto_detect : bool
        フォームの種類を自動判定するかどうか

    Returns
    -------
    str
        フォームの種類、settings.get_form_types()で取得できるフォームの種類のいずれか
        (基本的には"general_form", "expense_form", "payment_form"のいずれか)
        対応するフォームが存在しない場合はNone

    Notes
    -----
    - タイトル行の冒頭数列分（共通項目の数分、"コメント"除く）が共通項目の表示名と一致するか判定する
    - 要素が一致していれば順番は問わない
    - 一致するフォームが複数存在する場合は、一致した項目数が最も多いフォームを返す
      (general_formが優先されないようにする)
    """
    if (form_type := settings.get_form_type(form_name=form_name)) is not None:
        # 指定されているform_nameに対応するフォームの種類が存在する場合はそのまま返す
        return form_type
    elif not auto_detect:
        # フォームの種類を自動判定しない場合はNoneを返す
        return None

    # 冒頭部分が共通項目の表示名と一致したform_typeの (一致したタイトル数, form_type) のリスト
    matched_forms: list[tuple[int, str]] = []

    for form_type in settings.get_form_types():
        # form_typeに対応するフォームの、共通項目のみを取得する
        item = settings.get_form_items(form_type, remove_specifics=True)[0]

        # タイトル行に対応する、共通項目の表示名を取得
        # 末尾のコメント列は連続しないケースがあるため、コメント列がある場合は除外する
        common_titles = [i[0] for i in item.common]
        common_titles = common_titles[:-1] if common_titles[-1] == "コメント" else common_titles

        # タイトル行の冒頭部分が共通項目の表示名と一致するか判定
        if set(titles[:len(common_titles)]) == set(common_titles):
            matched_forms.append((len(common_titles), form_type))

    # 一致した項目数が最も多いものを返す
    if matched_forms:
        return max(matched_forms, key=lambda x: x[0])[1]
    # フォームの種類が見つからない場合はNoneを返す
    return None

def excel_type_column_name(num: int) -> str:
    """列番号 (0始まり) からExcelの列名を取得する

    Parameters
    ----------
    num : int
        列番号 (0始まり)

    Returns
    -------
    str
        Excelの列名, (A, B, ..., Z, AA, AB, ..., ZZ, AAA, AAB, ...)
        0 -> A, 1 -> B, ..., 25 -> Z, 26 -> AA, 27 -> AB, ...
    """
    if num < 26:
        return chr(ord("A") + num)
    else:
        return excel_type_column_name(num // 26 - 1) + excel_type_column_name(num % 26)

def extract_additional_items(
        titles: list[str], common_items: list[list[str]],
    ) -> tuple[list[list[str]], list[list[str]]]:
    """追加・明細項目を自動判定・取得する

    Parameters
    ----------
    titles : list[str]
        CSVファイルのタイトル行
    common_items : list[list[str]]
        フォーム毎に共通の項目、末尾の表示名が"コメント"であることが前提.
        それぞれのリストは、表示名・JSONキー・データ型・コメントの順で格納される

    Returns
    -------
    tuple[list[list[str]], list[list[str]]]
        追加項目と明細項目のタイトル行のリスト.
        それぞれのリストは、表示名・JSONキー・データ型・コメントの順で格納される.
        自動生成のため、データ型・コメントは空文字列で初期化される.また、JSONキーは
        ExcelにCSVを読み込んだ際の列名 (A, B, C, ..., AA, AB, ...) となる.

    Raises
    ------
    ValueError
        - 共通項目が空、または末尾が"コメント"でない場合
        - タイトル行の冒頭部分が共通項目の表示名と一致しない場合 ("コメント"を除く)
    """
    if not common_items or common_items[-1][0] != "コメント":
        # 共通項目が空、または末尾が"コメント"でない場合はエラーを返す
        raise ValueError("The last item of common_items must be 'コメント'")
    # 末尾の"コメント"を除いた共通項目の表示名を取得
    common_titles = [i[0] for i in common_items][:-1]

    # タイトル行の冒頭部分が共通項目の表示名と一致することを確認
    if set(titles[:len(common_titles)]) != set(common_titles):
        raise ValueError("The title line does not match the common items")

    # 共通項目列以降、"コメント"列以前の列を追加項目として取得
    if "コメント" not in titles:
        raise ValueError("The title line must contain 'コメント'")
    comment_index = titles.index("コメント")
    extended_items = []
    for i in range(len(common_titles), comment_index):
        json_key = excel_type_column_name(i)
        extended_items.append([titles[i], json_key, "", ""])

    # "コメント"列以降の列を明細項目として取得
    detail_items = []
    for i in range(comment_index + 1, len(titles)):
        json_key = excel_type_column_name(i)
        detail_items.append([titles[i], json_key, "", ""])

    return extended_items, detail_items


#
# パーサー
#

def _single_request_items(
        common_items: list[list[str]],
        titles:list[str], data:list[list[str]]
    ) -> list[OrderedDict[str, Any]]:
    """一つの申請書について、CSVファイルのデータを整形する

    Parameters
    ----------
    common_items : list[list[str]]
        フォーム毎に共通の項目
    titles : list[str]
        CSVファイルのタイトル行
    data : list[list[str]]
        CSVファイルのデータ行
        1行で完結する場合も list[list[str]] として与える

    Returns
    -------
    list[OrderedDict[str, Any]]
        整形されたデータ. 各要素のキーはJSONキー、値はデータ.
        `common_item`で指定されたキーが存在しない場合は`None`を返す

    Raises
    ------
    ValueError
        - タイトルが存在しない場合
        - 未対応のデータ型が指定された場合

    Notes
    -----
    - 1行で完結するデータ (共通項目・追加項目) は、`data`に1行分のデータを与え、0番目の要素を取得する
        >>> _single_request_items(common_items, titles, [data])[0]
    """
    ret = []
    for data_i in data:
        ret_i = OrderedDict()

        for item in common_items:
            title, key, data_type, _ = item

            # title に相当する位置の data_i のデータを取得
            try:
                _data = data_i[titles.index(title)]
            except ValueError:
                # タイトルが存在しない場合はエラーを返す
                raise ValueError(f"Title '{title}' not found in CSV file")

            # データ型を変換
            # data_typeはParameterConversionMethodに変換できることを検証済み: TOML読込時)
            # ただしdata_typeが空文字列の場合は変換しない
            if data_type != "":
                conv_method = ParameterConversionMethod[data_type]
                ret_i[key] = convert_data_type_specific(_data, conv_method)
            else:
                ret_i[key] = _data
        ret.append(ret_i)

    return ret

def _single_request_to_json(
        form_type:str,
        titles:list[str], data:list[str],
        settings:CsvToJsonSettings,
        details: Optional[list[list[str]]],
        *,
        form_unique_key: Optional[str] = None,
        form_name: Optional[str] = None
    ) -> tuple[ParsedCSVData, list[list[str]], list[list[str]]]:
    """一つの申請書について、CSVファイルのデータを整形する

    Parameters
    ----------
    form_type : str
        フォームの種類、"general_form", "expense_form", "payment_form"のいずれか
    titles : list[str]
        CSVファイルのタイトル行
    data : list[str]
        CSVファイルのデータ行(1行分)
    settings : CsvToJsonSettings
        CSV->JSON読込・変換設定、`conversion_setting.toml`から読み込む
    details : Optional[list[list[str]]]
        明細項目 (経費精算・支払依頼フォームのみ).
        存在する場合はその行数分のデータを与える
    form_unique_key : Optional[str]
        form_unique_keyとform_nameのいずれかを指定する.
        フォームのID、追加・明細項目を取得する際に使用する.
        TOMLファイルの [csv2json.form_items.<form_type>.<form_unique_key>] に対応する
    form_name : Optional[str]
        form_unique_keyとform_nameのいずれかを指定する.
        フォームの種類、追加・明細項目を取得する際に使用する.

    Returns
    -------
    ParsedCSVData
        整形されたデータ. 一つ目のキーは以下の通り:
        - "common": form_type毎に共通の項目 (OrderedDict)
        - "extends": 追加項目、form_id毎に異なる (OrderedDict)
        - "details": 明細項目、経費精算・支払依頼フォームのみ (list[dict])
        二つ目のキーで各項目を取得
    list[list[str]]
        追加項目のタイトル行のリスト、項目の自動判定を行った場合は判定された項目が格納される.
        外側のリストの各要素は [表示名, JSONキー, データ型, コメント] .
    list[list[str]]
        明細項目のタイトル行のリスト、項目の自動判定を行った場合は判定された項目が格納される.
        外側のリストの各要素は [表示名, JSONキー, データ型, コメント] .

    Raises
    ------
    ValueError
        - `conversion_settings.toml`の`csv2json`に指定されたフォームの種類が存在しない場合
        - `conversion_settings.toml`の`csv2json`の各項目で指定されたタイトル(表示名)の
          データがCSV側に存在しない場合
        - `conversion_settings.toml`の`csv2json`の各項目で指定されたデータ型が未対応の場合
        - 追加・明細項目の自動判定に失敗した場合
    """
    ret = ParsedCSVData(form_type=form_type)

    # フォーム毎に共通の項目を取得
    forms = settings.get_form_items(form_type, remove_specifics=True)
    if not forms:
        # 指定されたフォームが存在しない場合はエラーを返す
        raise ValueError(f"Form type '{form_type}' not found in conversion_settings.toml")
    ret.common = _single_request_items(forms[0].common, titles, [data])[0]
    ret.titles["common"] = {i[1]: i[0] for i in forms[0].common}
    ret.dtypes["common"] = {i[1]: ParameterConversionMethod[i[2] or "TO_STRING"]
                            for i in forms[0].common}

    unique_form = None
    extended_items, detail_items = [], []
    if (form_unique_key is not None) or (form_name is not None):
        # フォームのID or フォームの種類が指定されている場合は、追加・明細項目を取得
        unique_form = settings.get_form_item(form_type,
                                             form_unique_key=form_unique_key,
                                             form_name=form_name)
    if unique_form is not None:
        # conversion_settings上に定義済みの追加・明細項目が存在する場合
        extended_items = unique_form.extended
        detail_items = unique_form.detail
    else:
        # conversion_settings上に定義済みの追加・明細項目が存在しない場合
        # ファイル構造から追加・明細項目を自動判定・取得する
        try:
            extended_items, detail_items = extract_additional_items(titles, forms[0].common)
        except ValueError as e:
            # 追加・明細項目の自動判定に失敗した場合はエラーを返す
            raise ValueError(f"Failed to extract extended and detail items: {e}") from e

    # 追加項目を取得
    if extended_items is not None:
        ret.extends = _single_request_items(extended_items, titles, [data])[0]
        ret.titles["extends"] = {i[1]: i[0] for i in extended_items}
        ret.dtypes["extends"] = {i[1]: ParameterConversionMethod[i[2] or "TO_STRING"]
                                 for i in extended_items}

    # 明細項目を取得
    if (details is not None) and (detail_items is not None):
        ret.details = _single_request_items(detail_items, titles, details)
        ret.titles["details"] = {i[1]: i[0] for i in detail_items}
        ret.dtypes["details"] = {i[1]: ParameterConversionMethod[i[2] or "TO_STRING"]
                                 for i in detail_items}

    return ret, extended_items, detail_items

def parse_csv_data(
        data: list[list[str]], settings: CsvToJsonSettings,
        *,
        form_unique_key: Optional[str] = None,
        form_name: Optional[str] = None
    ) -> tuple[list[ParsedCSVData], list[list[str]], list[list[str]]]:
    """CSVファイルのデータを整形する

    Parameters
    ----------
    data : list[list[str]]
        CSVファイルのデータ、タイトル行(1行目)を含む
    settings : CsvToJsonSettings
        CSV->JSON 読込・変換設定、`conversion_setting.toml`から読み込む
    form_unique_key : Optional[str]
        フォームのID、追加・明細項目を取得する際に使用する.
        TOMLファイルの [csv2json.form_items.<form_type>.<form_unique_key>] に対応する
    form_name : Optional[str]
        フォームの種類、追加・明細項目を取得する際に使用する.
    list[list[str]]
        追加項目のタイトル行のリスト、項目の自動判定を行った場合は判定された項目が格納される.
        外側のリストの各要素は [表示名, JSONキー, データ型, コメント] .
    list[list[str]]
        明細項目のタイトル行のリスト、項目の自動判定を行った場合は判定された項目が格納される.
        外側のリストの各要素は [表示名, JSONキー, データ型, コメント] .

    Returns
    -------
    list[ParsedCSVData]
        整形されたデータ. 一つ目のキーは以下の通り:
        - "common": form_type毎に共通の項目
        - "extends": 追加項目、form_id毎に異なる
        - "details": 明細項目、経費精算・支払依頼フォームのみ
        二つ目のキーで各項目を取得

    Raises
    ------
    ValueError
        - `conversion_settings.toml`の`csv2json`に指定されたフォームの種類が存在しない場合
        - `conversion_settings.toml`の`csv2json`の各項目で指定されたタイトル(表示名)の
          データがCSV側に存在しない場合
        - `conversion_settings.toml`の`csv2json`の各項目で指定されたデータ型が未対応の場合
        - 追加・明細項目の自動判定に失敗した場合

    Notes
    -----
    - `form_unique_key`と`form_name`のどちらも指定しない場合、または指定したフォームの記述が
      `conversion_settings.toml`に存在しない場合は、追加・明細項目を自動判定・取得する
    - 追加・明細項目の自動判定を行わない際に、form_nameが指定されていない場合は空のデータを返す
    """
    titles = data[0]
    auto_detect = settings.csv_import_settings.enable_auto_form_detection
    form_type = classify_form_type(titles, settings,
                                   form_name=form_name,auto_detect=auto_detect)
    if (form_type is None) and (not auto_detect):
        # フォームの種類を自動判定しない場合に、フォームの種類が見つからない場合は空のデータを返す
        return [], [], []
    if form_type is None:
        # フォームの種類が見つからない場合はエラーを返す
        # (settingsで指定されたいずれのフォームにも該当しない場合)
        raise ValueError("The elements of the title line do not correspond to " \
                         "any of the forms defined in the CSV to JSON configuration. " \
                         "The title of the first few columns did not exactly match " \
                         f"the common items. Title: {titles}")

    ret: list[ParsedCSVData] = []
    extended_items, detail_items = [], []

    i = 0
    while i + 1 < len(data):
        # 一つの申請書について、CSVファイルのデータを整形
        i += 1
        data_row = data[i]

        # 次の行以降を見て、1列目の要素が空文字列であればdetailsに追加
        # - 1列目は申請書ID
        # - 明細項目以外のデータは、1列目が空文字列ではない行に格納される
        # - その行に続けて明細項目が続く場合があり、その場合明細項目以外の行は空文字列となる
        # - このため、1列目が空ではない行に続く、1列目が空の行を明細項目として取得する
        details = []
        while i + 1 < len(data) and data[i + 1][0] == "":
            i += 1
            details.append(data[i])

        parsed, extended_items, detail_items = _single_request_to_json(
            form_type, titles, data_row, settings, details,
            form_unique_key=form_unique_key, form_name=form_name
        )

        ret.append(parsed)

    return ret, extended_items, detail_items

def parse_csv(
        file_path: str, settings: CsvToJsonSettings,
        *,
        form_unique_key: Optional[str] = None,
        form_name: Optional[str] = None
    ) -> tuple[list[ParsedCSVData], list[list[str]], list[list[str]]]:
    """CSVファイルを読み込み、データを整形する

    Parameters
    ----------
    file_path : str
        CSVファイルのパス
    settings : CsvToJsonSettings
        CSV->JSON 読込・変換設定、`conversion_setting.toml`から読み込む
    form_unique_key : str
        フォームのID、追加・明細項目を取得する際に使用する.
        TOMLファイルの [csv2json.form_items.<form_type>.<form_unique_key>] に対応する
    form_name : str
        フォームの種類、追加・明細項目を取得する際に使用する.
    list[list[str]]
        追加項目のタイトル行のリスト、項目の自動判定を行った場合は判定された項目が格納される.
        外側のリストの各要素は [表示名, JSONキー, データ型, コメント] .
    list[list[str]]
        明細項目のタイトル行のリスト、項目の自動判定を行った場合は判定された項目が格納される.
        外側のリストの各要素は [表示名, JSONキー, データ型, コメント] .

    Returns
    -------
    list[ParsedCSVData]
        整形されたデータ. 一つ目のキーは以下の通り:
        - "common": form_type毎に共通の項目
        - "extends": 追加項目、form_id毎に異なる
        - "details": 明細項目、経費精算・支払依頼フォームのみ
        二つ目のキーで各項目を取得

    Raises
    ------
    ValueError
        - `conversion_settings.toml`の`csv2json`に指定されたフォームの種類が存在しない場合
        - `conversion_settings.toml`の`csv2json`の各項目で指定されたタイトル(表示名)の
          データがCSV側に存在しない場合
        - `conversion_settings.toml`の`csv2json`の各項目で指定されたデータ型が未対応の場合
        - 追加・明細項目の自動判定に失敗した場合

    Notes
    -----
    - `form_unique_key`と`form_name`のどちらも指定しない場合、または指定したフォームの記述が
      `conversion_settings.toml`に存在しない場合は、追加・明細項目を自動判定・取得する
    - 追加・明細項目の自動判定を行わない際に、form_nameが指定されていない場合は空のデータを返す
    """
    # Windowsの場合、クォートされた文字列内の改行に余分な\rが追加されないようにする
    newline = "" if os.name == "nt" else None

    with open(file_path, "r",
              encoding= settings.csv_import_settings.encoding,
              newline= newline) as f:
        data = [row for row in csv.reader(f,
                    delimiter= settings.csv_import_settings.delimiter,
                    quotechar= settings.csv_import_settings.quotechar
                )]

    return parse_csv_data(data, settings,
                          form_unique_key=form_unique_key,
                          form_name=form_name)

#
# データソース型への変換
#

def csv_to_raw_data_source(
        source_name: str, data: list[ParsedCSVData]
    ) -> RawDataSource:
    """整形されたCSVデータをRawDataSourceに変換する

    Parameters
    ----------
    source_name : str
        データソース名、ほかのデータソースと重複しないこと
    data : list[ParsedCSVData]
        整形されたCSVデータ

    Returns
    -------
    RawDataSource
        変換されたデータソース
    """
    return RawDataSource(
        source_name,
        SourceResultFormat.MULTIPLE_JSON_ENTRIES,
        results_key= "",
        data= [d.to_dict() for d in data]
    )
