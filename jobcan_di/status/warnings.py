"""
jobcan_di.status.warnings

警告情報を提供するモジュール

Classes
-------
- `JDIWarning` : 警告 (列挙型)
- `JDIWarningData` : 警告情報 (抽象クラス)
- `UnexpectedWarning` : 予期しないエラーが発生した場合の警告情報
- `InvalidConfigFilePath` : コンフィグファイルのパスが不正な場合の警告情報
- `InvalidStatusFilePath` : ステータスファイルのパスが不正な場合の警告情報
- `InvalidLogFilePath` : ログファイルのパスが不正な場合の警告情報
- `ApiRequestWarningData` : API警告情報 (抽象クラス)
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
from copy import deepcopy
from typing import Optional, Union, Dict

from .progress import APIType, API_TYPE_NAME



class JDIWarningData(metaclass=ABCMeta):
    """警告情報"""
    def __init__(self, e:Union[Exception, str, dict, None]=None):
        """コンストラクタ

        Parameters
        ----------
        e : Exception | str | dict | None
            例外、エラーメッセージ、エラー情報
            dictの場合は、エラー情報を格納した辞書
        """
        self.details: dict = {}

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
    def warning_message(self) -> str:
        """警告メッセージの取得

        Returns
        -------
        str
            警告メッセージ
        """

class UnexpectedWarning(JDIWarningData):
    """予期しないエラーが発生した場合の警告情報"""
    def warning_message(self) -> str:
        if self.exception_name is None:
            return "予期しないエラーが発生しました。"

        return f"予期しないエラーが発生しました。" \
                f"例外: {self.exception_name} - {self.args}"



#
# ファイルパス
#

class InvalidConfigFilePath(JDIWarningData):
    """指定されたコンフィグファイルのパスが不正な場合の警告情報"""
    def __init__(self, file_path:str, e:Union[Exception, str, dict, None]=None):
        """指定されたコンフィグファイルのパスが不正な場合の警告情報

        Parameters
        ----------
        file_path : str
            コンフィグファイルのパス
        e : Exception | str | dict | None
            例外、エラーメッセージ、エラー情報
            dictの場合は、エラー情報を格納した辞書
        """
        super().__init__(e)
        self._details["file_path"] = file_path

    def warning_message(self) -> str:
        return f"指定されたコンフィグファイルのパス ({self._details['file_path']}) が不正です。" \
               "デフォルトのコンフィグファイルを使用します。"

class InvalidStatusFilePath(JDIWarningData):
    """指定されたステータスファイルのパスが不正な場合の警告情報"""
    def __init__(self, file_path:str, e:Union[Exception, str, dict, None]=None):
        """指定されたステータスファイルのパスが不正な場合の警告情報

        Parameters
        ----------
        file_path : str
            ステータスファイルのパス
        e : Exception | str | dict | None
            例外、エラーメッセージ、エラー情報
            dictの場合は、エラー情報を格納した辞書
        """
        super().__init__(e)
        self._details["file_path"] = file_path

    def warning_message(self) -> str:
        return f"指定されたステータスファイルのパス ({self._details['file_path']}) が不正です。" \
               "デフォルトのファイルを使用します。"

class InvalidLogFilePath(JDIWarningData):
    """指定されたログファイルのパスが不正な場合の警告情報"""
    def __init__(self, file_path:str, e:Union[Exception, str, dict, None]=None):
        """指定されたログファイルのパスが不正な場合の警告情報

        Parameters
        ----------
        file_path : str
            ログファイルのパス
        e : Exception | str | dict | None
            例外、エラーメッセージ、エラー情報
            dictの場合は、エラー情報を格納した辞書
        """
        super().__init__(e)
        self._details["file_path"] = file_path

    def warning_message(self) -> str:
        return f"指定されたログファイルのパス ({self._details['file_path']}) が不正です。" \
               "デフォルトのログファイルを使用します。"



#
# API (general)
#

class ApiRequestWarningData(JDIWarningData):
    """
    API警告情報 (抽象クラス)

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
    def warning_message(self) -> str:
        """警告メッセージの取得

        Returns
        -------
        str
            警告メッセージ
        """

