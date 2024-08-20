"""
進捗状況を表す列挙型とメッセージを定義

Functions
---------
- `get_progress_status_msg`: ProgressStatusと各進捗状況に対応するメッセージを取得
- `get_progress_status`: APIの種類に応じた進捗状況を取得
- `get_detailed_progress_status`: APIの種類に応じた詳細な進捗状況を取得
- `get_detailed_progress_status_from_str`: 進捗状況の文字列からDetailedProgressStatusを取得

Classes
-------
- `ProgressStatus`: 進捗状況 (大枠)
- `DetailedProgressStatus`: 進捗状況 (詳細、継承用)
- `InitializingStatus`: 進捗状況 (ProgressStatus.INITIALIZING)
- `GetBasicDataStatus`: 進捗状況 (ProgressStatus.BASIC_DATA)
- `GetFormOutlineStatus`: 進捗状況 (ProgressStatus.FORM_OUTLINE)
- `GetFormDetailStatus`: 進捗状況 (ProgressStatus.FORM_DETAIL)
- `TerminatingStatus`: 進捗状況 (ProgressStatus.TERMINATING)
- `ErrorStatus`: エラー
- `APIType`: APIの種類

Constants
----------
- `MAX_STATUS_LENGTH`: 進捗状況の最大文字数
- `PROGRESS_STATUS_MSG`: 進捗状況メッセージ
- `INITIALIZING_STATUS_MSG`: 進捗状況 (IN_PROGRESS) メッセージ
- `GET_BASIC_DATA_STATUS_MSG`: 進捗状況 (BASIC_DATA) メッセージ
- `GET_FORM_OUTLINE_STATUS_MSG`: 進捗状況 (FORM_OUTLINE) メッセージ
- `GET_FORM_DETAIL_STATUS_MSG`: 進捗状況 (FORM_DETAIL) メッセージ
- `TERMINATING_STATUS_MSG`: 進捗状況 (TERMINATING) メッセージ
- `API_TYPE_NAME`: APIの種類の名前
"""
from enum import Enum, auto
from typing import Union



#
# 進捗状況 (全体)
#

class ProgressStatus(Enum):
    """進捗状況 (大枠)"""
    # 設定読み込み・事前準備
    INITIALIZING = 0
    # 基本データの取得
    BASIC_DATA = auto()
    # 申請書データ (概要) の取得
    FORM_OUTLINE = auto()
    # 申請書データ (詳細) の取得
    FORM_DETAIL = auto()
    # 終了処理
    TERMINATING = auto()
    # データの取得失敗
    FAILED = -1
MAX_STATUS_LENGTH = max([len(s.name) for s in ProgressStatus])

# 進捗状況メッセージ
_cnt = len(ProgressStatus) - 1
PROGRESS_STATUS_MSG = {
    ProgressStatus.INITIALIZING: f"初期化中... (STEP 1/{_cnt})",
    ProgressStatus.BASIC_DATA: f"基本データ取得中... (STEP 2/{_cnt})",
    ProgressStatus.FORM_OUTLINE: f"申請書データ (概要) 取得中... (STEP 3/{_cnt})",
    ProgressStatus.FORM_DETAIL: f"申請書データ (詳細) 取得中... (STEP 4/{_cnt})",
    ProgressStatus.TERMINATING: f"終了処理中... (STEP 5/{_cnt})",
    ProgressStatus.FAILED: "更新に失敗しました"
}

class DetailedProgressStatus(Enum):
    """進捗状況 (詳細)

    Notes
    -----
    - 以下のEnumクラスで継承して使用
      - InitializingStatus
      - GetBasicDataStatus
      - GetFormOutlineStatus
      - GetFormDetailStatus
      - TerminatingStatus"""

class InitializingStatus(DetailedProgressStatus):
    """進捗状況 (ProgressStatus.INITIALIZING)"""
    LOADING_CONFIG = 1
    INIT_LOGGER = auto()
    INIT_NOTIFICATION = auto()
    INIT_DIRECTORIES = auto()
    INIT_TOKEN = auto()
    INIT_DB_CONNECTION = auto()
    INIT_DB_TABLES = auto()
    COMPLETED = auto()

# 進捗状況 (IN_PROGRESS) メッセージ
_cnt = len(InitializingStatus)
INITIALIZING_STATUS_MSG = {
    InitializingStatus.LOADING_CONFIG: f"設定ファイルを読み込み中... (1/{_cnt})",
    InitializingStatus.INIT_LOGGER: f"ロガーを初期化中... (2/{_cnt})",
    InitializingStatus.INIT_NOTIFICATION: f"通知を初期化中... (3/{_cnt})",
    InitializingStatus.INIT_DIRECTORIES: f"ディレクトリを初期化中... (4/{_cnt})",
    InitializingStatus.INIT_TOKEN: f"APIトークンを初期化中... (5/{_cnt})",
    InitializingStatus.INIT_DB_CONNECTION: f"データベースとの接続を初期化中... (6/{_cnt})",
    InitializingStatus.INIT_DB_TABLES: f"データベースのテーブルを初期化中... (7/{_cnt})",
    InitializingStatus.COMPLETED: f"初期化が完了しました (8/{_cnt})"
}

