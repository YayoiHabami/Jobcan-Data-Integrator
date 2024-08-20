"""
jobcan_di.integrator.integrator_warnings

警告情報を提供するモジュール

Classes
-------
- `JDIWarning` : 警告 (列挙型)
- `JDIWarningData` : 警告情報 (抽象クラス)
- `UnexpectedWarning` : 予期しないエラーが発生した場合の警告情報
- `InvalidConfigFilePath` : コンフィグファイルのパスが不正な場合の警告情報
- `InvalidStatusFilePath` : ステータスファイルのパスが不正な場合の警告情報
- `InvalidLogFilePath` : ログファイルのパスが不正な場合の警告情報
- `ApiInvalidParameterWarning` : APIのパラメータが不正な場合の警告情報
- `ApiInvalidJsonFormatWarning` : APIのJSONの形式が不正な場合の警告情報
- `ApiCommonIdSyncFailedWarning` : APIの共通IDとの連携に失敗した場合の警告情報
- `ApiDataNotFoundWarning` : APIのデータが見つからない場合の警告情報
- `ApiUnexpectedWarning` : APIの予期しないエラーが発生した場合の警告情報
- `FormDetailApiInvalidParameterWarning` : 申請書データ (詳細) のAPIのパラメータが不正な場合の警告情報
- `FormDetailApiDataNotFoundWarning` : 指定された申請書データ (詳細) が見つからない場合の警告情報
- `FormDetailApiUnexpectedWarning` : 申請書データ (詳細) のAPIで予期しないエラーが発生した場合の警告情報
- `DBUpdateFailed` : DBのデータ更新に失敗した場合の警告情報

Functions
---------
- `get_api_error` : APIエラー情報の取得
- `get_form_detail_api_warning` : 申請書データ (詳細) のAPIの警告情報を取得
"""
from abc import ABCMeta, abstractmethod
from enum import Enum, auto
from typing import Optional, Union

from .progress_status import APIType, API_TYPE_NAME



class JDIWarning(Enum):
    """警告"""
    # ファイルパス
    INVALID_CONFIG_FILE_PATH = auto()
    """指定されたコンフィグファイルのパスが不正な場合"""
    INVALID_STATUS_FILE_PATH = auto()
    """指定されたステータスファイル (app_status) のパスが不正な場合"""
    INVALID_LOG_FILE_PATH = auto()
    """指定されたログファイルのパスが不正な場合"""
    # API (general)
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
    # API (form_detail)
    FORM_DETAIL_API_INVALID_PARAMETER = auto()
    """申請書データ (詳細) のAPIのパラメータが不正な場合"""
    FORM_DETAIL_API_API_DATA_NOT_FOUND = auto()
    """指定された申請書データ (詳細) が見つからない場合"""
    FORM_DETAIL_API_UNEXPECTED_ERROR = auto()
    """申請書データ (詳細) のAPIで予期しないエラーが発生した場合"""
    # DB
    DB_UPDATE_FAILED = auto()
    """DBのデータ更新に失敗した場合"""
    # その他
    UNEXPECTED_ERROR = auto()
    """予期しないエラーが発生した場合"""


class JDIWarningData(metaclass=ABCMeta):
    """警告情報"""
    status: JDIWarning = JDIWarning.INVALID_CONFIG_FILE_PATH

    @abstractmethod
    def warning_message(self) -> str:
        """警告メッセージの取得

        Returns
        -------
        str
            警告メッセージ
        """

class UnexpectedWarning(JDIWarningData):
    """予期しないエラーが発生した場合の警告情報"""
    status = JDIWarning.UNEXPECTED_ERROR

    def __init__(self, e:Union[Exception, str, None]):
        """予期しないエラーが発生した場合の警告情報

        Parameters
        ----------
        e : Exception | str | None
            例外、またはエラーメッセージ
        """
        if isinstance(e, str):
            self._exception_name = "UnexpectedError"
            self._args = e
        elif isinstance(e, Exception):
            self._exception_name = e.__class__.__name__
            self._args = e.args[0] if e.args else ""
        else:
            self._exception_name = None
            self._args = None

    def warning_message(self) -> str:
        if self._exception_name is None:
            return "予期しないエラーが発生しました。"

        return f"予期しないエラーが発生しました。" \
                f"例外: {self._exception_name} - {self._args}"



#
# ファイルパス
#