class ApiInvalidParameterWarning(ApiRequestWarningData):
    """APIのパラメータが不正な場合の警告情報 (Status code: 400, code: 400003)"""
    def __init__(self,
                 api_type:Union[APIType, str],
                 response:Union[dict, str],
                 e:Union[Exception, str, dict, None]=None):
        """APIのパラメータが不正な場合の警告情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        response : dict
            APIのレスポンス
        """
        super().__init__(api_type, e)
        if isinstance(response, dict):
            self._details["response"] = " / ".join(response.get("detail", []))
        else:
            self._details["response"] = response

    def warning_message(self) -> str:
        return f"{self.api_name} の取得に失敗しました。" \
               f"パラメータが不正です (ステータスコード 400): {self._details['response']} "

class ApiInvalidJsonFormatWarning(ApiRequestWarningData):
    """APIのJSONの形式が不正な場合の警告情報 (Status code: 400, code: 400100)"""
    def __init__(self,
                 api_type:Union[APIType, str],
                 response:Union[dict, str],
                 e:Union[Exception, str, dict, None]=None):
        """APIのJSONの形式が不正な場合の警告情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        response : dict
            APIのレスポンス
        """
        super().__init__(api_type, e)
        if isinstance(response, dict):
            self._details["response"] = " / ".join(response.get("message", []))
        else:
            self._details["response"] = response

    def warning_message(self) -> str:
        return f"{self.api_name} の取得に失敗しました。" \
               f"JSONの形式が不正です (ステータスコード 400): {self._details['response']}"

class ApiCommonIdSyncFailedWarning(ApiRequestWarningData):
    """APIの共通IDとの連携に失敗した場合の警告情報 (Status code: 400, code: 400900)"""
    def warning_message(self) -> str:
        return f"{self.api_name} の取得に失敗しました。" \
               f"共通IDとの連携に失敗しました (ステータスコード 400)"

class ApiDataNotFoundWarning(ApiRequestWarningData):
    """APIのデータが見つからない場合の警告情報 (Status code: 404)"""
    def __init__(self,
                 api_type:Union[APIType, str],
                 target:str,
                 e:Union[Exception, str, dict, None]=None):
        """APIのデータが見つからない場合の警告情報

        Parameters
        ----------
        api_type : APIType
            APIの種類
        target : str
            対象 (クエリ文字列など)
        e : Exception | str | dict | None
            例外、エラーメッセージ
            dict の場合はエラー詳細を格納した辞書
        """
        super().__init__(api_type, e)
        self._details["target"] = target

    def warning_message(self) -> str:
        return f"{self.api_name} の取得に失敗しました。" \
               f"対象のデータが見つかりません (ステータスコード 404; ターゲット:{self._details['target']})"

class ApiUnexpectedWarning(ApiRequestWarningData):
    """APIの予期しないエラーが発生した場合の警告情報 (Status code: 500)"""
    def warning_message(self) -> str:
        return f"{self.api_name} の取得に失敗しました。" \
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

class FormDetailApiInvalidParameterWarning(ApiRequestWarningData):
    """申請書データ (詳細) のAPIのパラメータが不正な場合の警告情報 (Status code: 400)"""
    def __init__(self,
                 response:Union[dict, str],
                 e:Union[Exception, str, dict, None]=None):
        """申請書データ (詳細) のAPIのパラメータが不正な場合の警告情報

        Parameters
        ----------
        response : dict | str
            APIのレスポンス
        e : Exception | str | dict | None
            例外、エラーメッセージ
            dict の場合はエラー詳細を格納した辞書
        """
        super().__init__(APIType.REQUEST_DETAIL)
        if isinstance(response, dict):
            self._details["response"] = " / ".join(response.get("detail", []))
        else:
            self._details["response"] = response

    def warning_message(self) -> str:
        return f"{API_TYPE_NAME[APIType.REQUEST_DETAIL]} の取得に失敗しました。" \
               f"パラメータが不正です (ステータスコード 400): {self._details['response']} "

