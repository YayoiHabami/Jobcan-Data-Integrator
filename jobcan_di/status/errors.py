"""
jobcan_di.status.errors
エラー情報を提供するモジュール

Classes
-------
- `JDIErrorData` : エラー情報 (抽象クラス)
- `TokenMissingEnvEmpty` : トークン取得先の環境変数名が指定されていない場合のエラー情報
- `TokenMissingEnvNotFound` : 指定された環境変数が存在しない場合のエラー情報
- `TokenInvalid` : トークンが無効な場合のエラー情報
- `DatabaseConnectionFailed` : データベースへの接続に失敗した場合のエラー情報
- `ApiRequestErrorData` : APIエラー情報 (抽象クラス)
- `ApiInvalidParameterError` : APIのパラメータが不正な場合のエラー情報
- `ApiCommonIdSyncFailedError` : APIの共通IDとの連携に失敗した場合のエラー情報
- `ApiDataNotFoundError` : APIのデータが見つからない場合のエラー情報
- `ApiUnexpectedError` : APIの予期しないエラーが発生した場合のエラー情報
- `UnexpectedError` : 未知のエラーが発生した場合のエラー情報

Classes (DeveloperErrorData)
---------------------------
- `DeveloperErrorData` : 開発者側に問題がある場合のエラー情報 (抽象クラス)
- `NotInitializedError` : 初期化されていない場合のエラー情報 (開発者エラー)
- `ApiClientNotPrepared` : APIクライアントが準備されていない場合のエラー情報 (開発者エラー)
- `DatabaseConnectionNotPrepared` : データベース接続が準備されていない場合のエラー情報 (開発者エラー)
- `DatabaseNotPrepared` : データベースが準備されていない場合のエラー情報 (開発者エラー)

Functions
---------
- `get_api_error` : APIエラー情報の取得
- `from_json` : JSONからエラー情報を生成
"""
from abc import ABCMeta, abstractmethod
from copy import deepcopy
from typing import Optional, Union, Dict

from .progress import API_TYPE_NAME, APIType



#
# エラー全般
#

class JDIErrorData(metaclass=ABCMeta):
    """エラー情報"""
    def __init__(self, e:Union[Exception, str, dict, None]=None):
        """コンストラクタ

        Parameters
        ----------
        e : Exception | str | dict | None
            例外、またはエラーメッセージ
            dict の場合はエラー詳細を格納した辞書
        """
        self._details: dict = {}

        if e is None:
            # e が None の場合はエラー情報を空にする
            return

        if isinstance(e, str):
            e_name = "UnexpectedError"
            e_args = e
        elif isinstance(e, Exception):
            e_name = e.__class__.__name__
            e_args = e.args[0] if e.args else ""
        elif isinstance(e, dict):
            e_name = e.get("exception_name", "UnexpectedError")
            e_args = e.get("args", "")
            self._details = e

        self._details["e"] = {
            "exception_name": e_name,
            "args": e_args
        }

    @property
    def exception_name(self) -> Optional[str]:
        """例外名

        Returns
        -------
        str
            例外名
        """
        if "e" not in self._details:
            return None
        return self._details["e"]["exception_name"]

    @property
    def args(self) -> Optional[str]:
        """例外の引数

        Returns
        -------
        str
            例外の引数
        """
        if "e" not in self._details:
            return None
        return self._details["e"]["args"]

    @property
    def name(self) -> str:
        """エラー名

        Returns
        -------
        str
            エラー名
        """
        return self.__class__.__name__

    def asdict(self) -> dict:
        """エラー情報を辞書形式で取得

        Returns
        -------
        dict
            エラー情報
        """
        return deepcopy(self._details)

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

    def error_message(self) -> str:
        if self.exception_name is None:
            return "未知のエラーが発生しました。"

        return "以下のエラーが発生しました: " \
               f"{self.exception_name}: {self.args}"



#
# トークン
#

class TokenNotFoundError(JDIErrorData):
    """トークンが指定されていない場合のエラー情報"""
    def error_message(self) -> str:
        return "トークンが指定されていません。API_TOKEN にトークンを指定するか、" \
               "TOKEN_ENV_NAME にトークンを記録している環境変数名を指定して下さい。"

class TokenMissingEnvEmpty(JDIErrorData):
    """トークン取得先の環境変数名が指定されていない場合のエラー情報"""
    def error_message(self) -> str:
        return "コンフィグにトークン取得先の環境変数名が指定されていません。" \
               "TOKEN_ENV_NAME を指定するか、API_TOKEN にトークンを指定して下さい。"

class TokenMissingEnvNotFound(JDIErrorData):
    """指定された環境変数が存在しない場合のエラー情報"""
    def __init__(self, env_name:str, e:Union[Exception, str, dict, None]=None):
        """指定された環境変数が存在しない場合のエラー情報

        Parameters
        ----------
        env_name : str
            トークン保存先の環境変数名
        """
        super().__init__(e)
        self._details["env_name"] = env_name

    def error_message(self) -> str:
        return f"指定された環境変数 {self._details['env_name']} が存在しません。" \
               "TOKEN_ENV_NAME を修正するか、API_TOKEN にトークンを指定して下さい。"