class InvalidConfigFilePath(JDIWarningData):
    """指定されたコンフィグファイルのパスが不正な場合の警告情報"""
    status = JDIWarning.INVALID_CONFIG_FILE_PATH

    def __init__(self, file_path:str):
        """指定されたコンフィグファイルのパスが不正な場合の警告情報

        Parameters
        ----------
        file_path : str
            コンフィグファイルのパス
        """
        self._file_path = file_path

    def warning_message(self) -> str:
        return f"指定されたコンフィグファイルのパス ({self._file_path}) が不正です。" \
               "デフォルトのコンフィグファイルを使用します。"

class InvalidStatusFilePath(JDIWarningData):
    """指定されたステータスファイルのパスが不正な場合の警告情報"""
    status = JDIWarning.INVALID_STATUS_FILE_PATH

    def __init__(self, file_path:str):
        """指定されたステータスファイルのパスが不正な場合の警告情報

        Parameters
        ----------
        file_path : str
            ステータスファイルのパス
        """
        self._file_path = file_path

    def warning_message(self) -> str:
        return f"指定されたステータスファイルのパス ({self._file_path}) が不正です。" \
               "デフォルトのファイルを使用します。"

class InvalidLogFilePath(JDIWarningData):
    """指定されたログファイルのパスが不正な場合の警告情報"""
    status = JDIWarning.INVALID_LOG_FILE_PATH

    def __init__(self, file_path:str):
        """指定されたログファイルのパスが不正な場合の警告情報

        Parameters
        ----------
        file_path : str
            ログファイルのパス
        """
        self._file_path = file_path

    def warning_message(self) -> str:
        return f"指定されたログファイルのパス ({self._file_path}) が不正です。" \
               "デフォルトのログファイルを使用します。"



#
# API (general)
#

class ApiInvalidParameterWarning(JDIWarningData):
    """APIのパラメータが不正な場合の警告情報"""
    status = JDIWarning.API_INVALID_PARAMETER

    def __init__(self, api_type:APIType, response:dict):
        """APIのパラメータが不正な場合の警告情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        response : dict
            APIのレスポンス
        """
        self._api_name = API_TYPE_NAME[api_type]
        self._detail = " / ".join(response.get("detail", []))

    def warning_message(self) -> str:
        return f"{self._api_name} の取得に失敗しました。" \
               f"パラメータが不正です (ステータスコード 400): {self._detail} "

class ApiInvalidJsonFormatWarning(JDIWarningData):
    """APIのJSONの形式が不正な場合の警告情報"""
    status = JDIWarning.API_INVALID_JSON_FORMAT

    def __init__(self, api_type:APIType, response:dict):
        """APIのJSONの形式が不正な場合の警告情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        response : dict
            APIのレスポンス
        """
        self._api_name = API_TYPE_NAME[api_type]
        self._detail = " / ".join(response.get("message", []))

    def warning_message(self) -> str:
        return f"{self._api_name} の取得に失敗しました。" \
               f"JSONの形式が不正です (ステータスコード 400): {self._detail}"

class ApiCommonIdSyncFailedWarning(JDIWarningData):
    """APIの共通IDとの連携に失敗した場合の警告情報"""
    status = JDIWarning.API_COMMON_ID_SYNC_FAILED

    def __init__(self, api_type:APIType):
        """APIの共通IDとの連携に失敗した場合の警告情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        """
        self._api_name = API_TYPE_NAME[api_type]

    def warning_message(self) -> str:
        return f"{self._api_name} の取得に失敗しました。" \
               f"共通IDとの連携に失敗しました (ステータスコード 400)"

class ApiDataNotFoundWarning(JDIWarningData):
    """APIのデータが見つからない場合の警告情報"""
    status = JDIWarning.API_DATA_NOT_FOUND

    def __init__(self, api_type:APIType, target:str):
        """APIのデータが見つからない場合の警告情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        target : str
            対象 (クエリ文字列など)
        """
        self._api_name = API_TYPE_NAME[api_type]
        self._target = target

    def warning_message(self) -> str:
        return f"{self._api_name} の取得に失敗しました。" \
               f"対象のデータが見つかりません (ステータスコード 404; ターゲット:{self._target})"

class ApiUnexpectedWarning(JDIWarningData):
    """APIの予期しないエラーが発生した場合の警告情報"""
    status = JDIWarning.API_UNEXPECTED_ERROR

    def __init__(self, api_type:APIType):
        """APIの予期しないエラーが発生した場合の警告情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        """
        self._api_name = API_TYPE_NAME[api_type]

    def warning_message(self) -> str:
        return f"{self._api_name} の取得に失敗しました。" \
               f"予期しないエラーが発生しました (ステータスコード 500)"