class FormDetailApiDataNotFoundWarning(ApiRequestWarningData):
    """指定された申請書データ (詳細) が見つからない場合の警告情報 (Status code: 404)"""
    def __init__(self, request_id:str, e:Union[Exception, str, dict, None]=None):
        """指定された申請書データ (詳細) が見つからない場合の警告情報

        Parameters
        ----------
        request_id : str
            対象の申請書ID
        e : Exception | str | dict | None
            例外、エラーメッセージ
            dict の場合はエラー詳細を格納した辞書
        """
        super().__init__(APIType.REQUEST_DETAIL, e)
        self._details["request_id"] = request_id

    def warning_message(self) -> str:
        return f"{API_TYPE_NAME[APIType.REQUEST_DETAIL]} の取得に失敗しました。" \
               f"指定された申請書データが見つかりません: {self._details['request_id']} "

class FormDetailApiUnexpectedWarning(ApiRequestWarningData):
    """申請書データ (詳細) のAPIで予期しないエラーが発生した場合の警告情報 (Status code: 500)"""
    def __init__(self,
                 status_code:Union[int, str],
                 e:Union[Exception, str, dict, None]=None):
        """申請書データ (詳細) のAPIで予期しないエラーが発生した場合の警告情報

        Parameters
        ----------
        status_code : int | str
            ステータスコード
        e : Exception | str | dict | None
            例外、エラーメッセージ
            dict の場合はエラー詳細を格納した辞書
        """
        super().__init__(APIType.REQUEST_DETAIL, e)
        self._details["status_code"] = str(status_code)

    def warning_message(self) -> str:
        return f"{API_TYPE_NAME[APIType.REQUEST_DETAIL]} の取得に失敗しました。" \
               f"予期しないエラーが発生しました (ステータスコード {self._details['status_code']})"

def get_form_detail_api_warning(status_code:int,
                                res:dict,
                                request_id:str="") -> ApiRequestWarningData:
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
    def __init__(self,
                 api_type:Union[APIType, str],
                 e:Union[Exception, str, dict, None]=None):
        """DBのデータ更新に失敗した場合の警告情報

        Parameters
        ----------
        api_type : APIType
            対象のAPIタイプ
        e : Exception, default None
            例外
        """
        super().__init__(e)
        self._details["api_type"] = api_type if isinstance(api_type, str) else api_type.name

    def warning_message(self) -> str:
        if self.exception_name:
            return f"{API_TYPE_NAME[self._details['api_type']]} のデータ更新に失敗しました。" \
                   f"例外: {self.exception_name} - {self.args}"
        return f"{API_TYPE_NAME[self._details['api_type']]} のデータ更新に失敗しました。"


#
# JSONとの変換
#

_class_registry: Dict[str, JDIWarningData] = {
    "UnexpectedWarning": UnexpectedWarning,
    "InvalidConfigFilePath": InvalidConfigFilePath,
    "InvalidStatusFilePath": InvalidStatusFilePath,
    "InvalidLogFilePath": InvalidLogFilePath,
    "ApiInvalidParameterWarning": ApiInvalidParameterWarning,
    "ApiInvalidJsonFormatWarning": ApiInvalidJsonFormatWarning,
    "ApiCommonIdSyncFailedWarning": ApiCommonIdSyncFailedWarning,
    "ApiDataNotFoundWarning": ApiDataNotFoundWarning,
    "ApiUnexpectedWarning": ApiUnexpectedWarning,
    "FormDetailApiInvalidParameterWarning": FormDetailApiInvalidParameterWarning,
    "FormDetailApiDataNotFoundWarning": FormDetailApiDataNotFoundWarning,
    "FormDetailApiUnexpectedWarning": FormDetailApiUnexpectedWarning,
    "DBUpdateFailed": DBUpdateFailed
}
"""警告情報のクラスを登録 (JSONとの変換用)"""

def from_json(name:str, kwargs:dict) -> JDIWarningData:
    """JSONから警告情報を生成

    Parameters
    ----------
    name : str
        警告情報のクラス名
    kwargs : dict
        警告情報の引数

    Returns
    -------
    JDIWarningData
        警告情報
    """
    if name not in _class_registry:
        raise ValueError(f"Invalid warning class name: {name}")
    return _class_registry[name](**kwargs)
