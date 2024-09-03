"""
jobcan_di.gateway._core

gatewayパッケージのコアモジュール

Classes
-------
- ApiResponse: APIのレスポンスデータ
"""
from dataclasses import dataclass, field
from typing import Iterable, Optional, Union

from jobcan_di.status.errors import JDIErrorData
from jobcan_di.status.progress import APIType
from jobcan_di.status.warnings import JDIWarningData

@dataclass
class ApiResponse:
    """
    APIのレスポンスデータ

    Attributes
    ----------
    results : list[dict]
        レスポンスの結果を結合したもの。
        - basic_data および form_outline の場合: `"results"` の内容を連結したもの
    error : ie.JDIErrorData | iw.JDIWarningData | None
        エラー/警告情報、エラー/警告が発生しなかった場合はNone
    success : bool
        エラーが発生していないかどうか
    """
    results: list[dict] = field(default_factory=list)
    """レスポンスの結果を結合したもの"""
    error: Union[JDIErrorData, JDIWarningData, None] = None
    """エラー/警告情報、エラー/警告が発生しなかった場合はNone"""

    @property
    def success(self) -> bool:
        """エラーが発生していないかどうか"""
        return self.error is None


class FormOutline:
    """申請書(概要)のデータクラス

    Attributes
    ----------
    success : bool
        成功フラグ
    ids : set[str]
        request_idのセット
    last_access : str
        最終アクセス日時、形式は "YYYY/MM/DD HH:MM:SS"
    is_empty : bool
        idsが空かどうか
    """

    def __init__(self,
                 success: bool = False,
                 ids: Optional[Iterable[str]] = None,
                 last_access: str = ""):
        """コンストラクタ

        Parameters
        ----------
        success : bool
            成功フラグ
        ids : Iterable[str] | None
            request_idのリストまたはセット
        last_access : str
            最終アクセス日時、形式は "YYYY/MM/DD HH:MM:SS"
        """
        self.success: bool = success
        """成功フラグ"""
        self.ids: set[str] = set(ids) if ids else set()
        """request_idのセット"""
        self.last_access: str = last_access
        """最終アクセス日時、形式は "YYYY/MM/DD HH:MM:SS" """

    def add_ids(self, ids: Iterable[str]):
        """request_idをセットに追加

        Parameters
        ----------
        ids : Iterable[str]
            request_idのリストやセット
        """
        self.ids.update(ids)

    def remove_id(self, id_: str):
        """request_idをセットから削除

        Parameters
        ----------
        id_ : str
            request_id
        """
        self.ids.discard(id_)

    def remove_ids(self, ids: Iterable[str]):
        """request_idをセットから削除

        Parameters
        ----------
        ids : Iterable[str]
            request_idのリストやセット
        """
        self.ids.difference_update(ids)

    def asdict(self, json_format: bool = False) -> dict:
        """辞書に変換

        Parameters
        ----------
        json_format : bool
            Trueの場合、JSON形式の辞書に変換 (set -> list等)

        Returns
        -------
        dict
            変換された辞書
        """
        if json_format:
            return {"success": self.success,
                    "ids": list(self.ids),
                    "last_access": self.last_access}
        return {"success": self.success,
                "ids": self.ids,
                "last_access": self.last_access}

    @property
    def is_empty(self) -> bool:
        """セットが空かどうか

        Returns
        -------
        bool
            空の場合はTrue
        """
        return not bool(self.ids)

UNIQUE_IDENTIFIER_KEYS = {
    APIType.USER_V3: "user_code",
    APIType.GROUP_V1: "group_code",
    APIType.POSITION_V1: "position_code",
    APIType.FORM_V1: "id",
    APIType.REQUEST_OUTLINE: "id"
}
"""APIの種類に応じたユニークな識別子のキー"""
def get_unique_identifier(data:dict, api_type:APIType) -> Union[str, int, None]:
    """APIの種類に応じたユニークな識別子を取得する

    Parameters
    ----------
    data : dict
        取得したデータ (APIレスポンスの`"results"`の各要素)
    api_type : APIType
        APIの種類
    """
    if api_type in UNIQUE_IDENTIFIER_KEYS:
        return data.get(UNIQUE_IDENTIFIER_KEYS[api_type])
    return None
