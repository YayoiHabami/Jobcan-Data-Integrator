"""
Jobcan Data Integrator のJSONデータの入出力を管理するモジュール

Functions
---------
- `save_response_to_json`: APIのレスポンスをJSONファイルに保存する
"""
import json
import os

from jobcan_di.status.progress import APIType

def save_response_to_json(response: dict,
                          api_type: APIType,
                          page: int,
                          indent: int,
                          output_dir: str,
                          encoding: str = "utf-8") -> None:
    """
    APIのレスポンスをJSONファイルに保存する

    Parameters
    ----------
    response : dict
        APIのレスポンスをそのままJSON化したもの (response.json())
    api_type : APIType
        APIの種類
    page : int
        ページ番号
    indent : int
        JSONのインデント
    output_dir : str
        出力先ディレクトリ
    encoding : str
        JSONのエンコーディング
    """
    file_name = ""
    if api_type == APIType.USER_V3:
        file_name = f"user-v3-p{page}.json"
    elif api_type == APIType.GROUP_V1:
        file_name = f"group-v1-p{page}.json"
    elif api_type == APIType.POSITION_V1:
        file_name = f"position-v1-p{page}.json"
    elif api_type == APIType.FORM_V1:
        file_name = f"form-v1-p{page}.json"
    elif api_type == APIType.REQUEST_OUTLINE:
        file_name = f"request-outline-p{page}.json"
    elif api_type == APIType.REQUEST_DETAIL:
        file_name = f"request-detail-p{page}.json"

    indent = indent if indent >= 0 else None

    with open(os.path.join(output_dir, file_name), 'w', encoding=encoding) as f:
        json.dump(response, f, indent=indent, ensure_ascii=False)
