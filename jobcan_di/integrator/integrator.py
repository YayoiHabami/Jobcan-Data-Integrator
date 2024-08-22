"""
JobcanのAPIを使用してデータを取得するクラス

Classes
-------
- `JobcanDataIntegrator`: JobcanのAPIを使用してデータを取得するクラス

Usage
-----

1a. with文を使用する場合

```python
from jobcan_di.integrator import JobcanDataIntegrator

with JobcanDataIntegrator() as di:
    di.run()
```

1b. with文を使用しない場合

```python
from jobcan_di.integrator import JobcanDataIntegrator

di = JobcanDataIntegrator()
di.run()

# 終了時にcleanup()を呼び出す
di.cleanup()
```

2. ログファイルの読み込み先を変更する場合

```python
from jobcan_di.integrator import JobcanDataIntegrator, JobcanDIConfig

# ログファイルの読み込み先を変更
# app_dir の下にある config フォルダ内の config.ini & app_status を読み込む
# 存在しない場合は自動生成
config = JobcanDIConfig(app_dir="C:/path/to/app_dir")

with JobcanDataIntegrator(config) as di:
    di.run()
```
"""
import copy
from dataclasses import dataclass, field
import datetime
import os
import sqlite3
from typing import Union, Optional, Tuple, Literal, Callable

from requests import exceptions as req_ex

from jobcan_di.database import (
    forms as f_io,
    group as g_io,
    positions as p_io,
    users as u_io,
    requests as r_io
)
from .integrator_config import JobcanDIConfig, LogLevel
from . import integrator_errors as ie
from . import integrator_warnings as iw
from .integrator_status import AppProgress
from ._json_data_io import save_response_to_json
from ._logger import Logger
from . import progress_status as ps
from .progress_status import (
    ProgressStatus,
    DetailedProgressStatus,
    InitializingStatus,
    GetFormDetailStatus,
    TerminatingStatus,
    APIType
)
from ._tf_io import JobcanTempDataIO, TempFormOutline
from .throttled_request import ThrottledRequests
from ._toast_notification import ToastProgressNotifier



@dataclass
class APIResponse:
    """
    APIのレスポンスデータ

    Attributes
    ----------
    results : list[dict]
        レスポンスの結果を結合したもの。
        - basic_data および form_outline の場合: `"results"` の内容を連結したもの
    error : ie.JDIErrorData | iw.JDIWarningData | None
        エラー/警告情報、エラー/警告が発生しなかった場合はNone
    """
    results: list[dict] = field(default_factory=list)
    """レスポンスの結果を結合したもの"""
    error: Union[ie.JDIErrorData, iw.JDIWarningData, None] = None
    """エラー/警告情報、エラー/警告が発生しなかった場合はNone"""

    @property
    def success(self) -> bool:
        """エラーが発生していないかどうか"""
        return self.error is None


UNIQUE_IDENTIFIER_KEYS = {
    APIType.USER_V3: "user_code",
    APIType.GROUP_V1: "group_code",
    APIType.POSITION_V1: "position_code",
    APIType.FORM_V1: "id",
    APIType.REQUEST_OUTLINE: "id"
}
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


#
# Data Integrator
#

