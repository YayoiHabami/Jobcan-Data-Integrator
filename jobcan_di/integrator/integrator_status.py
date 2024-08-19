"""
Jobcan Data Integrator クラスのステータス管理クラス

Classes
-------
- `AppProgress`: アプリケーションの進捗状況を管理するクラス
- `FetchFailureRecord`: APIでデータ取得に失敗した対象を保持するクラス
- `JobcanDIStatus`: Jobcan Data Integrator クラスのステータス管理クラス

Notes
-----
`AppProgress`では`.specifics`として、処理済みの具体的な対象 (読み込み済みのrequest_idなど) を保持する。
一方、`FetchFailureRecord`では、処理に失敗した対象をAPIの種類ごとに保持する。この違いは以下の通り。

- `AppProgress`: 進捗状態 (`ProgressStatus`, `DetailedProgressStatus`) が進行する度に`.specifics`が初期化される
  - エラーが発生した際に、その進捗状態で具体的にどこまで処理が完了しているかを記録するために使用される
- `FetchFailureRecord`: APIの種類ごとに処理に失敗した対象を保持し、最後まで処理が完了した後も保持される
  - 次回の処理時に、前回の処理で失敗した対象を再度処理するために使用される
"""
import json
from os import path, makedirs
from typing import Dict, Optional, Union, Tuple

from .progress_status import (
    ProgressStatus, DetailedProgressStatus, TerminatingStatus,
    APIType, get_detailed_progress_status_from_str
)