class GetBasicDataStatus(DetailedProgressStatus):
    """進捗状況 (ProgressStatus.BASIC_DATA)"""
    GET_USER = 1
    GET_GROUP = auto()
    GET_POSITION = auto()

# 進捗状況 (BASIC_DATA) メッセージ
_cnt = len(GetBasicDataStatus)
GET_BASIC_DATA_STATUS_MSG = {
    GetBasicDataStatus.GET_USER: f"ユーザデータを取得中... (1/{_cnt})",
    GetBasicDataStatus.GET_GROUP: f"グループデータを取得中... (2/{_cnt})",
    GetBasicDataStatus.GET_POSITION: f"役職データを取得中... (3/{_cnt})",
}

class GetFormOutlineStatus(DetailedProgressStatus):
    """進捗状況 (ProgressStatus.FORM_OUTLINE)"""
    GET_FORM_INFO = 1
    GET_OUTLINE = auto()

# 進捗状況 (FORM_OUTLINE) メッセージ
GET_FORM_OUTLINE_STATUS_MSG = {
    GetFormOutlineStatus.GET_FORM_INFO: "申請書様式データを取得中... ({}/{})",
    GetFormOutlineStatus.GET_OUTLINE: "申請書データ（概要）取得中... ({}/{})",
}

class GetFormDetailStatus(DetailedProgressStatus):
    """進捗状況 (ProgressStatus.FORM_DETAIL)"""
    SEEK_TARGET = 1     # 取得対象の申請書を探す
    GET_DETAIL = auto() # APIで申請書データ（詳細）を取得＆保存

# 進捗状況 (FORM_DETAIL) メッセージ
_cnt = len(GetFormDetailStatus)
GET_FORM_DETAIL_STATUS_MSG = {
    GetFormDetailStatus.SEEK_TARGET: "取得対象の申請書を探しています... (1/{})",
    GetFormDetailStatus.GET_DETAIL: "申請書データ（詳細）取得中... ({}/{})",
}

class TerminatingStatus(DetailedProgressStatus):
    """進捗状況 (ProgressStatus.TERMINATING)"""
    CLOSE_DB_CONNECTION = 1
    DELETE_TEMP_FILES = auto()
    COMPLETED = auto()

# 進捗状況 (TERMINATING) メッセージ
_cnt = len(TerminatingStatus)
TERMINATING_STATUS_MSG = {
    TerminatingStatus.CLOSE_DB_CONNECTION: f"データベースとの接続を終了中... (1/{_cnt})",
    TerminatingStatus.DELETE_TEMP_FILES: f"一時ファイルを削除中... (2/{_cnt})",
    TerminatingStatus.COMPLETED: f"すべての処理が完了しました (3/{_cnt})",
}

class ErrorStatus(DetailedProgressStatus):
    """エラー"""
    # トークン
    TOKEN_MISSING_ENV_EMPTY = auto()
    """トークンが指定されず、指定された環境変数が空の場合"""
    TOKEN_MISSING_ENV_NOT_FOUND = auto()
    """トークンが指定されず、指定された環境変数が存在しない場合"""
    TOKEN_INVALID = auto()
    """トークンが不正な場合"""
    # データベース
    DATABASE_CONNECTION_FAILED = auto()
    """データベースへの接続に失敗した場合"""
    # requests
    REQUEST_CONNECTION_ERROR = auto()
    """requestsでの接続に失敗した場合 (requests.exceptions.ConnectionError)"""
    REQUEST_READ_TIMEOUT = auto()
    """requestsでの接続がタイムアウトした場合 (requests.exceptions.ReadTimeout)"""
    # API
    API_INVALID_PARAMETER = auto()
    """APIのパラメータが不正な場合 (Status code: 400, code: 400003)"""
    API_INVALID_JSON_FORMAT = auto()
    """リクエストのJSONの形式が不正な場合 (Status code: 400, code: 400100)"""
    API_COMMON_ID_SYNC_FAILED = auto()
    """共通IDとの連携に失敗した場合 (Status code: 400, code: 400900)"""
    API_DATA_NOT_FOUND = auto()
    """対象のデータが見つからない場合 (Status code: 404)"""
    API_UNEXPECTED_ERROR = auto()
    """予期しないエラーが発生した場合 (Status code: 500)"""
    # その他
    UNKNOWN_ERROR = auto()
    """未知のエラーが発生した場合"""