class TokenInvalid(JDIErrorData):
    """トークンが無効な場合のエラー情報"""
    def __init__(self, token:str, e:Union[Exception, str, dict, None]=None):
        """トークンが無効な場合のエラー情報

        Parameters
        ----------
        token : str
            トークン
        """
        super().__init__(e)
        self._details["token"] = token[:3] + "*"*len(token[3:])
        """トークン (一部マスク)"""

    def error_message(self) -> str:
        return f"指定されたトークンが無効です。" \
               f"設定を確認してください (トークン: {self._details['token']})"



#
# データベース
#

class DatabaseConnectionFailed(JDIErrorData):
    """データベースへの接続に失敗した場合のエラー情報"""

    def error_message(self) -> str:
        if self.exception_name:
            return f"データベースへの接続に失敗しました: " \
                   f"{self.exception_name}: {self.args}"
        else:
            return "データベースへの接続に失敗しました。"

class DatabaseTableCreationFailed(JDIErrorData):
    """データベースのテーブル作成に失敗した場合のエラー情報"""

    def error_message(self) -> str:
        if self.exception_name:
            return f"データベースのテーブル作成に失敗しました: " \
                   f"{self.exception_name}: {self.args}"
        else:
            return "データベースのテーブル作成に失敗しました。"


#
# requests
#

class RequestConnectionError(JDIErrorData):
    """リクエストの接続に失敗した場合のエラー情報
    (requests.exceptions.ConnectionError)"""

    def error_message(self) -> str:
        return f"接続に失敗しました: {self.exception_name}: {self.args}"

class RequestReadTimeout(JDIErrorData):
    """リクエストの読み込みがタイムアウトした場合のエラー情報
    (requests.exceptions.ReadTimeout)"""

    def error_message(self) -> str:
        return f"読み込みがタイムアウトしました: {self.exception_name}: {self.args}"


#
# API
#

class ApiRequestErrorData(JDIErrorData):
    """
    APIエラー情報 (抽象クラス)

    Attributes
    ----------
    api_type : APIType
        APIの種類
    api_name : str
        APIの名前
    """
    def __init__(self,
                 api_type:Union[APIType, str],
                 e:Union[Exception, str, dict, None]=None):
        """APIエラー情報 (抽象クラス)

        Parameters
        ----------
        api_type : APIType
            APIの種類
        e : Exception | str | dict | None
            例外、またはエラーメッセージ
            dict の場合はエラー詳細を格納した辞書
        """
        super().__init__(e)
        self._details["api_type"] = api_type if isinstance(api_type, str) else api_type.name

    @property
    def api_type(self) -> APIType:
        """APIの種類

        Returns
        -------
        APIType
            APIの種類
        """
        return APIType[self._details["api_type"]]

    @property
    def api_name(self) -> str:
        """APIの名前

        Returns
        -------
        str
            APIの名前
        """
        return API_TYPE_NAME[self.api_type]

    @abstractmethod
    def error_message(self) -> str:
        """エラー情報

        Returns
        -------
        str
            エラーメッセージ
        """

class ApiInvalidParameterError(ApiRequestErrorData):
    """APIのパラメータが不正な場合のエラー情報 (Status code: 400, code: 400003)"""
    def __init__(self,
                 api_type:Union[APIType, str],
                 response:Union[dict, str],
                 e:Union[Exception, str, dict, None]=None):
        """APIのパラメータが不正な場合のエラー情報

        Parameters
        ----------
        api_type : APIType | str
            APIの種類
        response : dict | str
            APIのレスポンス
            str の場合はレスポンスを結合した文字列 (JSONとの変換用)
        e : Exception | str | dict | None
            例外、またはエラーメッセージ
            dict の場合はエラー詳細を格納した辞書
        """
        super().__init__(api_type, e)
        if isinstance(response, dict):
            self._details["response"] = " / ".join(response.get("detail", []))
        else:
            self._details["response"] = response

    def error_message(self) -> str:
        return f"{self.api_name} の取得に失敗しました。" \
               f"パラメータが不正です (ステータスコード 400): {self._details['response']} "

class ApiInvalidJsonFormatError(ApiRequestErrorData):
    """APIのJSONの形式が不正な場合のエラー情報 (Status code: 400, code: 400100)"""
    def __init__(self,
                 api_type:Union[APIType, str],
                 response:Union[dict, str],
                 e:Union[Exception, str, dict, None]=None):
        """APIのJSONの形式が不正な場合のエラー情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        response : dict
            APIのレスポンス
            str の場合はレスポンスを結合した文字列 (JSONとの変換用)
        e : Exception | str | dict | None
            例外、またはエラーメッセージ
            dict の場合はエラー詳細を格納した辞書
        """
        super().__init__(api_type, e)
        if isinstance(response, dict):
            self._details["response"] = " / ".join(response.get("message", []))
        else:
            self._details["response"] = response

    def error_message(self) -> str:
        return f"{self.api_name} の取得に失敗しました。" \
               f"JSONの形式が不正です (ステータスコード 400): {self._details['response']}"

