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
from typing import Dict, Optional, Union, Tuple, Set, Iterable, Literal

from .progress_status import (
    ProgressStatus, DetailedProgressStatus, TerminatingStatus,
    APIType, get_detailed_progress_status_from_str,
    get_progress_status, get_detailed_progress_status
)
from .integrator_errors import JDIErrorData, from_json as error_from_json



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
                 specifics: Union[Iterable[Union[str, int]], None] = None
                 ) -> None:
        """コンストラクタ

        Parameters
        ----------
        outline : ProgressStatus | str, optional
            大まかな進捗状況、
            文字列の場合は `ProgressStatus` に変換される
        detail : DetailedProgressStatus | str | None, optional
            詳細な進捗状況、
            文字列の場合は `DetailedProgressStatus` に変換される
        specifics : set[str | int], optional
            処理済みの具体的な対象 (読み込み済みのrequest_idなど)、
            JSON形式からの復元のため、listによる表現を許容
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
        self._specifics: set[Union[str, int]] = set() if specifics is None else set(specifics)
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
        self._specifics = set()

    @property
    def specifics(self) -> Set[Union[str, int]]:
        """処理済みの具体的な対象を取得する

        Returns
        -------
        set[str | int]
            処理済みの具体的な対象
        """
        return self._specifics

    def add_specifics(self,
                      specifics:Union[Iterable[Union[str, int]], Union[str, int]]
                     ) -> None:
        """処理済みの具体的な対象を追加する

        Parameters
        ----------
        specifics : list[str | int] | str | int
            追加する対象
        """
        if isinstance(specifics, (str, int)):
            self._specifics.add(specifics)
        else:
            self._specifics.update(specifics)

    def reset_specifics(self) -> None:
        """specificsをリセットする"""
        self._specifics = set()

    def asdict(self, json_format:bool = False) -> dict:
        """辞書形式に変換する

        Returns
        -------
        dict
            変換した辞書
        json_format : bool, default False
            JSON形式に変換するかどうか (set -> list などの変換を行う)

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
            "specifics": list(self._specifics) if json_format else self._specifics
        }

    def is_future_process(
            self,
            progress:Union[APIType, Tuple[ProgressStatus, DetailedProgressStatus]],
            *, specific:Union[str, int, None]=None
        ) -> bool:
        """指定された処理が、現在進行中、または次以降に実施するものであるか。

        Parameters
        ----------
        progress : APIType | Tuple[ProgressStatus, DetailedProgressStatus]
            APIの種類、または進捗状況
        specific : str | int | None, optional
            進捗状況を確認する対象、指定されていない場合は全ての対象を確認する

        Returns
        -------
        bool
            完了している場合は True

        Notes
        -----
        - `progress`として`APIType`が指定された場合、内部的に
          `ProgressStatus`と`DetailedProgressStatus`に変換される
        - `specific`が指定されず、自身の`DetailedProgressStatus`が`GetBasicDataStatus.GET_POSITION`
          の場合について、`progress`の`DetailedProgressStatus`ごとの戻り値の例を以下に示す
          - `GetBasicDataStatus.GET_USER_V3`: `False` (処理済)
          - `GetBasicDataStatus.GET_POSITION`: `True` (処理中)
          - `GetFormDetailStatus.GET_DETAIL`: `True` (未処理)
        - `specific`が指定された場合も基本的には上と同様の判定を行うが、(処理中)のものについては
          以下のように判定する
          - `specific`が`.specifics`に含まれている場合: `False` (処理済)
          - それ以外: `True` (未処理/処理中)
        """
        if isinstance(progress, APIType):
            po = get_progress_status(progress)
            pd = get_detailed_progress_status(progress)
        else:
            po, pd = progress

        if po == self._outline:
            # 進捗状況(概要)が同じ
            if pd == self._detail:
                # 進捗状況(詳細)が同じ
                if specific is None:
                    # specificが指定されていない場合はTrue (処理中)
                    return True
                # specificが指定されている場合は、specificsに含まれているかどうかで判定
                return specific not in self._specifics

            # 進捗状況(詳細)が異なり、どちらもエラーでない場合
            return pd.value > self._detail.value

        # 進捗状況(概要)が異なり、どちらもエラーでない場合
        return po.value > self._outline.value


