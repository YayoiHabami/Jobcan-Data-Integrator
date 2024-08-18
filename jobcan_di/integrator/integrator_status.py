"""
Jobcan Data Integrator クラスのステータス管理クラス

Classes
-------
- `AppProgress`: アプリケーションの進捗状況を管理するクラス
- `FetchFailureRecord`: APIでデータ取得に失敗した対象を保持するクラス
- `JobcanDIStatus`: Jobcan Data Integrator クラスのステータス管理クラス
"""
from dataclasses import dataclass
import json
from os import path, makedirs
from typing import Dict, Optional, Union, Tuple

from .progress_status import (
    ProgressStatus, DetailedProgressStatus, TerminatingStatus,
    APIType, get_detailed_progress_status_from_str
)


@dataclass
class AppProgress:
    """アプリケーションの進捗状況を管理するクラス
    """
    status_outline: ProgressStatus = ProgressStatus.TERMINATING
    status_detail: Optional[DetailedProgressStatus] = TerminatingStatus.COMPLETED

    def is_completed(self) -> bool:
        """アプリケーションの進捗が完了しているかどうか

        Returns
        -------
        bool
            完了している場合は True
        """
        return self.status_detail == TerminatingStatus.COMPLETED

    def get(self) -> Tuple[ProgressStatus, DetailedProgressStatus]:
        """進捗状況を取得する

        Returns
        -------
        Tuple[ProgressStatus, DetailedProgressStatus]
            進捗状況
        """
        return self.status_outline, self.status_detail

    def set(self, status_outline:ProgressStatus, status_detail:DetailedProgressStatus) -> None:
        """進捗状況を設定する

        Parameters
        ----------
        status_outline : ProgressStatus
            大まかな進捗状況
        status_detail : DetailedProgressStatus
            詳細な進捗状況
        """
        self.status_outline = status_outline
        self.status_detail = status_detail


class FetchFailureRecord:
    """APIでデータ取得に失敗した対象を保持するクラス"""

    def __init__(
            self,
            basic_data:Optional[Dict[str, list[str]]] = None,
            request_detail:Optional[Dict[Union[str, int], list[str]]] = None
        ) -> None:
        """コンストラクタ

        Parameters
        ----------
        basic_data : Dict[str, list[str]], optional
            申請書(詳細)を除いた、基本データの取得に失敗した対象
        request_detail : Dict[int, list[str]], optional
            申請書(詳細)の取得に失敗した対象、
            JSON形式からの復元のためにキーが文字列であることを許容

        Notes
        -----
        以下のように辞書型との相互変換が可能

        ```python
        record = FetchFailureRecord()
        record.add(APIType.USER_V3, "123")
        record.add(APIType.REQUEST_DETAIL, "456", form_id=789)
        record.asdict()
        # -> {'basic_data': {"USER_V3": ['123']}, 'request_detail': {789: ['456']}}
        record2 = FetchFailureRecord(**record.asdict())
        record2.asdict()
        # -> {'basic_data': {"USER_V3": ['123']}, 'request_detail': {789: ['456']}}
        ```
        """
        self.basic_data: Dict[APIType, list[str]] = {}
        """申請書(詳細)を除いた、基本データの取得に失敗した対象"""
        self.request_detail: Dict[int, list[str]] = {}
        """申請書(詳細)の取得に失敗した対象、キーはform_id、値は取得に失敗したrequest_id"""

        if basic_data is None and request_detail is None:
            self.clear()
            return

        # 基本データに関するデータを取得
        if basic_data is not None:
            for api_type, targets in basic_data.items():
                self.basic_data[APIType[api_type]] = targets

        # 申請書(詳細)に関するデータを取得
        if request_detail is not None:
            for form_id, targets in request_detail.items():
                self.request_detail[int(form_id)] = targets

    def add(self, api_type:APIType, target:str, *, form_id:Optional[int]=None) -> None:
        """データ取得に失敗した対象を追加する

        Parameters
        ----------
        api_type : APIType
            取得に失敗したAPIの種類
        target : str
            取得に失敗した対象のID
        form_id : int, optional
            取得に失敗した申請書のID、api_type が REQUEST_DETAIL の場合のみ指定
        """
        if api_type == APIType.REQUEST_DETAIL:
            if form_id is None:
                raise ValueError("form_id must be specified when api_type is REQUEST_DETAIL")
            if form_id not in self.request_detail:
                self.request_detail[form_id] = []
            self.request_detail[form_id].append(target)
        else:
            self.basic_data[api_type].append(target)

    def get(self, api_type:APIType, *, form_id:Optional[int]=None) -> list[str]:
        """データ取得に失敗した対象を取得する

        Parameters
        ----------
        api_type : APIType
            取得に失敗したAPIの種類
        form_id : int, optional
            取得に失敗した申請書のID、api_type が REQUEST_DETAIL の場合のみ指定

        Returns
        -------
        list[str]
            取得に失敗した対象のID
        """
        if api_type == APIType.REQUEST_DETAIL:
            if form_id is None:
                raise ValueError("form_id must be specified when api_type is REQUEST_DETAIL")
            return self.request_detail.get(form_id, [])
        else:
            return self.basic_data.get(api_type, [])

    def get_request_detail(self) -> Dict[int, list[str]]:
        """申請書(詳細)の取得に失敗した対象を取得する

        Returns
        -------
        Dict[int, list[str]]
            取得に失敗したform_idと、その申請書に対して取得に失敗したrequest_idの辞書
        """
        return self.request_detail

    def clear(self) -> None:
        """初期化する"""
        for api_type in APIType:
            # 申請書(詳細)以外のデータは空リストで初期化
            if api_type != APIType.REQUEST_DETAIL:
                self.basic_data[api_type] = []

        self.request_detail = {}

    def asdict(self) -> dict:
        """辞書形式に変換する

        Returns
        -------
        dict
            変換した辞書

        Notes
        -----
        変換後の辞書は以下のような形式

        ```python
        {
            "basic_data": {"API_TYPE": [str, ...]},
            "request_detail": {int: [str, ...]}
        }
        ```
        """
        return {
            "basic_data": {k.name: v for k, v in self.basic_data.items()},
            "request_detail": self.request_detail
        }