class ApiCommonIdSyncFailedError(ApiRequestErrorData):
    """APIの共通IDとの連携に失敗した場合のエラー情報 (Status code: 400, code: 400900)"""
    def error_message(self) -> str:
        return f"{self.api_name} の取得に失敗しました。" \
               f"共通IDとの連携に失敗しました (ステータスコード 400)"

class ApiDataNotFoundError(ApiRequestErrorData):
    """APIのデータが見つからない場合のエラー情報 (Status code: 404)"""
    def __init__(self,
                 api_type:Union[APIType, str],
                 target:str,
                 e:Union[Exception, str, dict, None]=None):
        """APIのデータが見つからない場合のエラー情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        target : str
            対象 (クエリ文字列など)
        e : Exception | str | dict | None
            例外、またはエラーメッセージ
            dict の場合はエラー詳細を格納した辞書
        """
        super().__init__(api_type, e)
        self._details["target"] = target

    def error_message(self) -> str:
        return f"{self.api_name} の取得に失敗しました。" \
               f"対象のデータが見つかりません (ステータスコード 404; ターゲット:{self._details['target']})"

class ApiUnexpectedError(ApiRequestErrorData):
    """APIの予期しないエラーが発生した場合のエラー情報 (Status code: 500)"""
    def error_message(self) -> str:
        return f"{self.api_name} の取得に失敗しました。" \
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

#
# 処理中のエラー
# 基本的に開発者側の（コードの）問題
#

# 開発者側に問題がある場合のエラー情報
class DeveloperErrorData(JDIErrorData):
    """開発者側に問題がある場合のエラー情報"""
    def error_message(self) -> str:
        return "コードに問題があります。"

class NotInitializedError(DeveloperErrorData):
    """初期化されていない場合のエラー情報"""
    def error_message(self) -> str:
        msg = super().error_message()
        return msg + "初期化されていません。ログを確認し、初期化処理の失敗原因を確認してください。"

class ApiClientNotPrepared(DeveloperErrorData):
    """APIクライアントが準備されていない場合のエラー情報"""
    def error_message(self) -> str:
        msg = super().error_message()
        if self.args:
            return msg + "APIクライアントが準備されていません。" \
                   f"エラー: {self.args}"
        return msg + "APIクライアントが準備されていません。APIのトークンが正しく設定されているかなどを確認してください。"

class DatabaseConnectionNotPrepared(DeveloperErrorData):
    """データベース接続が準備されていない場合のエラー情報"""
    def error_message(self) -> str:
        msg = super().error_message()
        if self.args:
            return msg + "データベース接続が準備されていません。" \
                   f"エラー: {self.args}"
        return msg + "データベース接続が準備されていません。データベースのパスが正しく設定されているかなどを確認してください。"

class DatabaseNotPrepared(DeveloperErrorData):
    """データベースが準備されていない場合のエラー情報"""
    def error_message(self) -> str:
        msg = super().error_message()
        if self.args:
            return msg + "データベースが準備されていません。" \
                   f"エラー: {self.args}"
        return msg + "データベースが準備されていません。データベースのパスが正しく設定されているかなどを確認してください。"


#
# JSONとの変換
#

_class_registry: Dict[str, type[JDIErrorData]] = {
    "UnexpectedError": UnexpectedError,
    "TokenNotFoundError": TokenNotFoundError,
    "TokenMissingEnvEmpty": TokenMissingEnvEmpty,
    "TokenMissingEnvNotFound": TokenMissingEnvNotFound,
    "TokenInvalid": TokenInvalid,
    "DatabaseConnectionFailed": DatabaseConnectionFailed,
    "RequestConnectionError": RequestConnectionError,
    "RequestReadTimeout": RequestReadTimeout,
    "ApiInvalidParameterError": ApiInvalidParameterError,
    "ApiInvalidJsonFormatError": ApiInvalidJsonFormatError,
    "ApiCommonIdSyncFailedError": ApiCommonIdSyncFailedError,
    "ApiDataNotFoundError": ApiDataNotFoundError,
    "ApiUnexpectedError": ApiUnexpectedError,
    # 開発者エラー
    "NotInitializedError": NotInitializedError,
    "ApiClientNotPrepared": ApiClientNotPrepared,
    "DatabaseConnectionNotPrepared": DatabaseConnectionNotPrepared,
    "DatabaseNotPrepared": DatabaseNotPrepared,
}
"""エラークラスの登録 (JSONとの変換用)"""

def from_json(name:str, kwargs:dict) -> JDIErrorData:
    """JSONからエラー情報を生成

    Parameters
    ----------
    name : str
        エラークラス名
    kwargs : dict
        エラー情報
        JDIErrorData.asdict() で取得した辞書

    Returns
    -------
    JDIErrorData
        エラー情報
    """
    if name not in _class_registry:
        return UnexpectedError(f"Invalid warning class name: {name}")
    return _class_registry[name](**kwargs)
