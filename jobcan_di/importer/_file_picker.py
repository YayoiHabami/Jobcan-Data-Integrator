"""
一定の規則に従ってファイルを取得するための関数を提供するモジュール

Functions
---------
- pick_files: ファイルを取得する

Examples
--------

`path/to`ディレクトリに以下の4つのファイルが存在する場合:

- `request_物品購入稟議申請書_20240131123456_12345_1.csv`
- `request_物品購入稟議申請書_20240131123456_12345_2.csv`
- `request_経費精算申請書_20240131123456_12345_3.csv`
- `unrelated_file.csv`

```python
from jobcan_di.importer import pick_files

# ファイル名の正規表現
file_name_regex = r"request_(.*?)_\d+_\d+_(\d+)\.csv"

# ファイルを取得
files = pick_files("path/to", file_name_regex)
# => {
#     "物品購入稟議申請書": [
#         "path/to/request_物品購入稟議申請書_20240131123456_12345_1.csv",
#         "path/to/request_物品購入稟議申請書_20240131123456_12345_2.csv"
#     ],
#     "経費精算申請書": [
#         "path/to/request_経費精算申請書_20240131123456_12345_3.csv"
#     ]
# }
```
"""
import os
import re
from typing import Optional

def _parse_file_name(
        file_name: str, regex: str
    ) -> Optional[tuple[str, int]]:
    """CSVファイルのファイル名から申請書の種類と連番を取得する

    Parameters
    ----------
    file_name : str
        ファイル名、例: `request_物品購入稟議申請書_20240131123456_12345_5.csv`
    regex : str
        ファイル名の正規表現 ($1: 申請書の種類, $2: 連番)
        例: `request_(.*?)_\\d+_\\d+_(\\d+)\\.csv`

    Returns
    -------
    Optional[tuple[str, int]]
        申請書の種類と連番のタプル、例: `("物品購入稟議申請書", 5)`
        ファイル名が正規表現にマッチしない場合はNone

    Raises
    ------
    ValueError
        - 正規表現にグループが足りない場合: $1 (申請書の種類), $2 (連番) が必要
        - 連番が数値でない場合: 正規表現の修正が必要
    """
    match = re.match(regex, file_name)
    if match is None:
        return None

    try:
        form_name = match.group(1)
        file_number = int(match.group(2))
    except IndexError:
        # 正規表現のグループが足りない場合: regexが間違っている
        raise ValueError("The regex must have two groups ($1: form name, $2: file number)" \
                         f"but got: '{regex}'")
    except ValueError:
        # 連番が数値でない場合 (regexが間違っている)
        raise ValueError("The file number must be an integer but got: " \
                         f"'{match.group(2)}' in file_name '{file_name}'")

    if not form_name:
        # 申請書の種類が空文字列の場合は不正なファイル名
        return None
    return form_name, file_number

def pick_files(
        folder_path: str, file_name_regex: str
    ) -> dict[str, list[str]]:
    """
    ファイルを取得する

    Parameters
    ----------
    folder_path : str
        ファイルが格納されているディレクトリのパス
    file_name_regex : str
        ファイル名の正規表現 ($1: 申請書の種類, $2: 連番)
        例: `request_(.*?)_\\d+_\\d+_(\\d+)\\.csv`

    Returns
    -------
    dict[str, list[str]]
        申請書の種類をキーとして、ファイルパスのリストを値とする辞書
        "物品購入稟議申請書"が2つ、"経費精算申請書"が1つの場合:

    >>> {
    ...     "物品購入稟議申請書": [
    ...         "path/to/request_物品購入稟議申請書_20241117165333_12345_1.csv",
    ...         "path/to/request_物品購入稟議申請書_20241117165333_12345_2.csv"
    ...     ],
    ...     "経費精算申請書": [
    ...         "path/to/request_経費精算申請書_20241117165333_12345_3.csv"
    ...     ]
    ... }

    Notes
    -----
    - 「申請検索」の画面において「CSVダウンロード」をクリックすると、以下の形式で
      CSVファイルがダウンロードされる (2024/11/21時点の仕様)
        - フォルダ名: `request_<ダウンロード日時>_jobcan_download_files`
        - ファイル名: `request_<申請書の種類>_<ダウンロード開始日時>_<総ダウンロード数?>_<連番>.csv`
      - ファイル名の例: `request_20240131122812_jobcan_download_files`に存在する5つめのファイル
        - `request_物品購入稟議申請書_20240131123456_12345_5.csv`
    - ここから、<申請書の種類>を取得し、<連番>の順でファイルパスを格納する
    - 各パスは`folder_path`に続く形式となる。
      - 例: `folder_path`が`C:/Users/hello/requests`の場合
        `request_物品購入稟議申請書_20241117165333_12345_5.csv`のファイルパスは
        `C:/Users/hello/requests/request_物品購入稟議申請書_20241117165333_12345_5.csv`
    """
    # 申請書の種類を第1のキー、連番を第2のキーとする辞書
    unsorted_files: dict[str, dict[int, str]] = {}

    for file_or_dir in os.listdir(folder_path):
        full_path = os.path.join(folder_path, file_or_dir)
        if not os.path.isfile(full_path):
            # ファイルでない場合はスキップ
            continue

        # ファイル名から申請書の種類と連番を取得
        if (fn_cnt := _parse_file_name(file_or_dir, file_name_regex)) is None:
            # ファイル名が不正な場合はスキップ
            continue
        form_name, count = fn_cnt

        # 申請書の種類を第1のキー、連番を第2のキーとしてファイルパスを格納
        if form_name not in unsorted_files:
            unsorted_files[form_name] = {}
        unsorted_files[form_name][count] = full_path

    files = {}
    for form_name, count_dict in unsorted_files.items():
        # 連番の昇順にファイルパスを取得
        files[form_name] = [count_dict[i] for i in sorted(count_dict.keys())]
    return files