class JobcanDIStatus:
    """Jobcan Data Integrator クラスのステータス管理クラス

    Attributes
    ----------
    progress : AppProgress
        前回/現在の進捗状況
        `.load()` での読み込み時に `ProgressStatus.TERMINATING` かつ
        `TerminatingStatus.COMPLETED` の場合は進捗状況をリセットする
        (`ProgressStatus.INITIALIZING` & `None` に設定)
    fetch_failure_record : FetchFailureRecord
        データ取得に失敗した対象
    config_file_path : str, default ""
        優先して読み込むコンフィグファイル
    form_api_last_access : Dict[int, str]
        申請書(概要)のAPIで最後にデータを取得した日時、
        キーはform_id、値は日時(文字列)
    """

    def __init__(self, dir_path:str):
        """コンストラクタ

        Parameters
        ----------
        dir_path : str
            ステータス用ファイルのディレクトリパス
        """
        self._dir_path = dir_path
        if not path.exists(dir_path):
            # ディレクトリが存在しない場合は作成
            makedirs(dir_path)

        self._file_path = path.join(dir_path, "app_status")

        self.progress = AppProgress()
        """前回/現在の進捗状況"""
        self.fetch_failure_record = FetchFailureRecord()
        """データ取得に失敗した対象"""
        self.config_file_path = ""
        """優先して読み込むコンフィグファイル"""
        self.form_api_last_access: Dict[int, str] = {}
        """申請書(概要)のAPIで最後にデータを取得した日時"""

    def load(self) -> None:
        """ステータスファイルを読み込む"""
        if not path.exists(self._file_path):
            return

        with open(self._file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 進捗状況の読み込み
        p_outline = ProgressStatus[data["status_outline"]]
        p_detail = get_detailed_progress_status_from_str(data["status_outline"],
                                                         data["status_detail"])
        if p_outline == ProgressStatus.TERMINATING and p_detail == TerminatingStatus.COMPLETED:
            # 進捗状況が終了済みの場合は進捗状況をリセット
            p_outline = ProgressStatus.INITIALIZING
            p_detail = None
        self.progress = AppProgress(status_outline = p_outline, status_detail = p_detail)

        # データ取得に失敗した対象の読み込み
        self.fetch_failure_record = FetchFailureRecord(**data["fetch_failure_record"])

        # 優先して読み込むコンフィグファイルの読み込み
        self.config_file_path = data.get("config_file_path", "")

        # 申請書(概要)のAPIで最後にデータを取得した日時の読み込み
        self.form_api_last_access = {
            int(k): v for k, v in data.get("form_api_last_access", {}).items()
        }

    def save(self) -> None:
        """ステータスファイルに保存する"""
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump({
                "status_outline": self.progress.status_outline.name,
                "status_detail": self.progress.status_detail.name,
                "fetch_failure_record": self.fetch_failure_record.asdict(),
                "config_file_path": self.config_file_path,
                "form_api_last_access": self.form_api_last_access
            }, f)