# ProgressStatusと各進捗状況に対応するメッセージを取得
def get_progress_status_msg(status:ProgressStatus, sub_status:DetailedProgressStatus,
                            sub_count: int = 0, sub_total_count : int = 0) -> str:
    """ProgressStatusと各進捗状況に対応するメッセージを取得する

    Parameters
    ----------
    status : ProgressStatus
        大枠の進捗状況
    sub_status : DetailedProgressStatus
        細かい進捗状況、ErrorStatusを除く
    sub_count : int, default 0
        進捗に可算する値, ProgressStatus.FORM_OUTLINEの場合に使用
    sub_total_count : int, default 0
        進捗の全体数に可算する値, ProgressStatus.FORM_OUTLINEの場合に使用"""
    if status == ProgressStatus.INITIALIZING:
        return INITIALIZING_STATUS_MSG[sub_status]
    elif status == ProgressStatus.BASIC_DATA:
        return GET_BASIC_DATA_STATUS_MSG[sub_status]
    elif status == ProgressStatus.FORM_OUTLINE:
        return GET_FORM_OUTLINE_STATUS_MSG[sub_status].format(
                sub_count + sub_status.value,
                sub_total_count+len(GetFormOutlineStatus)
            )
    elif status == ProgressStatus.FORM_DETAIL:
        return GET_FORM_DETAIL_STATUS_MSG[sub_status].format(
                sub_count + sub_status.value,
                sub_total_count+len(GetFormDetailStatus)
            )
    elif status == ProgressStatus.TERMINATING:
        return TERMINATING_STATUS_MSG[sub_status]
    elif status == ProgressStatus.FAILED:
        return "更新に失敗しました"
    return ""

def get_detailed_progress_status_from_str(
        status:str, sub_status:str
        ) -> DetailedProgressStatus:
    """進捗状況の文字列からDetailedProgressStatusを取得する

    Parameters
    ----------
    status : str
        大枠の進捗状況
    sub_status : str
        細かい進捗状況

    Returns
    -------
    DetailedProgressStatus
        進捗状況 (詳細)"""
    if status == ProgressStatus.INITIALIZING.name:
        return InitializingStatus[sub_status]
    elif status == ProgressStatus.BASIC_DATA.name:
        return GetBasicDataStatus[sub_status]
    elif status == ProgressStatus.FORM_OUTLINE.name:
        return GetFormOutlineStatus[sub_status]
    elif status == ProgressStatus.FORM_DETAIL.name:
        return GetFormDetailStatus[sub_status]
    elif status == ProgressStatus.TERMINATING.name:
        return TerminatingStatus[sub_status]
    return ErrorStatus.UNKNOWN_ERROR


#
# 進捗状況 (APIデータ取得)
#

class APIType(Enum):
    """
    APIの種類
    """
    USER_V3 = auto()
    GROUP_V1 = auto()
    POSITION_V1 = auto()
    FORM_V1 = auto()
    REQUEST_OUTLINE = auto()
    REQUEST_DETAIL = auto()

API_TYPE_NAME = {
    APIType.USER_V3: "ユーザデータ",
    APIType.GROUP_V1: "グループデータ",
    APIType.POSITION_V1: "役職データ",
    APIType.FORM_V1: "申請書様式データ",
    APIType.REQUEST_OUTLINE: "申請書データ (概要)",
    APIType.REQUEST_DETAIL: "申請書データ (詳細)",
}

def get_progress_status(api_type:APIType) -> ProgressStatus:
    """
    APIの種類に応じた進捗状況を取得する

    Parameters
    ----------
    api_type : APIType
        APIの種類

    Returns
    -------
    ProgressStatus
        進捗状況 (大枠)
    """
    if api_type == APIType.USER_V3:
        return ProgressStatus.BASIC_DATA
    elif api_type == APIType.GROUP_V1:
        return ProgressStatus.BASIC_DATA
    elif api_type == APIType.POSITION_V1:
        return ProgressStatus.BASIC_DATA
    elif api_type == APIType.FORM_V1:
        return ProgressStatus.FORM_OUTLINE
    elif api_type == APIType.REQUEST_OUTLINE:
        return ProgressStatus.FORM_OUTLINE
    elif api_type == APIType.REQUEST_DETAIL:
        return ProgressStatus.FORM_DETAIL

def get_detailed_progress_status(api_type:APIType) -> Union[GetBasicDataStatus,
                                                            GetFormOutlineStatus,
                                                            GetFormDetailStatus]:
    """
    APIの種類に応じた詳細な進捗状況を取得する

    Parameters
    ----------
    api_type : APIType
        APIの種類

    Returns
    -------
    Enum
        進捗状況 (詳細)
    """
    if api_type == APIType.USER_V3:
        return GetBasicDataStatus.GET_USER
    elif api_type == APIType.GROUP_V1:
        return GetBasicDataStatus.GET_GROUP
    elif api_type == APIType.POSITION_V1:
        return GetBasicDataStatus.GET_POSITION
    elif api_type == APIType.FORM_V1:
        return GetFormOutlineStatus.GET_FORM_INFO
    elif api_type == APIType.REQUEST_OUTLINE:
        return GetFormOutlineStatus.GET_OUTLINE
    elif api_type == APIType.REQUEST_DETAIL:
        return GetFormDetailStatus.GET_DETAIL
