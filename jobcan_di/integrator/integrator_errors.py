"""
jobcan_di.integrator.integrator_errors
エラー情報を提供するモジュール

Classes
-------
- `JDIErrorData` : エラー情報 (抽象クラス)
- `TokenMissingEnvEmpty` : トークン取得先の環境変数名が指定されていない場合のエラー情報
- `TokenMissingEnvNotFound` : 指定された環境変数が存在しない場合のエラー情報
- `TokenInvalid` : トークンが無効な場合のエラー情報
- `DatabaseConnectionFailed` : データベースへの接続に失敗した場合のエラー情報
- `ApiInvalidParameterError` : APIのパラメータが不正な場合のエラー情報
- `ApiCommonIdSyncFailedError` : APIの共通IDとの連携に失敗した場合のエラー情報
- `ApiDataNotFoundError` : APIのデータが見つからない場合のエラー情報
- `ApiUnexpectedError` : APIの予期しないエラーが発生した場合のエラー情報
- `UnexpectedError` : 未知のエラーが発生した場合のエラー情報

Functions
---------
- `get_api_error` : APIエラー情報の取得
"""
from abc import ABCMeta, abstractmethod
from typing import Optional, Union

from .progress_status import ErrorStatus, API_TYPE_NAME, APIType



#
# エラー全般
#

class JDIErrorData(metaclass=ABCMeta):
    """エラー情報"""
    status: ErrorStatus = ErrorStatus.UNKNOWN_ERROR

    @abstractmethod
    def error_message(self) -> str:
        """エラー情報

        Returns
        -------
        str
            エラーメッセージ
        """