class FailureRecord:
    """各API関連の処理についてなんらかの失敗があった対象を保持するクラス

    Notes
    -----
    以下のように辞書型との相互変換が可能

    ```python
    record = FailureRecord()
    record.add(APIType.USER_V3, "123")
    record.add(APIType.REQUEST_DETAIL, "456", form_id=789)
    record.asdict()
    # -> {'basic_data': {"USER_V3": ['123']}, 'request_detail': {789: ['456']}}
    record2 = FailureRecord(**record.asdict())
    record2.asdict()
    # -> {'basic_data': {"USER_V3": ['123']}, 'request_detail': {789: ['456']}}
    ```
    """

    def __init__(
            self,
            basic_data:Optional[Dict[str, Iterable[str]]] = None,
            request_detail:Optional[Dict[Union[str, int], Iterable[str]]] = None
        ) -> None:
        """コンストラクタ

        Parameters
        ----------
        basic_data : Dict[str, set[str]], optional
            申請書(詳細)を除いた、処理に失敗した基本データ、
            JSON形式からの復元のため、辞書の値がリストであることを許容
        request_detail : Dict[int, set[str]], optional
            申請書(詳細)の取得に失敗した対象、
            JSON形式からの復元のためにキーが文字列であることと、辞書の値がリストであることを許容
        """
        self._basic_data: Dict[APIType, set[str]] = {}
        """申請書(詳細)を除いた、処理に失敗した基本データ"""
        self._request_detail: Dict[int, set[str]] = {}
        """申請書(詳細)の取得に失敗した対象、キーはform_id、値は取得に失敗したrequest_id"""

        if basic_data is None and request_detail is None:
            # データが指定されていない場合は初期化のみ行う
            self.clear()
            return

        # 基本データに関するデータを取得
        if basic_data is not None:
            for api_type, targets in basic_data.items():
                self._basic_data[APIType[api_type]] = set(targets)

        # 申請書(詳細)に関するデータを取得
        if request_detail is not None:
            for form_id, targets in request_detail.items():
                self._request_detail[int(form_id)] = set(targets)

    def add(self, api_type:APIType, target:str, *, form_id:Optional[int]=None) -> None:
        """処理に失敗した対象を追加する

        Parameters
        ----------
        api_type : APIType
            処理に失敗した対象のAPIの種類
        target : str
            処理に失敗した対象のID
            例) form_outline であれば form_id
        form_id : int, optional
            処理に失敗した申請書のID、api_type が REQUEST_DETAIL の場合のみ指定
        """
        if api_type == APIType.REQUEST_DETAIL:
            if form_id is None:
                raise ValueError("form_id must be specified when api_type is REQUEST_DETAIL")
            if form_id not in self._request_detail:
                self._request_detail[form_id] = set()
            self._request_detail[form_id].add(target)
        else:
            self._basic_data[api_type].add(target)

    def get(self, api_type:APIType, *, form_id:Optional[int]=None) -> set[str]:
        """処理に失敗した対象を取得する

        Parameters
        ----------
        api_type : APIType
            処理に失敗した対象のAPIの種類
        form_id : int, optional
            処理に失敗した申請書のID、api_type が REQUEST_DETAIL の場合のみ指定

        Returns
        -------
        set[str]
            処理に失敗した対象のID
        """
        if api_type == APIType.REQUEST_DETAIL:
            if form_id is None:
                raise ValueError("form_id must be specified when api_type is REQUEST_DETAIL")
            return self._request_detail.get(form_id, set())
        else:
            return self._basic_data.get(api_type, set())

    def get_request_detail(self) -> Dict[int, set[str]]:
        """処理に失敗した申請書(詳細)のform_id,request_idを取得する

        Returns
        -------
        Dict[int, set[str]]
            処理に失敗したform_idと、処理に失敗した (その申請書に対応した) request_idの辞書
        """
        return self._request_detail

    def clear(self) -> None:
        """初期化する"""
        for api_type in APIType:
            # 申請書(詳細)以外のデータは空リストで初期化
            if api_type != APIType.REQUEST_DETAIL:
                self._basic_data[api_type] = set()

        self._request_detail = {}

    def asdict(self, json_format:bool=False) -> dict:
        """辞書形式に変換する

        Returns
        -------
        dict
            変換した辞書
        json_format : bool, default False
            JSON形式に変換するかどうか (set -> list などの変換を行う)

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
        if json_format:
            return {
                "basic_data": {k.name: list(v) for k, v in self._basic_data.items()},
                "request_detail": {k: list(v) for k, v in self._request_detail.items()}
            }

        return {
            "basic_data": {k.name: v for k, v in self._basic_data.items()},
            "request_detail": self._request_detail
        }


class DBSaveFailureRecord(FailureRecord):
    """DB操作に失敗した対象を保持するクラス

    Notes
    -----
    - 以下のように辞書型との相互変換が可能

    ```python
    record = DBSaveFailureRecord()
    record.add(APIType.USER_V3, "123")
    record.add(APIType.REQUEST_DETAIL, "456", form_id=789)
    record.asdict()
    # -> {'basic_data': {"USER_V3": ['123']}, 'request_detail': {789: ['456']}}
    record2 = DBSaveFailureRecord(**record.asdict())
    record2.asdict()
    # -> {'basic_data': {"USER_V3": ['123']}, 'request_detail': {789: ['456']}}
    ```

    - `is_failed()` メソッドを使用することで、指定されたAPIでのDB操作に失敗したかどうかを判定できる

    ```python
    record = DBSaveFailureRecord()
    # USER_V3 APIでのDB操作を失敗として記録
    record.is_failed(APIType.USER_V3, True)

    # USER_V3 APIでのDB操作が失敗したかどうかを取得
    record.is_failed(APIType.USER_V3)
    # -> True
    ```
    """
    def is_failed(
            self,
            api_type:Literal[APIType.USER_V3, APIType.GROUP_V1, APIType.POSITION_V1],
            value: Optional[bool] = None
        ) -> bool:
        """指定されたAPIでのDB操作に失敗したかどうか
        `value`を指定した場合、DB操作に失敗/成功したとして記録する

        Parameters
        ----------
        api_type : APIType
            APIの種類
        value : bool, optional
            失敗した場合はTrue、成功した場合はFalse

        Returns
        -------
        bool
            指定されたAPIでのDB操作に失敗した場合はTrue
        """
        if value is not None:
            if value:
                self.add(api_type, "")
            else:
                self._basic_data[api_type] = set()
        return bool(self._basic_data[api_type])


class FetchFailureRecord(FailureRecord):
    """APIでデータ取得に失敗した対象を保持するクラス

    Notes
    -----
    - 以下のように辞書型との相互変換が可能

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

    - `is_failed()` メソッドを使用することで、指定されたAPIでのデータ取得に失敗したかどうかを判定できる

    ```python
    record = FetchFailureRecord()
    # USER_V3 APIでのデータ取得を失敗として記録
    record.is_failed(APIType.USER_V3, True)

    # USER_V3 APIでのデータ取得が失敗したかどうかを取得
    record.is_failed(APIType.USER_V3)
    # -> True
    ```
    """
    def is_failed(
            self,
            apy_type:Literal[APIType.USER_V3, APIType.GROUP_V1,
                             APIType.POSITION_V1, APIType.FORM_V1],
            value: Optional[bool] = None
        ) -> bool:
        """指定されたAPIでのデータ取得に失敗したかどうか
        valueが指定されている場合は、そのAPIでのデータ取得に失敗/成功したとして記録する

        Parameters
        ----------
        apy_type : APIType
            APIの種類
        value : bool, optional
            失敗した場合はTrue、成功した場合はFalse

        Returns
        -------
        bool
            指定されたAPIでのデータ取得に失敗した場合はTrue
        """
        if value is not None:
            if value:
                self.add(apy_type, "")
            else:
                self._basic_data[apy_type] = set()
        return bool(self._basic_data[apy_type])


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
        self.current_error: Optional[JDIErrorData] = None
        """現在のエラー情報、エラーが発生していない場合はNone"""
        self.db_save_failure_record = DBSaveFailureRecord()
        """DBへの保存に失敗した対象"""
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
        self.db_save_failure_record.clear()
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

        # 現在のエラー情報の読み込み
        if (ce := data.get("current_error", None)) is not None:
            self.current_error = error_from_json(ce["name"], ce["data"])

        # DBへの保存に失敗した対象の読み込み
        try:
            # "db_save_failure_record" が存在する場合のみ読み込む
            if "db_save_failure_record" in data:
                self.db_save_failure_record = DBSaveFailureRecord(**data["db_save_failure_record"])
        except TypeError:
            # データ型が不正な場合はデータを読み込まない
            pass

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
        current_error = None
        if self.current_error is not None:
            current_error = {
                "name": self.current_error.name,
                "data": self.current_error.asdict()
            }

        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump({
                "progress": self.progress.asdict(json_format=True),
                "current_error": current_error,
                "db_save_failure_record": self.db_save_failure_record.asdict(json_format=True),
                "fetch_failure_record": self.fetch_failure_record.asdict(json_format=True),
                "config_file_path": self.config_file_path,
                "form_api_last_access": self.form_api_last_access
            }, f)

    @property
    def has_error(self) -> bool:
        """エラーが発生しているかどうか

        Returns
        -------
        bool
            エラーが発生している場合はTrue
        """
        return self.current_error is not None