class JobcanDataIntegrator:
    """
    JobcanのAPIを使用してデータを取得するクラス

    Attributes
    ----------
    app_id : str
        アプリケーションID

    Properties
    ----------
    progress : Tuple[ProgressStatus, DetailedProgressStatus]
        進捗状況を取得する（致命的なエラーが発生した場合はエラー発生時の進捗状況を返す）
    current_error : Optional[ie.JDIErrorData]
        現在のエラー情報を取得する、エラーが発生していない場合はNone
    has_error : bool
        エラーが発生しているかどうか
    is_canceled : bool
        処理がキャンセルされたかどうか
    is_completed : bool
        全ての処理が完了したかどうか、中断された場合はFalse
    """

    def __init__(self, config:Optional[JobcanDIConfig]=None):
        """Constructor

        Parameters
        ----------
        config : Optional[JobcanDIConfig], default None
            コンフィグ、読み込むconfig.iniを変更したい場合はここから指定
        """
        self.config = JobcanDIConfig(os.getcwd()) if config is None else config

        # 変数の初期化
        self.app_id = "ジョブカン API"
        self._headers = {}
        """APIリクエストのヘッダ。トークンを含み、ヘッダが空でない場合はトークンが有効であることを示す"""
        self._request = ThrottledRequests(self.config.requests_per_sec)
        self._conn = None
        self._logger = Logger(self.config.default_log_path)
        """ロガー"""
        self._notifier = ToastProgressNotifier(self.app_id,
                                               app_icon_path=self.config.app_icon_png_path)
        """進捗通知クラス"""
        self._completed = False
        """全ての処理が完了したかどうか、中断された場合もFalse"""
        self._is_canceled = False
        """致命的なエラーが発生し、以降の処理を行えなくなった場合はTrue"""
        self._tmp_io = JobcanTempDataIO(os.getcwd())
        """一時データの入出力クラス"""
        self._previous_progress = AppProgress(
            **self.config.app_status.progress.asdict()
        )
        """前回の進捗状況"""
        self._issued_warnings: list[iw.JDIWarningData] = []
        """実行中に発生した警告のログ"""

        # 初期化処理
        self._initialize()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    #
    # 初期化処理関連
    #

    def _initialize(self):
        """初期化処理"""
        # 前回の進捗状況に関わらず、初期化処理は毎回行う

        self._init_logger()
        self._init_progress_notification()
        self._init_directories()

        self._init_token()
        if self.is_canceled:
            return

        self._init_connection()
        if self.is_canceled:
            return

        self._init_tables()
        if self.is_canceled:
            return

        self._update_progress(ProgressStatus.INITIALIZING,
                              InitializingStatus.COMPLETED, 1, 1)

    def _init_logger(self):
        """ロガーの初期化 (出力先など)"""
        # 出力先の設定
        s = self._logger.init_logger(self.config.log_path, self.config.log_encoding,
                                     init_log = self.config.log_init=="ALWAYS_ON_STARTUP",
                                     logging_to_console=self.config.logging_to_console)

        # 'config.ini'のLOG_PATHが不正な場合はWarningを出力
        if not s:
            self._logger.log(ProgressStatus.INITIALIZING,
                             iw.InvalidLogFilePath(self.config.log_path).warning_message(),
                             LogLevel.WARNING)

        self._update_progress(ProgressStatus.INITIALIZING,
                              InitializingStatus.INIT_LOGGER, 1, 1)

    def _init_progress_notification(self):
        """進捗に関するトースト通知の初期化"""
        # 本アプリケーションに関するトースト通知を全て削除
        if self.config.clear_previous_notifications_on_startup:
            self._notifier.clear_notifications()

        # トースト通知の作成
        self._notifier.init_notification(title=self.app_id, body="初期化中...",
                                         suppress_popup=True)

        # 進捗状況の更新
        self._update_progress(ProgressStatus.INITIALIZING,
                              InitializingStatus.INIT_NOTIFICATION, 1, 1)

    def _init_directories(self):
        """ディレクトリの初期化"""
        # DBファイルのディレクトリが存在しない場合は作成
        if not os.path.exists(os.path.dirname(self.config.db_path)):
            os.makedirs(os.path.dirname(self.config.db_path))

        # JSON出力先ディレクトリが存在しない場合は作成
        if self.config.save_json and not os.path.exists(self.config.json_dir):
            os.makedirs(self.config.json_dir)

        # 進捗状況の更新
        self._update_progress(ProgressStatus.INITIALIZING,
                              InitializingStatus.INIT_DIRECTORIES, 1, 1)

    def _init_token(self):
        """APIトークンの初期化"""
        # 設定ファイルのトークンで初期化
        token = self.config.api_token

        if (self.config.api_token_env != "") and (self.config.api_token_env in os.environ):
            # 環境変数の指定があるケース
            # 環境変数からAPIトークンを取得して上書き
            tmp = os.getenv(self.config.api_token_env)
            if tmp:
                # 環境変数に値が設定されている場合は[API][API_TOKEN]を無視
                token = tmp

        if not token:
            # APIトークンが設定されていない場合はエラーを出力して終了
            if self.config.api_token_env == "":
                err = ie.TokenMissingEnvEmpty()
            elif self.config.api_token_env not in os.environ:
                err = ie.TokenMissingEnvNotFound(self.config.api_token_env)
            return self.cancel(err)

        # トークンの更新・有効性の確認
        if (err:=self.update_token(token)) is not None:
            # 指定されたトークンが無効な場合は終了
            return self.cancel(err)

        # 進捗状況の更新
        self._update_progress(ProgressStatus.INITIALIZING,
                              InitializingStatus.INIT_TOKEN, 1, 1)

    def _init_connection(self):
        """データベースとの接続の初期化"""
        # フォルダが存在しない場合は作成
        if not os.path.exists(os.path.dirname(self.config.db_path)):
            os.makedirs(os.path.dirname(self.config.db_path))

        # データベースとの接続
        try:
            self._conn = sqlite3.connect(self.config.db_path)
        except sqlite3.Error as e:
            return self.cancel(ie.DatabaseConnectionFailed(e))

        # 進捗状況の更新
        self._update_progress(ProgressStatus.INITIALIZING,
                              InitializingStatus.INIT_DB_CONNECTION, 1, 1)

    def _init_tables(self):
        """テーブルの初期化"""
        f_io.create_tables(self._conn)
        g_io.create_tables(self._conn)
        p_io.create_tables(self._conn)
        u_io.create_tables(self._conn)
        r_io.create_tables(self._conn)

        # 進捗状況の更新
        self._update_progress(ProgressStatus.INITIALIZING,
                              InitializingStatus.INIT_DB_TABLES, 1, 1)

    def update_token(self, token:str) -> Optional[ie.JDIErrorData]:
        """トークンの更新および有効性の確認

        Parameters
        ----------
        token : str
            新しいAPIトークン

        Returns
        -------
        Optional[ie.JDIErrorData]
            トークンが無効な場合はエラー情報、それ以外はNone
        """
        headers = self._get_headers(token)

        # トークンの有効性を確認
        response = self._request.get(self.config.base_url+'/test/', headers=headers)
        if response.status_code != 200:
            # トークンが無効
            return ie.TokenInvalid(token)

        # トークンの更新
        self._headers = headers
        return None

    def _get_headers(self, token:str) -> dict:
        """ヘッダを取得する

        Parameters
        ----------
        token : str
            APIトークン"""
        return {
            'Authorization': f'Token {token}',
            'Content-Type': 'application/json'
        }

    def _update_progress(
            self,
            status:ProgressStatus,
            sub_status:DetailedProgressStatus,
            current:int=0, total:Union[int,None]=None,
            sub_count:int=0, sub_total_count:int=0
        ) -> None:
        """進捗状況を更新する

        Parameters
        ----------
        status : ProgressStatus
            大枠の進捗状況
        sub_status : DetailedProgressStatus
            細かい進捗状況、InitializingStatusなど
        current : int
            現在の進捗
        total : Union[int,None]
            全体の進捗
            Noneの場合、valueが0なら0%、それ以外なら100%として扱われる
        sub_count : int, default 0
            第2段階進捗に可算する値、基本的には0
            ProgressStatus.FORM_OUTLINEの場合に使用
        sub_total_count : int, default 0
            第2段階進捗の全体数に可算する値、基本的には0
            ProgressStatus.FORM_OUTLINEの場合に使用

        Notes
        -----
        - 本メソッドでは基本的には以下のようなルールで本メソッドを呼び出すことを想定しています。
          - 通常の進捗更新: `ProgressStatus` と `DetailedProgressStatus` を指定
            - 進捗が生じた直後に本メソッドを呼び出す
        """
        # ログメッセージを取得
        level = LogLevel.INFO
        message = ps.get_progress_status_msg(status, sub_status, sub_count, sub_total_count)

        # ログ出力
        self._logger.log(status, message, level)

        # トースト通知
        if self.config.notify_log_level <= level.value:
            self._notifier.notify(title=self.app_id, body=message, level=level)

        # 通知を更新
        self._notifier.update(status, sub_status, current, total, sub_count, sub_total_count)

        # app_status側の進捗状況を更新・保存
        self.config.app_status.progress.set(status, sub_status)

        self.save_status()

    def _update_issue(self, issue:Union[ie.JDIErrorData, iw.JDIWarningData]):
        """エラー/警告情報を更新する

        Parameters
        ----------
        issue : Union[ie.JDIErrorData, iw.JDIWarningData]
            エラー/警告情報

        Notes
        -----
        - エラー/警告情報を更新し、ログ・通知を更新する
        - 警告: `JDIWarningData` を指定
            - 警告の原因のエラーが発生した直後に本メソッドを呼び出す
        - エラー: `JDIErrorData` を指定
            - 続行不可能なエラーが生じた場合に、`.cancel`に`JDIErrorData`を渡し、間接的に呼び出す
            - 基本的に続行不可能なエラーが生じた場合は、終了処理が必要なため
        """
        if isinstance(issue, ie.JDIErrorData):
            level = LogLevel.ERROR
            message = issue.error_message()
            # エラーの場合は現在のエラー情報を更新
            self.config.app_status.current_error = issue
        else:
            level = LogLevel.WARNING
            message = issue.warning_message()
            # 警告の場合はログに記録
            self._issued_warnings.append(issue)

        # ログ出力
        status = self.config.app_status.progress.get()[0]
        self._logger.log(status, message, level)

        # トースト通知
        if self.config.notify_log_level <= level.value:
            self._notifier.notify(title=self.app_id, body=message, level=level)

        # 通知を更新
        if level == LogLevel.ERROR and self.config.clear_progress_on_error:
            self._notifier.update(status, issue, 0, 1)

        self.save_status()

    def save_status(self):
        """アプリケーションの状態を保存する"""
        self.config.app_status.save()

    def _is_future_progress(self, api_type:APIType) -> bool:
        """指定されたAPIでの処理が、現在進行中または次以降に実施するものであるか。
        `.is_canceled == True`の場合は常に`False`を返す。

        Parameters
        ----------
       api_type : APIType
            APIの種類

        Examples
        --------
        `.is_cancel`が`False`かつ前回の進捗状況が`GetBasicDataStatus.GET_POSITION`の場合:
        - `APIType.USER_V3` ⇒ `False`
        - `APIType.POSITION` ⇒ `True`
        - `APIType.REQUEST_DETAIL` ⇒ `True`

        `.is_cancel`が`True`、または現在の進捗状況が`ProgressStatus.FAILED`の場合、常に`False`を返す。

        また、一応、前回の進捗状況がエラーの場合は`True`を返す (前回エラーの場合は最初から実行する)
        ようにしています。
        """
        if self.is_canceled or self.config.app_status.has_error:
            # キャンセルされた場合、または現在エラー発生中であればFalse
            return False

        # 前回の進捗状況がapi_typeよりも未来のものの場合はFalse
        return self._previous_progress.is_future_process(api_type)

    #
    # プロパティ
    #

    @property
    def progress(self) -> Tuple[ProgressStatus, DetailedProgressStatus]:
        """進捗状況を取得する

        Returns
        -------
        Tuple[ProgressStatus, DetailedProgressStatus]
            進捗状況
        """
        return self.config.app_status.progress.get()

    @property
    def current_error(self) -> Optional[ie.JDIErrorData]:
        """現在のエラー情報を取得する

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラー情報、エラーが発生していない場合はNone
        """
        return self.config.app_status.current_error

    @property
    def has_error(self) -> bool:
        """エラーが発生しているかどうか"""
        return self.config.app_status.has_error

    @property
    def is_canceled(self) -> bool:
        """処理がキャンセルされたかどうか"""
        return self._is_canceled

    @property
    def is_completed(self) -> bool:
        """全ての処理が完了したかどうか、中断された場合はFalse"""
        return self._completed

    @property
    def issued_warnings(self) -> list[iw.JDIWarningData]:
        """発生した警告のログ"""
        return self._issued_warnings

    #
    # メイン処理
    #

    def cancel(self, error:ie.JDIErrorData):
        """処理をキャンセルする（再実行可能）

        Parameters
        ----------
        error : ie.JDIErrorData
            キャンセルの理由となるエラー情報

        Notes
        -----
        - `._update_issue()`を呼び出す
        """
        # TODO: 前回 (_previous_progress) と今回 (app_status) の進捗状況の統合
        # 統合したものをapp_statusのprogressとして更新・保存する

        self._is_canceled = True
        self._completed = False

        self._update_issue(error)

    def _run(self):
        """メイン処理"""
        # 基本データの取得
        for api_type, update_func in [(APIType.USER_V3, u_io.update),
                                      (APIType.GROUP_V1, g_io.update),
                                      (APIType.POSITION_V1, p_io.update),
                                      (APIType.FORM_V1, f_io.update)]:
            self._update_basic_data(api_type, update_func)

        # 申請書データ (概要) の取得
        self._update_form_outline()

        # 申請書データ (詳細) の取得
        self._update_form_detail()

        # 全処理が完了
        if not self.is_canceled:
            self._completed = True
            self._update_progress(ProgressStatus.TERMINATING,
                                  TerminatingStatus.COMPLETED, 1, 1)

    def run(self):
        """メイン処理を実行する

        Notes
        -----
        - `CATCH_ERRORS_ON_RUN`が`True`の場合、エラーが発生してもアプリケーションが終了しない"""
        if not self.config.catch_errors_on_run:
            # デバッグ用: 想定外のエラー(UNEXPECTED_ERROR)をキャッチしない
            return self._run()

        # 本番用: エラーをキャッチしてアプリケーションの終了を防ぐ
        try:
            self._run()
        except Exception as e:
            self.cancel(ie.UnexpectedError(e))
            return

    def restart(self):
        """処理を再開する"""
        # キャンセルフラグをリセット
        # エラーが発生している場合 (ProgressStatus.FAILED) は

        # previous_progressをリセット

    def cleanup(self):
        """終了処理"""
        # データベースとの接続を閉じる
        if self._conn:
            self._conn.close()

        # 全処理が正常に完了した場合、一時ファイルを削除
        if self._completed:
            self._tmp_io.cleanup()

        self.save_status()

    #
    # 内部処理 (データ取得・更新等)
    #

    def _fetch_data(self, url:str, api_type:APIType) -> APIResponse:
        """APIを使用してデータを取得する

        Parameters
        ----------
        url : str
            APIのURL
        api_type : APIType
            取得するデータの種類

        Returns
        -------
        APIResponse
            取得したデータ、APIの種類などに関わらず.json()の内容を格納する
        """
        try:
            res = self._request.get(url, headers=self._headers)

            if res.status_code != 200:
                # 正常なレスポンスが返ってこなかった場合
                warning = iw.get_api_error(api_type, res.status_code, res, url)
                self._update_issue(warning)
                return APIResponse(error=warning)

            # 正常なレスポンスが返ってきた場合
            return APIResponse(results=[res.json()])
        except req_ex.ConnectionError as e:
            # 通信エラー
            return APIResponse(error=ie.RequestConnectionError(e))
        except req_ex.ReadTimeout as e:
            # タイムアウト
            return APIResponse(error=ie.RequestReadTimeout(e))

    def _fetch_basic_data(
                self,
                api_type: APIType,
                query: str = "",
                skip_on_error: bool = False,
                sub_count: int = 0,
                sub_total_count: int = 0) -> APIResponse:
        """
        APIを使用してデータを取得する

        Parameters
        ----------
        api_type : APIType
            取得するデータの種類
        query : str, default ""
            クエリ文字列
            例) "?form_id=1234" (申請書データ (概要))
        skip_on_error : bool, default False
            エラーが発生した場合にスキップするかどうか、Falseの場合は処理を終了する
        sub_count : int, default 0
            第2段階進捗に可算する値 -> _update_progress() に渡す
        sub_total_count : int, default 0
            第2段階進捗の全体数に可算する値 -> _update_progress() に渡す

        Returns
        -------
        APIResponse
            取得したデータ
            エラーが発生した場合、または`skip_on_error`が`True`でエラーが発生した場合は
            その時点でのデータを返す

        Notes
        -----
        - この関数では申請書データ (詳細) は取得できません
        """
        assert api_type != APIType.REQUEST_DETAIL, "この関数では申請書データ (詳細) は取得できません"

        url = self.config.api_base_url[api_type] + query
        page_num = 1
        self._update_progress(ps.get_progress_status(api_type),
                              ps.get_detailed_progress_status(api_type),
                              0, None, sub_count, sub_total_count)
        result = APIResponse()
        while True:
            res = self._fetch_data(url, api_type)
            res_j = res.results[0]
            result.results.extend(res_j.get("results", []))

            if isinstance(res.error, iw.JDIWarningData):
                # 正常なレスポンスが返ってこなかった場合
                result.error = res.error
                if skip_on_error:
                    # エラーが発生した場合にスキップする場合、現時点で取得したデータを返す
                    return result
                continue
            elif isinstance(res.error, ie.JDIErrorData):
                # 致命的なエラーが発生した場合
                result.error = res.error
                return result

            if self.config.save_json:
                save_response_to_json(res_j, api_type, page_num,
                                      self.config.json_indent, self.config.json_dir,
                                      self.config.json_encoding)

            self._update_progress(ps.get_progress_status(api_type),
                                  ps.get_detailed_progress_status(api_type),
                                  len(result.results), res_j["count"],
                                  sub_count, sub_total_count)

            if not res_j['next']:
                # 次のページが存在しない場合にループを抜ける
                break
            url = res_j['next']
            page_num += 1

        return result

    def _fetch_form_outline_data(
                self,
                form_id: int,
                applied_after: Optional[str] = None,
                skip_on_error: bool = False,
                include_cancel: bool = True,
                sub_count: int = 0,
                sub_total_count: int = 0
        ) -> Tuple[TempFormOutline, Union[ie.JDIErrorData, iw.JDIWarningData, None]]:
        """
        APIを使用して申請書(概要)データを取得する

        Parameters
        ----------
        api_type : APIType
            取得するデータの種類
        form_id : int
            申請書データのID
        applied_after : Optional[str], default None
            申請日時のフィルタ、指定した日時以降のデータのみ取得する。
            形式は "YYYY/MM/DD HH:MM:SS" (JST) で指定する。
            例) "2021/01/01 00:00:00"
        skip_on_error : bool, default False
            エラーが発生した場合にスキップするかどうか、Falseの場合は処理を終了する
        include_cancel : bool, default True
            取得するデータにキャンセルされたデータを含めるかどうか、APIのデフォルトはFalse
            これをFalseにした場合、独自の申請書ID (request_id) を採用している環境での通し番号の取得はできなくなる。
        sub_count : int, default 0
            第2段階進捗に可算する値 -> _update_progress() に渡す
        sub_total_count : int, default 0
            第2段階進捗の全体数に可算する値 -> _update_progress() に渡す

        Returns
        -------
        TempFormOutline
            取得したデータ、APIのレスポンスに失敗があったかを示す `.success` と、
            取得した申請書データのIDのリスト `.ids` にのみ値が格納される
        Union[ie.JDIErrorData, iw.JDIWarningData, None]
            エラー/警告情報、エラー/警告が発生しなかった場合はNone
        """
        # クエリの作成
        query = f"?form_id={form_id}"
        if applied_after:
            query += f"&applied_after={applied_after}"
        if include_cancel:
            query += "&include_canceled=true"

        f_outline = self._fetch_basic_data(
            APIType.REQUEST_OUTLINE,
            query=query,
            skip_on_error=skip_on_error,
            sub_count=sub_count,
            sub_total_count=sub_total_count
        )

        return TempFormOutline(
            success = f_outline.success,
            ids = [res["id"] for res in f_outline.results]
        ), f_outline.error

    def _fetch_form_detail_data(self, request_id: str) -> APIResponse:
        """APIを使用して申請書(詳細)データを取得する

        Parameters
        ----------
        request_id : str
            申請書データのID

        Returns
        -------
        APIResponse
            取得したデータ
        """
        return self._fetch_data(
            url = self.config.api_base_url[APIType.REQUEST_DETAIL] + f"{request_id}/",
            api_type = APIType.REQUEST_DETAIL
        )

    def _update_data(
            self, update_func: Callable[[sqlite3.Connection, dict], None],
            data:dict, api_type: APIType
        ) -> Union[ie.JDIErrorData, iw.JDIWarningData, None]:
        """DBへデータの更新を試みる。
        一部のエラーが発生した場合、それをキャッチし`JDIErrorData`か`JDIWarningData`を返す

        Parameters
        ----------
        update_func : function
            更新処理を行う関数、引数は (conn, data)
        data : dict
            更新するデータ、APIのレスポンスの'results'内のデータなど
        api_type : APIType
            更新するデータの種類

        Returns
        -------
        Union[ie.JDIErrorData, iw.JDIWarningData, None]
            エラー/警告が発生した場合はエラー/警告情報、それ以外はNone

        Notes
        -----
        - キャッチする例外は以下の通り
          - sqlite3.Error -> warning
        """
        try:
            update_func(self._conn, data)
        except sqlite3.Error as e:
            warning = iw.DBUpdateFailed(api_type, e)
            self._update_issue(warning)
            return warning

        # 更新が正常に終了
        return None

    def _update_basic_data(
            self,
            api_type: Literal[APIType.USER_V3, APIType.GROUP_V1, APIType.POSITION_V1,
                              APIType.FORM_V1],
            update_func: Callable[[sqlite3.Connection, dict], None]
    ):
        """基本データの取得＆更新

        Parameters
        ----------
        api_type : APIType
            取得するデータの種類
        update_func : function
            更新処理を行う関数、引数は (conn, data)
            u_io.update, g_io.update, p_io.update, f_io.update のいずれか
        """
        if not self._is_future_progress(api_type):
            # 前回処理済みorキャンセルorエラーの場合はスキップ
            return

        # データ取得
        data = self._fetch_basic_data(api_type)
        if isinstance(data.error, ie.JDIErrorData):
            # エラーが発生した場合は処理を終了
            return self.cancel(data.error)
        elif isinstance(data.error, iw.JDIWarningData):
            # 警告が発生した場合はログに記録 (処理は続行)
            self.config.app_status.fetch_failure_record.is_failed(api_type, True)

        # データをデータベースに保存
        for res in data.results:
            err = self._update_data(update_func, res, api_type)
            if isinstance(err, ie.JDIErrorData):
                # エラーが発生した場合は処理を終了
                return self.cancel(err)
            elif isinstance(err, iw.JDIWarningData):
                # 更新に失敗した場合、app_statusに保存失敗として記録 (処理は続行)
                self.config.app_status.db_save_failure_record.add(
                    api_type, get_unique_identifier(res, api_type)
                )

    def _update_form_outline(self):
        """申請書データ (概要) の取得＆更新

        Notes
        -----
        - 申請書データ (概要)
        """
        if not self._is_future_progress(APIType.REQUEST_OUTLINE):
            # 前回処理済みorキャンセルorエラーの場合はスキップ
            return

        # 申請書データ (概要) 取得
        failed_ids = self.config.app_status.fetch_failure_record.get(APIType.REQUEST_OUTLINE)
        ids = f_io.retrieve_form_ids(self._conn)
        tmp_data = self._tmp_io.load_form_outline()
        self._update_progress(ProgressStatus.FORM_OUTLINE,
                                ps.GetFormOutlineStatus.GET_OUTLINE, 0, None)

        # 取得開始日時を設定
        for i, form_id in enumerate(ids):
            if (form_id not in failed_ids
                and not self._previous_progress.is_future_process(APIType.REQUEST_OUTLINE,
                                                                    specific = form_id)):
                # 前回の取得に失敗しておらず、前回取得済みの場合はスキップ
                # NOTE: .is_future_processにより、form_idとrequest_id等とが偶発的に一致した場合の判定を除外
                self.config.app_status.progress.add_specifics(form_id)
                self._update_progress(ProgressStatus.FORM_OUTLINE,
                                        ps.GetFormOutlineStatus.GET_OUTLINE,
                                        1, 1, i+1, len(ids))
                continue

            # 取得開始時刻を記録し、データ取得開始
            last_access = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            # 前回の取得日時が存在する場合はそれを適用 (applied_after)
            f_outline, err = self._fetch_form_outline_data(
                form_id = form_id,
                applied_after = self.config.app_status.form_api_last_access.get(form_id, None),
                sub_count = i+1,
                sub_total_count = len(ids)
            )
            if isinstance(err, ie.JDIErrorData):
                # エラーが発生した場合は処理を終了
                return self.cancel(err)
            elif isinstance(err, iw.JDIWarningData):
                # 更新に失敗した場合（取得できなかったrequest_idがある場合）
                # app_statusに取得失敗として記録 (処理は続行)
                self.config.app_status.fetch_failure_record.add(APIType.REQUEST_OUTLINE,
                                                                target = form_id)
            succeeded &= f_outline.success

            # 申請書データ (概要) を一時ファイルに保存
            # 成否にかかわらず、取得したデータは一時ファイルに保存
            if form_id not in tmp_data:
                tmp_data[form_id] = f_outline
            else:
                tmp_data[form_id].add_ids(f_outline.ids)

            if f_outline.success:
                # 今回の更新に成功した場合、成否フラグと最終アクセス日時を更新
                tmp_data[form_id].success = True
                tmp_data[form_id].last_access = last_access
            # NOTE: 新規記録対象が10000件程度でも保存にかかる時間は0.1s程度のため、毎回直接保存する
            self._tmp_io.save_form_outline(tmp_data)

            # 進捗状況を更新 (一時ファイルへの保存が完了した時点でform_idをspecificsに追加)
            self.config.app_status.progress.add_specifics(form_id)

    def _update_form_detail(self) -> bool:
        """申請書データ (詳細) の取得＆更新"""
        if not self._is_future_progress(APIType.REQUEST_DETAIL):
            # 申請書データ (詳細) の取得をスキップ
            return True

        # 一時ファイルの読み込み
        self._update_progress(ProgressStatus.FORM_DETAIL,
                              GetFormDetailStatus.SEEK_TARGET, 0, None)
        tmp_data = self._tmp_io.load_form_outline()

        for i, item in enumerate(tmp_data.items()):
            form_id, data = item
            # 取得対象のrequest_idを取得 (データはtmp_dataの増減により変動するため、コピーを作成)
            target_ids = copy.copy(data.ids)
            # 更新されうるデータのIDを取得 (i.e. "in_progress", "returned"; 今後の拡張に備えて以下のように記述)
            target_ids.update(r_io.retrieve_ids(self._conn.cursor(), form_id,
                                                ant_status = ["completed", "rejected",
                                                              "canceled",
                                                              "canceled_after_completion"]))
            # 前回の取得に失敗したデータを取得対象に追加
            failed_ids = self.config.app_status.fetch_failure_record.get(APIType.REQUEST_DETAIL,
                                                                         form_id = form_id)
            target_ids.update(failed_ids)

            for j, request_id in enumerate(target_ids):
                if (request_id not in failed_ids
                    and not self._previous_progress.is_future_process(APIType.REQUEST_DETAIL,
                                                                      specific = request_id)):
                    # 前回の取得に失敗しておらず、前回取得済みの場合はスキップ
                    # NOTE: .is_future_processにより、form_idとrequest_id等とが偶発的に一致した場合の判定を除外
                    self.config.app_status.progress.add_specifics(request_id)
                    self._update_progress(ProgressStatus.FORM_DETAIL,
                                          ps.GetFormDetailStatus.GET_DETAIL,
                                          1, 1, i+1, len(tmp_data)-1)
                    continue

                # 申請書データ (詳細) 取得
                res = self._fetch_form_detail_data(request_id)
                if isinstance(res.error, ie.JDIErrorData):
                    # エラーが発生した場合は処理を終了
                    return self.cancel(res.error)
                elif isinstance(res.error, iw.JDIWarningData):
                    # 正常なレスポンスが返ってこなかった場合app_statusに取得失敗として記録
                    self.config.app_status.fetch_failure_record.add(APIType.REQUEST_DETAIL,
                                                                    target = request_id,
                                                                    form_id = form_id)
                    continue

                # 申請書データ (詳細) をデータベースに保存
                err = self._update_data(r_io.update, res.results[0], APIType.REQUEST_DETAIL)
                if isinstance(err, ie.JDIErrorData):
                    # エラーが発生した場合は処理を終了
                    return self.cancel(err)
                elif isinstance(err, iw.JDIWarningData):
                    # 保存に失敗した場合app_statusに保存失敗として記録 (処理は続行)
                    self.config.app_status.db_save_failure_record.add(APIType.REQUEST_DETAIL,
                                                                      request_id, form_id=form_id)

                # 進捗を更新
                self._update_progress(ProgressStatus.FORM_DETAIL,
                                      ps.get_detailed_progress_status(APIType.REQUEST_DETAIL),
                                      j+1, len(target_ids),
                                      i+1, len(tmp_data)-1)

                # 一時ファイルから取得に成功したrequest_idを削除
                tmp_data[form_id].remove_id(request_id)
                self._tmp_io.save_form_outline(tmp_data)

                # app_statusに取得成功として記録
                self.config.app_status.progress.add_specifics(request_id)

            # 各form_idについて申請書(詳細)の取得が完了した場合、app_statusの最終アクセス日時を更新
            self.config.app_status.form_api_last_access[form_id] = data.last_access

        return True