class AppProgress:
    """アプリケーションの進捗状況を管理するクラス

    Usage
    -----
    1. 辞書形式との相互変換

    ```python
    progress = AppProgress()
    data = progress.asdict()
    new_progress = AppProgress(**data)
    ```

    2. 進捗状況の設定・取得

    ```python
    progress = AppProgress()
    progress.set(ProgressStatus.INITIALIZING, InitializingStatus.COMPLETED)

    outline, detail = progress.get()
    ```

    3. より詳細な進捗状況の設定 (request_idなどの追加)

    ```python
    processed_request_ids = ["sa-10", "sa-11", "sa-12"]
    progress.add_specifics(processed_request_ids)

    specifics = progress.specifics
    ```
    """
    def __init__(self, *,
                 outline: Union[ProgressStatus, str] = ProgressStatus.TERMINATING,
                 detail: Union[DetailedProgressStatus, str, None] = TerminatingStatus.COMPLETED,
                 specifics: Optional[list[Union[str, int]]] = None) -> None:
        """コンストラクタ

        Parameters
        ----------
        outline : ProgressStatus | str, optional
            大まかな進捗状況、
            文字列の場合は `ProgressStatus` に変換される
        detail : DetailedProgressStatus | str | None, optional
            詳細な進捗状況、
            文字列の場合は `DetailedProgressStatus` に変換される
        specifics : list[str | int], optional
            処理済みの具体的な対象 (読み込み済みのrequest_idなど)
        """
        po = ProgressStatus[outline] if isinstance(outline, str) else outline
        if isinstance(detail, str):
            pd = get_detailed_progress_status_from_str(po.name, detail)
        else:
            pd = detail

        self._outline: ProgressStatus = po
        """大まかな進捗状況"""
        self._detail: Optional[DetailedProgressStatus] = pd
        """詳細な進捗状況"""
        self._specifics: list[Union[str, int]] = [] if specifics is None else specifics
        """処理済みの具体的な対象 (読み込み済みのrequest_idなど)"""

    def is_completed(self) -> bool:
        """アプリケーションの進捗が完了しているかどうか

        Returns
        -------
        bool
            完了している場合は True
        """
        return self._detail == TerminatingStatus.COMPLETED

    def get(self) -> Tuple[ProgressStatus, Optional[DetailedProgressStatus]]:
        """進捗状況を取得する

        Returns
        -------
        Tuple[ProgressStatus, Optional[DetailedProgressStatus]]
            進捗状況
        """
        return self._outline, self._detail

    def set(self, outline:ProgressStatus,
            detail: Optional[DetailedProgressStatus]) -> None:
        """進捗状況を設定する。指定された進捗状況が同じ場合は何もしない

        Parameters
        ----------
        outline : ProgressStatus
            大まかな進捗状況
        detail : DetailedProgressStatus | None
            詳細な進捗状況

        Notes
        -----
        - `.specifics`は空リストに初期化される
        """
        if self._outline == outline and self._detail == detail:
            # 進捗状況が同じ場合は何もしない
            return

        self._outline = outline
        self._detail = detail
        self._specifics = []

    @property
    def specifics(self) -> list[Union[str, int]]:
        """処理済みの具体的な対象を取得する

        Returns
        -------
        list[str | int]
            処理済みの具体的な対象
        """
        return self._specifics

    def add_specifics(self, specifics:Union[list[Union[str, int]], Union[str, int]]) -> None:
        """処理済みの具体的な対象を追加する

        Parameters
        ----------
        specifics : list[str | int] | str | int
            追加する対象
        """
        if isinstance(specifics, list):
            self._specifics.extend(specifics)
        else:
            self._specifics.append(specifics)

    def reset_specifics(self) -> None:
        """specificsをリセットする"""
        self._specifics = []

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
            "outline": "ProgressStatus",
            "detail": "DetailedProgressStatus",
            "specifics": list[str | int]
        }
        ```
        """
        return {
            "outline": self._outline.name,
            "detail": None if self._detail is None else self._detail.name,
            "specifics": self._specifics
        }

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
        self._basic_data: Dict[APIType, list[str]] = {}
        """申請書(詳細)を除いた、基本データの取得に失敗した対象"""
        self._request_detail: Dict[int, list[str]] = {}
        """申請書(詳細)の取得に失敗した対象、キーはform_id、値は取得に失敗したrequest_id"""

        if basic_data is None and request_detail is None:
            # データが指定されていない場合は初期化のみ行う
            self.clear()
            return

        # 基本データに関するデータを取得
        if basic_data is not None:
            for api_type, targets in basic_data.items():
                self._basic_data[APIType[api_type]] = targets

        # 申請書(詳細)に関するデータを取得
        if request_detail is not None:
            for form_id, targets in request_detail.items():
                self._request_detail[int(form_id)] = targets

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
            if form_id not in self._request_detail:
                self._request_detail[form_id] = []
            self._request_detail[form_id].append(target)
        else:
            self._basic_data[api_type].append(target)

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
            return self._request_detail.get(form_id, [])
        else:
            return self._basic_data.get(api_type, [])

    def get_request_detail(self) -> Dict[int, list[str]]:
        """申請書(詳細)の取得に失敗した対象を取得する

        Returns
        -------
        Dict[int, list[str]]
            取得に失敗したform_idと、その申請書に対して取得に失敗したrequest_idの辞書
        """
        return self._request_detail

    def clear(self) -> None:
        """初期化する"""
        for api_type in APIType:
            # 申請書(詳細)以外のデータは空リストで初期化
            if api_type != APIType.REQUEST_DETAIL:
                self._basic_data[api_type] = []

        self._request_detail = {}

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
            "basic_data": {k.name: v for k, v in self._basic_data.items()},
            "request_detail": self._request_detail
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

        self.progress = AppProgress(outline = ProgressStatus.INITIALIZING,
                                    detail = None)
        """前回/現在の進捗状況"""
        self.fetch_failure_record = FetchFailureRecord()
        """データ取得に失敗した対象"""
        self.config_file_path = ""
        """優先して読み込むコンフィグファイル"""
        self.form_api_last_access: Dict[int, str] = {}
        """申請書(概要)のAPIで最後にデータを取得した日時"""

    def _init_status(self) -> None:
        """ステータスを初期化する"""
        self.progress = AppProgress(outline = ProgressStatus.INITIALIZING,
                                    detail = None)
        self.fetch_failure_record.clear()
        self.config_file_path = ""
        self.form_api_last_access = {}

    def load(self) -> None:
        """ステータスファイルを読み込む

        Notes
        -----
        - 指定されたファイルが存在しない場合はデータを初期化する
        - 指定されたファイルのデータが不完全な場合、読み込める部分だけを利用する
        """
        self._init_status()

        if not path.exists(self._file_path):
            return

        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError:
            # 指定されたファイルがJSON形式でない場合は初期化されたデータをそのまま利用する
            return

        self._load(data)

    def _load(self, data:dict) -> None:
        """読み込んだデータをステータスに反映する

        Parameters
        ----------
        data : dict
            読み込んだデータ
        """
        # 進捗状況の読み込み
        if (ap := data.get("progress", None)) is not None:
            # "progress"の中に各要素が存在しない場合はデフォルト値を使用
            p_outline = ProgressStatus[ap.get("outline", ProgressStatus.INITIALIZING.name)]
            p_detail = get_detailed_progress_status_from_str(
                p_outline.name,
                ap.get("detail", TerminatingStatus.COMPLETED.name)
            )
            p_specifics = ap.get("specifics", [])

            if p_outline == ProgressStatus.TERMINATING and p_detail == TerminatingStatus.COMPLETED:
                # 進捗状況が終了済みの場合は進捗状況をリセット
                p_outline = ProgressStatus.INITIALIZING
                p_detail = None
                p_specifics = []
            self.progress = AppProgress(outline = p_outline,
                                        detail = p_detail,
                                        specifics=p_specifics)

        # データ取得に失敗した対象の読み込み
        try:
            # "fetch_failure_record" が存在する場合のみ読み込む
            if "fetch_failure_record" in data:
                self.fetch_failure_record = FetchFailureRecord(**data["fetch_failure_record"])
        except TypeError:
            # データ型が不正な場合はデータを読み込まない
            pass

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
                "progress": self.progress.asdict(),
                "fetch_failure_record": self.fetch_failure_record.asdict(),
                "config_file_path": self.config_file_path,
                "form_api_last_access": self.form_api_last_access
            }, f)
