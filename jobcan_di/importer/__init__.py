"""
importer
--------
　データベース・API以外のソースからデータを取得し、ETL (Extract, Transform, Load)
処理を行うためのパッケージです。

Classes
-------
- ConversionSettings: 変換設定を保持するクラス
  - CsvToJsonSettings: CSV -> JSON 変換設定を保持するクラス
    - CsvImportSettings: JSON -> SQL 変換設定を保持するクラス
    - FormItems: フォームの項目を保持するクラス
- ParsedCSVData: CSVデータを保持するクラス

Functions
---------
- ConversionSettingsの生成
  - parse_toml_data: TOMLデータをパースしてConversionSettingsを生成する
  - parse_toml: TOMLファイルをパースしてConversionSettingsを生成する
- CSVデータのパース
  - parse_csv_data: CSVデータをパースしてParsedCSVDataを生成する
  - parse_csv: CSVファイルをパースしてParsedCSVDataを生成する
  - csv_to_raw_data_source: ParsedCSVDataをRawDataSourceに変換する

Examples
--------
　ETL処理を定義したTOMLファイルを読み込み`ConversionSettings`を生成し、
入力 (Extract) にCSVファイルを含むETL処理を実行する例を以下に示します。

　ここで、以下で読み込むTOMLファイルは`jobcan_di/test/data/conversion_settings.toml`
であり、データソースとしてCSVファイルを含んでいます。また、CSVファイルを
どのようにデータベースに格納できる形に変換するかの定義も含まれているため、
これを元にETL処理を実行することができます。

```python
from jobcan_di.importer import parse_toml

# ETL処理を定義したTOMLファイルを読み込む
settings = parse_toml('conversion_settings.toml')
```
"""
# 変換設定 (CSV -> JSON -> SQL)
from ._conversion_settings import (
    ConversionSettings,
    CsvToJsonSettings, CsvImportSettings, FormItems,
    parse_toml_data, parse_toml
)
# CSVのパーサー (CSV -> JSON)
from ._parse_csv import (
    ParsedCSVData, parse_csv_data, parse_csv,
    csv_to_raw_data_source
)