class UnexpectedError(JDIErrorData):
    """未知のエラーが発生した場合のエラー情報"""
    status = ErrorStatus.UNKNOWN_ERROR

    def __init__(self, e:Union[Exception, str, None]):
        """未知のエラーが発生した場合のエラー情報

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

    def error_message(self) -> str:
        if self._exception_name is None:
            return "未知のエラーが発生しました。"

        return "以下のエラーが発生しました: " \
               f"{self._exception_name}: {self._args}"



#
# トークン
#

class TokenMissingEnvEmpty(JDIErrorData):
    """トークン取得先の環境変数名が指定されていない場合のエラー情報"""
    status = ErrorStatus.TOKEN_MISSING_ENV_EMPTY

    def error_message(self) -> str:
        return "コンフィグにトークン取得先の環境変数名が指定されていません。" \
               "TOKEN_ENV_NAME を指定するか、API_TOKEN にトークンを指定して下さい。"

class TokenMissingEnvNotFound(JDIErrorData):
    """指定された環境変数が存在しない場合のエラー情報"""
    status = ErrorStatus.TOKEN_MISSING_ENV_NOT_FOUND

    def __init__(self, env_name:str):
        """指定された環境変数が存在しない場合のエラー情報

        Parameters
        ----------
        env_name : str
            トークン保存先の環境変数名
        """
        self._env_name = env_name

    def error_message(self) -> str:
        return f"指定された環境変数 {self._env_name} が存在しません。" \
               "TOKEN_ENV_NAME を修正するか、API_TOKEN にトークンを指定して下さい。"

class TokenInvalid(JDIErrorData):
    """トークンが無効な場合のエラー情報"""
    status = ErrorStatus.TOKEN_INVALID

    def __init__(self, token:str):
        """トークンが無効な場合のエラー情報

        Parameters
        ----------
        token : str
            トークン
        """
        self._token = token[:3] + "*"*len(token[3:])
        """トークン (一部マスク)"""

    def error_message(self) -> str:
        return f"指定されたトークンが無効です。" \
               f"設定を確認してください (トークン: {self._token})"



#
# データベース
#

class DatabaseConnectionFailed(JDIErrorData):
    """データベースへの接続に失敗した場合のエラー情報"""
    status = ErrorStatus.DATABASE_CONNECTION_FAILED

    def __init__(self, e:Optional[Exception]=None):
        """データベースへの接続に失敗した場合のエラー情報

        Parameters
        ----------
        e : Optional[Exception], default None
            例外
        """
        self._exception_name = e.__class__.__name__ if e else ""
        self._args = e.args[0] if e and e.args else ""

    def error_message(self) -> str:
        if self._exception_name:
            return f"データベースへの接続に失敗しました: " \
                   f"{self._exception_name}: {self._args}"
        else:
            return "データベースへの接続に失敗しました。"



#
# requests
#

class RequestConnectionError(JDIErrorData):
    """リクエストの接続に失敗した場合のエラー情報
    (requests.exceptions.ConnectionError)"""
    status = ErrorStatus.REQUEST_CONNECTION_ERROR

    def __init__(self, e:Exception):
        """リクエストの接続に失敗した場合のエラー情報

        Parameters
        ----------
        e : Exception
            例外
        """
        self._exception_name = e.__class__.__name__
        self._args = e.args[0] if e.args else ""

    def error_message(self) -> str:
        return f"接続に失敗しました: {self._exception_name}: {self._args}"

class RequestReadTimeout(JDIErrorData):
    """リクエストの読み込みがタイムアウトした場合のエラー情報
    (requests.exceptions.ReadTimeout)"""
    status = ErrorStatus.REQUEST_READ_TIMEOUT

    def __init__(self, e:Exception):
        """リクエストの読み込みがタイムアウトした場合のエラー情報

        Parameters
        ----------
        e : Exception
            例外
        """
        self._exception_name = e.__class__.__name__
        self._args = e.args[0] if e.args else ""

    def error_message(self) -> str:
        return f"読み込みがタイムアウトしました: {self._exception_name}: {self._args}"


#
# API
#

class ApiInvalidParameterError(JDIErrorData):
    """APIのパラメータが不正な場合のエラー情報"""
    status = ErrorStatus.API_INVALID_PARAMETER

    def __init__(self, api_type:APIType, response:dict):
        """APIのパラメータが不正な場合のエラー情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        response : dict
            APIのレスポンス
        """
        self._api_name = API_TYPE_NAME[api_type]
        self._detail = " / ".join(response.get("detail", []))

    def error_message(self) -> str:
        return f"{self._api_name} の取得に失敗しました。" \
               f"パラメータが不正です (ステータスコード 400): {self._detail} "

class ApiInvalidJsonFormatError(JDIErrorData):
    """APIのJSONの形式が不正な場合のエラー情報"""
    status = ErrorStatus.API_INVALID_JSON_FORMAT

    def __init__(self, api_type:APIType, response:dict):
        """APIのJSONの形式が不正な場合のエラー情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        response : dict
            APIのレスポンス
        """
        self._api_name = API_TYPE_NAME[api_type]
        self._detail = " / ".join(response.get("message", []))

    def error_message(self) -> str:
        return f"{self._api_name} の取得に失敗しました。" \
               f"JSONの形式が不正です (ステータスコード 400): {self._detail}"

class ApiCommonIdSyncFailedError(JDIErrorData):
    """APIの共通IDとの連携に失敗した場合のエラー情報"""
    status = ErrorStatus.API_COMMON_ID_SYNC_FAILED

    def __init__(self, api_type:APIType):
        """APIの共通IDとの連携に失敗した場合のエラー情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        """
        self._api_name = API_TYPE_NAME[api_type]

    def error_message(self) -> str:
        return f"{self._api_name} の取得に失敗しました。" \
               f"共通IDとの連携に失敗しました (ステータスコード 400)"

class ApiDataNotFoundError(JDIErrorData):
    """APIのデータが見つからない場合のエラー情報"""
    status = ErrorStatus.API_DATA_NOT_FOUND

    def __init__(self, api_type:APIType, target:str):
        """APIのデータが見つからない場合のエラー情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        target : str
            対象 (クエリ文字列など)
        """
        self._api_name = API_TYPE_NAME[api_type]
        self._target = target

    def error_message(self) -> str:
        return f"{self._api_name} の取得に失敗しました。" \
               f"対象のデータが見つかりません (ステータスコード 404; ターゲット:{self._target})"

class ApiUnexpectedError(JDIErrorData):
    """APIの予期しないエラーが発生した場合のエラー情報"""
    status = ErrorStatus.API_UNEXPECTED_ERROR

    def __init__(self, api_type:APIType):
        """APIの予期しないエラーが発生した場合のエラー情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        """
        self._api_name = API_TYPE_NAME[api_type]

    def error_message(self) -> str:
        return f"{self._api_name} の取得に失敗しました。" \
               f"予期しないエラーが発生しました (ステータスコード 500)"

def get_api_error(api_type:APIType,
                  status_code:int, res:dict,
                  target:str="") -> JDIErrorData:
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
    JDIErrorData
        APIエラー情報
    """
    if status_code == 400:
        code = res.get("code", None)

        if code == 400003:
            return ApiInvalidParameterError(api_type, res)
        elif code == 400100:
            return ApiInvalidJsonFormatError(api_type, res)
        elif code == 400900:
            return ApiCommonIdSyncFailedError(api_type)
        return UnexpectedError("400 Bad Request / APIによるデータ取得時に不明なエラーが発生しました")
    elif status_code == 404:
        return ApiDataNotFoundError(api_type, target)
    elif status_code == 500:
        return ApiUnexpectedError(api_type)

    return UnexpectedError(f"APIによるデータ取得時に不明なエラーが発生しました (ステータスコード {status_code})")
