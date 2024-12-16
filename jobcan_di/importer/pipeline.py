"""CSVファイルをデータソースとして追加したパイプライン定義を生成する関数を提供するモジュール

Functions
---------
- merge_csv_as_data_source: CSVファイルをデータソースとしてパイプライン定義にマージする
- extract_data_source: CSVファイルからデータをDataSourceとして抽出する

Examples
--------

```python
from jobcan_di.database.data_pipeline.pipeline import execute_etl_pipeline
from jobcan_di.importer import parse_toml
from jobcan_di.importer.pipeline import merge_csv_as_data_source

# パイプライン定義をTOMLファイルから読み込む
c_settings = parse_toml("path/to/conversion_settings.toml")
pipeline_def = c_settings.json2sql

# CSVファイルをデータソースとしてパイプライン定義にマージする
pipeline_def = merge_csv_as_data_source(pipeline_def, c_settings.csv2json)

# ETL処理を実行
execute_etl_pipeline(pipeline_def)
```
"""
from collections import OrderedDict
from copy import deepcopy
from typing import Optional

from jobcan_di.database.data_pipeline import (
    RawDataSource, SourceResultFormat, ParameterConversionMethod,
    PipelineDefinition
)
from jobcan_di.database.data_pipeline.transformation import convert_data_type_specific
from jobcan_di.importer import CsvToJsonSettings, parse_csv, ParsedCSVData
from ._file_picker import pick_files


def merge_csv_as_data_source(definition: PipelineDefinition,
                             settings: CsvToJsonSettings) -> PipelineDefinition:
    """CSVファイルをデータソースとしてPipelineDefinitionにマージする

    Parameters
    ----------
    definition : PipelineDefinition
        パイプライン定義、TOMLから読み込んだConversionSettingsの`.json2sql`を指定
    settings : CsvToJsonSettings
        CSVファイルの設定、TOMLから読み込んだConversionSettingsの`.csv2json`を指定

    Returns
    -------
    PipelineDefinition
        データソースをマージしたパイプライン定義

    Raises
    ------
    """
    copied = deepcopy(definition)

    # データソースを抽出
    sources = extract_data_source(settings)

    # データソースをマージ
    for source in sources:
        if not copied.data_link.add_source(source):
            # 同名のデータソースが複数存在する場合はエラー
            raise ValueError(f"Duplicate data source name: '{source.name}' (from CSV files)")

    return copied

def extract_data_source(settings: CsvToJsonSettings) -> list[RawDataSource]:
    """CSVファイルからデータをDataSourceとして抽出する

    Parameters
    ----------
    settings : CsvToJsonSettings
        CSVファイルの設定、TOMLから読み込んだConversionSettingsの`.csv2json`を指定

    Returns
    -------
    list[RawDataSource]
        抽出したデータソースのリスト
    """
    import_settings = settings.csv_import_settings
    files = pick_files(import_settings.folder, import_settings.file_name_regex)

    sources = []
    unnamed_count = 1
    for form_name, file_paths in files.items():
        parsed: list[ParsedCSVData] = []
        for file_path in file_paths:
            # 1つのCSVファイルを読み込む
            data = parse_csv(file_path, settings, form_name=form_name)
            if not data[0]:
                continue

            # データを結合する
            if (p := _merge_csv_data_sources(parsed, data[0])) is None:
                raise ValueError(
                    f"The CSV file '{file_path}' has different columns from " \
                    f"the other {form_name} CSV files"
                )
            parsed = p

        # データソースに変換
        if not parsed:
            continue
        form_uk = settings.get_form_unique_key(form_name)
        if (form_uk is not None) or import_settings.enable_auto_form_detection:
            source_name = f"csv2json.{parsed[0].form_type}." \
                        + (form_uk or f'unnamed_{unnamed_count}')
            sources.append(RawDataSource(
                source_name, SourceResultFormat.MULTIPLE_JSON_ENTRIES,
                "", data = [p.to_dict() for p in parsed]
            ))
            unnamed_count += 1
            print(source_name, form_name)#, "  ---  ", list(parsed[0].titles["common"].values()))

    return sources

def _is_sublist_either_way(x: list, y: list) -> bool:
    """リストxとyのいずれかがもう一方の部分リストかどうかを判定する

    Parameters
    ----------
    x : list
        リストx
    y : list
        リストy

    Returns
    -------
    bool
        いずれかがもう一方の部分リストの場合True (x ⊂ y or y ⊂ x)
    """
    if not x or not y:
        # どちらかが空リストの場合は常にTrue
        return True

    # より短いリストを部分列の候補として扱う
    if len(x) < len(y):
        longer, shorter = y, x
    else:
        longer, shorter = x, y

    for shorter_i in shorter:
        if shorter_i not in longer:
            return False

    return True

