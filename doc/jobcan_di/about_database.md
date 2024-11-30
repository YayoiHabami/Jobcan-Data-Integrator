# `jobcan_di/database`

## 目次

- [目次](#目次)
- [`schema_toolkit`](#schema_toolkit)
  - [`schema_toolkit`: データベースの構造を保持するためのクラス群を提供するパッケージ](#schema_toolkit-データベースの構造を保持するためのクラス群を提供するパッケージ)
  - [`schema_toolkit.sql_parser`: SQL文からデータベースの構造を取得するための関数群を提供するモジュール](#schema_toolkitsql_parser-sql文からデータベースの構造を取得するための関数群を提供するモジュール)
  - [`schema_toolkit.validator`: データベースの構造を検証するための関数群を提供するモジュール](#schema_toolkitvalidator-データベースの構造を検証するための関数群を提供するモジュール)
- [`data_pipeline`](#data_pipeline)
  - [概要](#概要)
  - [`data_pipeline`: データの取得方法・DBへの書き込み方法を保持するクラス群を提供するパッケージ](#data_pipeline-データの取得方法dbへの書き込み方法を保持するクラス群を提供するパッケージ)
  - [`data_pipeline.parser`: TOMLファイルから`PipelineDefinition`を取得するための関数群を提供するモジュール](#data_pipelineparser-tomlファイルからpipelinedefinitionを取得するための関数群を提供するモジュール)
  - [`data_pipeline.pipeline`: ETL処理を行うための関数群を提供するモジュール](#data_pipelinepipeline-etl処理を行うための関数群を提供するモジュール)

## `schema_toolkit`

　このパッケージは、データベースの構造を管理・検証するための関数群を提供します。大きく以下の3つの機能を提供します。

1. データベースの構造を保持するためのクラス
2. SQL文からデータベースの構造を取得するための関数
3. データベースの構造を検証するための関数

### `schema_toolkit`: データベースの構造を保持するためのクラス群を提供するパッケージ

| | クラス名 | 機能 |
| --- | --- | --- |
| メイン | `TableStructure` | テーブルの構造を保持するクラス |
| サブ | `ColumnStructure` | カラムの構造を保持するクラス |
| ^ | `SQLDialect` | どのSQL方言のものかを保持する列挙型 |

### `schema_toolkit.sql_parser`: SQL文からデータベースの構造を取得するための関数群を提供するモジュール

　このモジュールは、SQL文からデータベースの構造を取得するための関数 `parse_sql` を提供します。

> 現在は `CREATE TABLE` 文のみに対応しています。

```python
from jobcan_di.database.schema_toolkit.sql_parser import parse_sql

sqlite_stat = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER
);
"""

tables = parse_sql(sqlite_stat)
```

<details><summary>【詳細】</summary><div>

上記の例の場合、`tables` は要素数が1の`TableStructure`クラスのリストとなります。`tables[0]`には以下のような構造が格納されます。

```python
TableStructure(
    name='users',
    columns=[
        ColumnStructure(
            name='id',
            ttype='INTEGER',
            not_null=True,
            autoincrement=True
        ),
        ColumnStructure(
            name='name',
            ttype='TEXT',
            not_null=True
        ),
        ColumnStructure(
            name='age',
            ttype='INTEGER'
        )
    ],
    unique_keys = [],
    primary_keys = ['id'],
    raw_sql=sqlite_stat
)
```

</div></details>

### `schema_toolkit.validator`: データベースの構造を検証するための関数群を提供するモジュール

　このモジュールは、データベースの構造を検証するための `check_table_structure` 関数を提供します。

> 現在はSQLiteのみに対応しています。

```python
import sqlite3

from jobcan_di.database.schema_toolkit.validator import check_table_structure

with sqlite3.connect('example.db') as conn:
    # データベースの構造が一致している場合Noneが返る
    err = check_table_structure(conn, tables[0])
```

## `data_pipeline`

### 概要

　`data_pipeline` は、ETL処理を行うための関数・クラス群を提供するパッケージです。ここで、ETL処理とは、データの取得（Extract）、加工（Transform）、DBへの書き込み（Load）を行う処理のことを指します。

　本パッケージで使用する、主要な関数・クラスは以下の通りです。

| モジュール | 関数・クラス名 | 機能 |
| --- | --- | --- |
| `data_pipeline` | `PipelineDefinition` | ETL処理を定義するためのクラスです。<br>　書き込み (Load) 先のDB・テーブルを定義する `table_definition` メンバと、実際のETL処理の定義を保持する `data_link` メンバから構成されます。 |
| ^ | `DataLink` | ETL処理の定義を保持するクラスです。<br>　データの取得方法 (`sources`メンバ) 、データの加工・書込方法 (`insertion_profiles`メンバ) を保持します。 |
| ^ | `DataSource` | データの取得方法を保持するクラスです。<br>　`extract_data` メソッドによりデータを取得 (extract) します。 |
| `data_pipeline.parser` | `parse_toml` / `parse_toml_data` | TOMLファイルのパス / データの文字列から `PipelineDefinition` を取得します。 |
| `data_pipeline.pipeline` | `execute_data_pipeline` | `PipelineDefinition` のインスタンスをもとに、ETL 処理を行います。 |

### `data_pipeline`: データの取得方法・DBへの書き込み方法を保持するクラス群を提供するパッケージ

### `data_pipeline.parser`: TOMLファイルから`PipelineDefinition`を取得するための関数群を提供するモジュール

　このモジュールは、TOMLファイルから`PipelineDefinition`のインスタンスを取得するための関数 `parse_toml` 等を提供します。

　`parse_toml`並びに`parse_toml_data`関数で読み込み可能なTOMLファイルの形式は[db_definition.toml](../../test/db_definition.toml)と同様のものであり、以下の構成を持ちます。

- `[table_definitions]`: 挿入先のテーブルを定義するセクション
- `[data_links]`: ETL処理を定義するセクション
  - `[[data_links.sources]]`: データの取得方法を定義するセクション
  - `[data_links.insertion_profiles]`: データの加工・書込方法を定義するセクション
    - `table_definitions`セクションで定義したテーブル名を指定する
    - 例: `users`テーブルを定義した場合は `[data_links.insertion_profiles.users]` 以下に変換・書込方法を定義する

　また、`table_definitions`、`data_link`、`data_link.sources`の各セクションをクラスインスタンスに変換するための以下の関数も提供します。いずれも引数は`tomlkit.items.Table`型です。

- `parse_table_definitions`: `table_definitions`の各セクションを`TableDefinition`のインスタンスに変換する関数
- `parse_data_link`: `data_link`の各セクションを`DataLink`のインスタンスに変換する関数
- `parse_data_source`: `data_link.sources`の各セクションを`DataSource`のインスタンスに変換する関数

```python
from jobcan_di.database.data_pipeline import (
    PipelineDefinition,
    TableDefinition, DataLink, DataSource
)
from jobcan_di.database.data_pipeline.parser import (
    parse_toml_data, parse_table_definitions,
    parse_data_link, parse_data_source
)
import tomlkit

# TOMLファイルの読み込み
with open('db_definition.toml') as f:
    toml_str = f.read()
    toml_data = tomlkit.parse(toml_str)

# TOMLデータからPipelineDefinitionのインスタンスを取得
pipeline_def = parse_toml_data(toml_data)

# table_definitionsやdata_linkセクションをインスタンスに変換することも可能
table_def: TableDefinition = parse_table_definitions(toml_data['table_definitions'])
data_link: DataLink = parse_data_link(toml_data['data_link'])

# data_link.sourcesの各セクションをインスタンスに変換することも可能
sources: list[DataSource] = []
for source in toml_data['data_link']['sources']:
    sources.append(parse_data_source(source))
```

### `data_pipeline.pipeline`: ETL処理を行うための関数群を提供するモジュール

　このモジュールでは、`data_pipeline.parser`で取得した`PipelineDefinition`のインスタンスをもとに、ETL処理を行うための関数を提供します。

```python
from jobcan_di.database.data_pipeline.parser import parse_toml
from jobcan_di.database.data_pipeline.pipeline import execute_data_pipeline

# tomlファイルからパイプライン定義を取得
pipeline_def = parse_toml('db_definition.toml')

# ETL処理を実行
execute_data_pipeline(pipeline_def)
```


