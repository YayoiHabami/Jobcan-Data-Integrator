"""CSVファイルのデータを読み込み、JSONとして出力可能な形式に整形する

Classes
-------
- `ParsedCSVData`: CSVファイルのデータを整形したもの
  `.to_dict()`でdictに変換可能

Functions
---------
- `parse_csv_data`: CSVファイルのデータを整形する
- `parse_csv`: CSVファイルを読み込み、データを整形する
- `csv_to_raw_data_source`: 整形されたCSVデータをRawDataSourceに変換する
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
    common : OrderedDict[str, Any]
        共通項目 (フォームの種類ごとに共通)
    extends : OrderedDict[str, Any]
        追加項目 (フォームのIDごとに異なる)
    details : list[OrderedDict[str, Any]]
        明細項目 (経費精算・支払依頼フォームのみ)
    """
    common: OrderedDict[str, Any] = field(default_factory=OrderedDict)
    """共通項目 (フォームの種類ごとに共通)"""
    extends: OrderedDict[str, Any] = field(default_factory=OrderedDict)
    """追加項目 (フォームのIDごとに異なる)"""
    details: list[OrderedDict[str, Any]] = field(default_factory=list)
    """明細項目 (経費精算・支払依頼フォームのみ)"""

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
        form_type:str, form_id:int,
        titles:list[str], data:list[str],
        settings:CsvToJsonSettings,
        details: Optional[list[list[str]]]
    ) -> ParsedCSVData:
    """一つの申請書について、CSVファイルのデータを整形する

    Parameters
    ----------
    form_type : str
        フォームの種類、"general_form", "expense_form", "payment_form"のいずれか
    form_id : int
        フォームのID
    titles : list[str]
        CSVファイルのタイトル行
    data : list[str]
        CSVファイルのデータ行(1行分)
    settings : CsvToJsonSettings
        CSV->JSON読込・変換設定、`conversion_setting.toml`から読み込む
    details : Optional[list[list[str]]]
        明細項目 (経費精算・支払依頼フォームのみ).
        存在する場合はその行数分のデータを与える

    Returns
    -------
    ParsedCSVData
        整形されたデータ. 一つ目のキーは以下の通り:
        - "common": form_type毎に共通の項目 (OrderedDict)
        - "extends": 追加項目、form_id毎に異なる (OrderedDict)
        - "details": 明細項目、経費精算・支払依頼フォームのみ (list[dict])
        二つ目のキーで各項目を取得

    Raises
    ------
    ValueError
        - `conversion_settings.toml`の`csv2json`に指定されたフォームの種類が存在しない場合
        - `conversion_settings.toml`の`csv2json`の各項目で指定されたタイトル(表示名)の
          データがCSV側に存在しない場合
        - `conversion_settings.toml`の`csv2json`の各項目で指定されたデータ型が未対応の場合
    """
    ret = ParsedCSVData()

    # フォーム毎に共通の項目を取得
    forms = settings.get_form_items(form_type, remove_specifics=True)
    if not forms:
        # 指定されたフォームが存在しない場合はエラーを返す
        raise ValueError(f"Form type '{form_type}' not found in conversion_settings.toml")
    ret.common = _single_request_items(forms[0].common, titles, [data])[0]

    if (unique_form := settings.get_form_item(form_type, form_id)) is not None:
        # 追加項目を取得
        if not (extended_items := unique_form.extended):
            ret.extends = _single_request_items(extended_items, titles, [data])[0]

        # 明細項目を取得
        if (details is not None) and ((detail_items := unique_form.detail) is not None):
            ret.details = _single_request_items(detail_items, titles, details)

    return ret

def parse_csv_data(
        form_type: str, form_id: int,
        data: list[list[str]],
        settings: CsvToJsonSettings
    ) -> list[ParsedCSVData]:
    """CSVファイルのデータを整形する

    Parameters
    ----------
    form_type : str
        フォームの種類、"general_form", "expense_form", "payment_form"のいずれか
    form_id : int
        フォームのID
    data : list[list[str]]
        CSVファイルのデータ、タイトル行(1行目)を含む
    settings : CsvToJsonSettings
        CSV->JSON 読込・変換設定、`conversion_setting.toml`から読み込む

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
    """
    titles = data[0]
    ret: list[ParsedCSVData] = []

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

        ret.append(_single_request_to_json(
            form_type, form_id, titles, data_row, settings, details))

    return ret

def parse_csv(
        form_type: str, form_id: int,
        file_path: str, settings: CsvToJsonSettings
    ) -> list[ParsedCSVData]:
    """CSVファイルを読み込み、データを整形する

    Parameters
    ----------
    form_type : str
        フォームの種類、"general_form", "expense_form", "payment_form"のいずれか
    form_id : int
        フォームのID
    file_path : str
        CSVファイルのパス
    settings : CsvToJsonSettings
        CSV->JSON 読込・変換設定、`conversion_setting.toml`から読み込む

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

    return parse_csv_data(form_type, form_id, data, settings)

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