def get_api_error(api_type:APIType,
                  status_code:int, res:dict,
                  target:str="") -> JDIWarningData:
    """APIエラー情報の取得

    Parameters
    ----------
    api_type : APIType
        APIの種類
    status_code : int
        ステータスコード
    res : dict
        APIのレスポンス (`.json()` で取得したdict)
    target : str
        対象 (クエリ文字列など)

    Returns
    -------
    JDIWarningData
        APIエラー情報
    """
    if status_code == 400:
        code = res.get("code", None)

        if code == 400003:
            return ApiInvalidParameterWarning(api_type, res)
        elif code == 400100:
            return ApiInvalidJsonFormatWarning(api_type, res)
        elif code == 400900:
            return ApiCommonIdSyncFailedWarning(api_type)
        return UnexpectedWarning("400 Bad Request / APIによるデータ取得時に不明なエラーが発生しました")
    elif status_code == 404:
        return ApiDataNotFoundWarning(api_type, target)
    elif status_code == 500:
        return ApiUnexpectedWarning(api_type)

    return UnexpectedWarning(f"APIによるデータ取得時に不明なエラーが発生しました (ステータスコード {status_code})")



#
# API (form_detail)
#

class FormDetailApiInvalidParameterWarning(JDIWarningData):
    """申請書データ (詳細) のAPIのパラメータが不正な場合の警告情報"""
    status = JDIWarning.FORM_DETAIL_API_INVALID_PARAMETER

    def __init__(self, response:dict):
        """申請書データ (詳細) のAPIのパラメータが不正な場合の警告情報

        Parameters
        ----------
        response : dict
            APIのレスポンス
        """
        self._detail = " / ".join(response.get("detail", []))

    def warning_message(self) -> str:
        return f"{API_TYPE_NAME[APIType.REQUEST_DETAIL]} の取得に失敗しました。" \
               f"パラメータが不正です (ステータスコード 400): {self._detail} "

class FormDetailApiDataNotFoundWarning(JDIWarningData):
    """指定された申請書データ (詳細) が見つからない場合の警告情報"""
    status = JDIWarning.FORM_DETAIL_API_API_DATA_NOT_FOUND

    def __init__(self, request_id:str):
        """指定された申請書データ (詳細) が見つからない場合の警告情報

        Parameters
        ----------
        request_id : str
            対象の申請書ID
        """
        self._request_id = request_id

    def warning_message(self) -> str:
        return f"{API_TYPE_NAME[APIType.REQUEST_DETAIL]} の取得に失敗しました。" \
               f"指定された申請書データが見つかりません: {self._request_id} "

class FormDetailApiUnexpectedWarning(JDIWarningData):
    """申請書データ (詳細) のAPIで予期しないエラーが発生した場合の警告情報"""
    status = JDIWarning.FORM_DETAIL_API_UNEXPECTED_ERROR

    def __init__(self, status_code:int):
        """申請書データ (詳細) のAPIで予期しないエラーが発生した場合の警告情報

        Parameters
        ----------
        status_code : int
            ステータスコード
        """
        self._status_code = status_code

    def warning_message(self) -> str:
        return f"{API_TYPE_NAME[APIType.REQUEST_DETAIL]} の取得に失敗しました。" \
               f"予期しないエラーが発生しました (ステータスコード {self._status_code})"

def get_form_detail_api_warning(status_code:int, res:dict, request_id:str="") -> JDIWarningData:
    """申請書データ (詳細) のAPIの警告情報を取得

    Parameters
    ----------
    status_code : int
        ステータスコード
    res : dict
        APIのレスポンス
    request_id : str, default ""
        対象の申請書ID
    """
    if status_code == 400:
        return FormDetailApiInvalidParameterWarning(res)
    elif status_code == 404:
        return FormDetailApiDataNotFoundWarning(request_id)
    else:
        return FormDetailApiUnexpectedWarning(status_code)

#
# DB
#

class DBUpdateFailed(JDIWarningData):
    """DBのデータ更新に失敗した場合の警告情報"""
    status = JDIWarning.DB_UPDATE_FAILED

    def __init__(self, api_type:APIType, e:Optional[Exception]=None):
        """DBのデータ更新に失敗した場合の警告情報

        Parameters
        ----------
        api_type : APIType
            対象のAPIタイプ
        e : Exception, default None
            例外
        """
        self._api_type = api_type
        self._exception_name = e.__class__.__name__ if e else ""
        self._exception_message = e.args[0] if e else ""

    def warning_message(self) -> str:
        if self._exception_name:
            return f"{API_TYPE_NAME[self._api_type]} のデータ更新に失敗しました。" \
                   f"例外: {self._exception_name} - {self._exception_message}"
        return f"{API_TYPE_NAME[self._api_type]} のデータ更新に失敗しました。"