def _merge_csv_data_sources(sources1:list[ParsedCSVData],
                            sources2:list[ParsedCSVData]) -> Optional[list[ParsedCSVData]]:
    """2つのCSVデータソースをマージする

    Parameters
    ----------
    sources1 : list[ParsedCSVData]
        CSVデータソース1
    sources2 : list[ParsedCSVData]
        CSVデータソース2

    Returns
    -------
    list[ParsedCSVData]
        マージしたCSVデータソース、
        項目名が包含関係になくマージできない場合はNone
    """
    if (not sources1) or (not sources2):
        # どちらかが空リストの場合はマージ不要
        return sources1 or sources2

    # 共通項目の項目名が一致するか確認
    if not set(sources1[0].titles["common"].values()) == set(sources2[0].titles["common"].values()):
        # 共通項目の項目名が一致しない場合はマージ不可
        return None

    merged: list[ParsedCSVData] = [deepcopy(s) for s in sources1] \
                                + [deepcopy(s) for s in sources2]

    for key in ["extends", "details"]:
        # 追加/明細項目が包含関係になっているか確認
        if not _is_sublist_either_way(list(sources1[0].titles[key].values()),
                                      list(sources2[0].titles[key].values())):
            # 項目が包含関係になっていない場合はマージ不可
            print(f"s1: {sources1[0].titles[key].keys()} \ns2: {sources2[0].titles[key].keys()}")
            return None
        n_key_1 = len(sources1[0].titles[key])
        n_key_2 = len(sources2[0].titles[key])
        if n_key_1 > n_key_2:
            _extend_items(merged[:len(sources1)], key, sources2[0])
        elif n_key_1 < n_key_2:
            _extend_items(merged[len(sources1):], key, sources1[0])

    return merged

def _extend_items(data:list[ParsedCSVData], key:str, ref_data:ParsedCSVData) -> None:
    """CSVデータの項目を拡張する

    Parameters
    ----------
    data : list[ParsedCSVData]
        CSVデータ
    key : str
        拡張する項目のキー、"extends"または"details"
    ref_data : ParsedCSVData
        拡張する項目

    Notes
    -----
    - ""をconvert_data_type_specificに渡した値で追加項目を埋める
    """
    _extend_titles(data, key, ref_data.titles[key])
    _extend_dtypes(data, key, ref_data.dtypes[key])
    if key == "extends":
        _extend_extended_items(data, ref_data.titles[key], ref_data.dtypes[key])
    elif key == "details":
        _extend_detail_items(data, ref_data.titles[key], ref_data.dtypes[key])

def _extend_titles(data:list[ParsedCSVData], key:str, titles:dict[str, str]) -> None:
    """CSVデータの項目名を拡張する

    Parameters
    ----------
    data : list[ParsedCSVData]
        CSVデータ
    key : str
        拡張する項目名のキー
    titles : dict[str, str]
        拡張する項目名
    """
    for d in data:
        d.titles[key] = deepcopy(titles)

def _extend_dtypes(data:list[ParsedCSVData], key:str, dtypes:dict[str, ParameterConversionMethod]):
    """CSVデータのデータ型を拡張する

    Parameters
    ----------
    data : list[ParsedCSVData]
        CSVデータ
    key : str
        拡張するデータ型のキー
    dtypes : dict[str, ParameterConversionMethod]
        拡張するデータ型
    """
    for d in data:
        d.dtypes[key] = deepcopy(dtypes)

def _extend_extended_items(data:list[ParsedCSVData],
                           titles: dict[str, str],
                           dtypes:dict[str, ParameterConversionMethod]) -> None:
    """CSVデータの追加項目を拡張する

    Parameters
    ----------
    data : list[ParsedCSVData]
        CSVデータ
    titles : dict[str, str]
        拡張後の追加項目の表示名(CSVのタイトル列)
    dtypes : dict[str, ParameterConversionMethod]
        拡張後の各項目のデータの型

    Notes
    -----
    - ""をconvert_data_type_specificに渡した値で追加項目を埋める
    """
    titles_diff = set(titles.values()) - set(data[0].extends.values())
    title2key = {v: k for k, v in titles.items()}

    for d in data:
        new_extends = OrderedDict()
        for key, title in titles.items():
            if title in titles_diff:
                # 存在しない内容の追加項目は空文字列からの変換で埋める
                new_extends[title2key[title]] = convert_data_type_specific(
                    "", dtypes[title2key[title]]
                )
            else:
                # dataに存在する項目について、JSONキーを列数が大きい方に合わせて拡張
                # Excel形式で自動命名する場合、タイトルとキーが異なる可能性があるため
                new_extends[title2key[title]] = d.extends[key]

        d.extends = new_extends

def _extend_detail_items(data:list[ParsedCSVData],
                         titles: dict[str, str],
                         dtypes:dict[str, ParameterConversionMethod]) -> None:
    """CSVデータの詳細項目を拡張する

    Parameters
    ----------
    data : list[ParsedCSVData]
        CSVデータ
    titles : dict[str, str]
        拡張後の詳細項目の表示名(CSVのタイトル列)
    dtypes : dict[str, ParameterConversionMethod]
        拡張後の各項目のデータの型

    Notes
    -----
    - ""をconvert_data_type_specificに渡した値で詳細項目を埋める
    """
    titles_diff = set(titles.values()) - set(data[0].details[0].keys())
    title2key = {v: k for k, v in titles.items()}

    for d in data:
        for i, d_item in enumerate(d.details):
            new_details = OrderedDict()
            for key, title in titles.items():
                if title in titles_diff:
                    # 存在しない内容の詳細項目は空文字列からの変換で埋める
                    new_details[title2key[title]] = convert_data_type_specific(
                        "", dtypes[title2key[title]]
                    )
                else:
                    # dataに存在する項目について、JSONキーを列数が大きい方に合わせて拡張
                    # Excel形式で自動命名する場合、タイトルとキーが異なる可能性があるため
                    new_details[title2key[title]] = d_item[key]

            d.details[i] = new_details
