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
import os
import sqlite3
import traceback
from typing import Union, Optional, Tuple, Literal, Callable

from jobcan_di.gateway import JobcanApiClient, JobcanApiGateway, FormOutline
from jobcan_di.status import AppProgress
from jobcan_di.status import errors as ie
from jobcan_di.status import progress as ps
from jobcan_di.status.progress import (
    ProgressStatus,
    DetailedProgressStatus,
    InitializingStatus,
    TerminatingStatus,
    APIType
)
from jobcan_di.status import warnings as iw
from .integrator_config import JobcanDIConfig, LogLevel
from ._logger import Logger
from ._tf_io import JobcanTempDataIO
from ._toast_notification import ToastProgressNotifier



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
        if self.config.save_json:
            client = JobcanApiClient(self.config.requests_per_sec,
                                     base_url=self.config.base_url,
                                     output_dir=self.config.json_dir,
                                     output_as_json=False)  # TODO: コンフィグでDB保存を選択可能にする
        else:
            client = None
        self._gateway = JobcanApiGateway(interval_seconds=self.config.requests_per_sec,
                                         client=client)
        """ジョブカンAPIとの通信・DBへのデータ保存を行うクラス"""
        self._logger = Logger(self.config.default_log_path)
        """ロガー"""
        self._notifier = ToastProgressNotifier(self.app_id,
                                               app_icon_path=self.config.app_icon_png_path)
        """進捗通知クラス"""
        self._completed = False
        """全ての処理が完了したかどうか、中断された場合もFalse"""
        self._is_canceled = False
        """致命的なエラーが発生し、以降の処理を行えなくなった場合はTrue"""
        self._is_initialized = False
        """初期化処理が完了したかどうか"""
        self._tmp_io = JobcanTempDataIO(os.getcwd())
        """一時データの入出力クラス"""
        self._previous_progress = AppProgress(
            **self.config.app_status.progress.asdict()
        )
        """前回の進捗状況"""
        self._issued_warnings: list[iw.JDIWarningData] = []
        """実行中に発生した警告のログ"""

        # 初期化処理
        if (err:=self._initialize()):
            self.cancel(err)

    def __enter__(self) -> "JobcanDataIntegrator":
        return self

    def __exit__(self, exc_type, exc_value, traceback_) -> None:
        self.cleanup()

    #
    # 初期化処理関連
    #

    def _initialize_inner(self) -> Optional[ie.JDIErrorData]:
        """初期化処理の具体的な処理、UnexpectedErrorをキャッチしない

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラー情報、エラーが発生していない場合はNone
        """
        # 前回の進捗状況に関わらず、初期化処理は毎回行う

        self._init_logger()
        self._init_progress_notification()
        self._init_directories()

        if (err:=self._init_token()):
            return err

        if (err:=self._init_connection()):
            return err

        if (err:=self._init_tables()):
            return err

        self._update_progress(ProgressStatus.INITIALIZING,
                              InitializingStatus.COMPLETED, 1, 1)
        self._is_initialized = True

    def _initialize(self) -> Optional[ie.JDIErrorData]:
        """初期化処理

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラー情報、エラーが発生していない場合はNone
        """
        if not self.config.catch_errors_on_run:
            # デバッグ用: 想定外のエラー(UNEXPECTED_ERROR)をキャッチしない
            return self._initialize_inner()

        try:
            self._initialize_inner()
        except Exception as e:
            return ie.UnexpectedError(e)

    def _init_logger(self) -> None:
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

    def _init_progress_notification(self) -> None:
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

    def _init_directories(self) -> None:
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

    def _init_token(self) -> Optional[ie.JDIErrorData]:
        """APIトークンの初期化

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラー情報、エラーが発生していない場合はNone
        """
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
            else:
                err = ie.TokenNotFoundError()
            return err

        # トークンの更新・有効性の確認
        if (err:=self._gateway.update_token(token)) is not None:
            # 指定されたトークンが無効な場合は終了
            return err

        # 進捗状況の更新
        self._update_progress(ProgressStatus.INITIALIZING,
                              InitializingStatus.INIT_TOKEN, 1, 1)

    def _init_connection(self) -> Optional[ie.JDIErrorData]:
        """データベースとの接続の初期化"""
        # フォルダが存在しない場合は作成
        if not os.path.exists(os.path.dirname(self.config.db_path)):
            os.makedirs(os.path.dirname(self.config.db_path))

        # データベースとの接続
        if (err := self._gateway.init_connection(self.config.db_path)):
            return err

        # 進捗状況の更新
        self._update_progress(ProgressStatus.INITIALIZING,
                              InitializingStatus.INIT_DB_CONNECTION, 1, 1)

    def _init_tables(self) -> Optional[ie.JDIErrorData]:
        """テーブルの初期化"""
        if (err := self._gateway.init_tables()):
            return err

        # 進捗状況の更新
        self._update_progress(ProgressStatus.INITIALIZING,
                              InitializingStatus.INIT_DB_TABLES, 1, 1)

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
        if isinstance(issue, ie.JDIErrorData) and self.config.clear_progress_on_error:
            self._notifier.update(status, issue, 0, 1)

        self.save_status()

    def save_status(self) -> None:
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
    def progress(self) -> Tuple[ProgressStatus, Optional[DetailedProgressStatus]]:
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
    def is_initialized(self) -> bool:
        """初期化処理が完了したかどうか"""
        return self._is_initialized

    @property
    def issued_warnings(self) -> list[iw.JDIWarningData]:
        """発生した警告のログ"""
        return self._issued_warnings

    #
    # メイン処理
    #

    def cancel(self, error:ie.JDIErrorData) -> Optional[ie.JDIErrorData]:
        """処理をキャンセルする（再実行可能）

        Parameters
        ----------
        error : ie.JDIErrorData
            キャンセルの理由となるエラー情報

        Returns
        -------
        ie.JDIErrorData
            エラー情報、エラー状態にならない場合はNone

        Notes
        -----
        - `._update_issue()`を呼び出す
        - 連続して何度呼び出しても、一回目の結果と同じ状態となるようになる
        """
        # TODO: 前回 (_previous_status) と今回 (app_status) の進捗状況の統合
        # 統合したものをapp_statusのprogressとして更新・保存する
        # 現在は_previous_progressなので不要
        self.save_status()

        self._is_canceled = True
        self._completed = False

        self._update_issue(error)

        return self.current_error

    def _run(self) -> Optional[ie.JDIErrorData]:
        """メイン処理

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラー情報、エラーが発生していない場合はNone
        """
        if not self.is_initialized:
            # 初期化が完了していない場合はエラー
            self.cancel(ie.NotInitializedError())

        # 基本データの取得
        for api_type in [APIType.USER_V3, APIType.GROUP_V1, APIType.POSITION_V1, APIType.FORM_V1]:
            if (err:=self._update_basic_data(api_type)):
                return self.cancel(err)

        # 申請書データ (概要) の取得
        if (err:=self._update_form_outline()):
            return self.cancel(err)

        # 申請書データ (詳細) の取得
        if (err:=self._update_form_detail()):
            return self.cancel(err)

        # 全処理が完了
        if not self.is_canceled:
            self._completed = True
            self._update_progress(ProgressStatus.TERMINATING,
                                  TerminatingStatus.COMPLETED, 1, 1)

    def run(self) -> Optional[ie.JDIErrorData]:
        """メイン処理を実行する

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラー情報、エラーが発生していない場合はNone

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
            tr = traceback.format_exc()
            if self.config.logging_to_console:
                print(tr)
            return self.cancel(ie.UnexpectedError(e))

    def restart(self) -> Optional[ie.JDIErrorData]:
        """処理を再開する

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラー情報、エラーが発生していない場合はNone

        Notes
        -----
        - 一度正常終了した場合でも、再開することができる
        """
        # フラグをリセット
        self._completed = False
        self._is_canceled = False

        # エラーが発生している場合 (ProgressStatus.FAILED) は消去
        self.config.app_status.remove_error()

        # previous_progressをリセット
        self._previous_progress = AppProgress(
            **self.config.app_status.progress.asdict()
        )
        # 前回最後まで実行されていた場合は進捗状況をリセット（正常終了後も再開可能とするため）
        if self.config.app_status.progress.is_completed():
            self.config.app_status.progress.reset()
        # 前回実行中に発生した警告をリセット
        self._issued_warnings = []

        # 前回終了時に初期化が終了していない場合は再度初期化処理を行う
        if not self.is_initialized:
            if (err:=self._initialize()):
                # 初期化に失敗
                return self.cancel(err)

        return self.run()

    def cleanup(self) -> None:
        """終了処理"""
        # データベースとの接続を閉じる
        self._gateway.cleanup()

        # 全処理が正常に完了した場合、一時ファイルを削除
        if self._completed:
            self._tmp_io.cleanup()

        self.save_status()

    #
    # 内部処理 (データ取得・更新等)
    #

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
            api_type: Literal[APIType.USER_V3, APIType.GROUP_V1,
                              APIType.POSITION_V1, APIType.FORM_V1]
    ) -> Optional[ie.JDIErrorData]:
        """基本データの取得＆更新

        Parameters
        ----------
        api_type : APIType
            取得するデータの種類

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラーが発生した場合はエラー情報、それ以外はNone
        """
        if not self._is_future_progress(api_type):
            # 前回処理済みorキャンセルorエラーの場合はスキップ
            return

        err, r_suc, d_uid = self._gateway.update_basic_data(
            api_type, issue_callback=self._update_issue,
            progress_callback=lambda a, c, t: self._update_progress(
                ps.get_progress_status(a), ps.get_detailed_progress_status(a), c, t, 0, 0
            )
        )
        # データ取得に成功したか否かをapp_statusに記録
        self.config.app_status.fetch_failure_record.is_failed(api_type, not r_suc)
        # データ更新に失敗したデータの識別子をapp_statusに記録
        if d_uid:
            self.config.app_status.db_save_failure_record.add(api_type, set(d_uid))
        return err

    def _update_form_outline(self) -> Optional[ie.JDIErrorData]:
        """申請書データ (概要) の取得＆更新

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラーが発生した場合はエラー情報、それ以外はNone

        Notes
        -----
        - 申請書データ (概要)
        """
        if not self._is_future_progress(APIType.REQUEST_OUTLINE):
            # 前回処理済みorキャンセルorエラーの場合はスキップ
            return

        # 除外対象のrequest_idを取得
        # 前回の進捗状況が申請書データ (概要) の取得である場合、取得に成功したデータを除外
        # ただし除外対象から前回取得に失敗したデータは除外 (再取得を試みる)
        ignore = set()
        if (self._previous_progress.get()[1]
                == ps.get_detailed_progress_status(APIType.REQUEST_OUTLINE)):
            ignore = {str(i) for i in self._previous_progress.specifics}
        ignore -= self.config.app_status.fetch_failure_record.get(APIType.REQUEST_OUTLINE)

        # 申請書データ (概要) 取得
        forms: dict[int, FormOutline] = dict()
        err = self._gateway.get_form_outline(
            applied_after=self.config.app_status.form_api_last_access,
            ignore=ignore, issue_callback=self._update_issue,
            progress_callback=lambda a, c, t, sc, st: self._update_progress(
                ps.get_progress_status(a), ps.get_detailed_progress_status(a), c, t, sc, st
            ),
            id_progress_callback=lambda s, fid, la, fs=forms: self._fid_progress_callback(
                s, fid, la, fs
            )
        )

        return err

    def _fid_progress_callback(self,
                              stat:Literal["fetch-failure", "success"],
                              form_id:int,
                              f_outline:Optional[FormOutline]=None,
                              last_access:Optional[str]=None,
                              forms:Optional[dict[int, FormOutline]]=None) -> None:
        """申請書データ (概要) 取得の進捗状況を更新する

        Parameters
        ----------
        stat : Literal["fetch-failure", "success"]
            進捗状況
        form_id : int
            申請書ID
        f_outline : Optional[FormOutline]
            申請書データ (概要)
        last_access : Optional[str]
            最終アクセス日時
        forms : Optional[dict[int, FormOutline]]
            申請書データ (概要)、取得したデータを一時保存する場合に使用
        """
        if stat == "fetch-failure":
            # APIからのデータ取得に失敗した場合はapp_statusへの記録のみ行う
            self.config.app_status.fetch_failure_record.add(
                APIType.REQUEST_OUTLINE, target=str(form_id)
            )
            return
        elif stat == "success":
            self.config.app_status.progress.add_specifics(form_id)

        if forms is None or f_outline is None or last_access is None:
            # forms, f_outline, last_accessが指定されていない (->"fetch-failure") 場合は
            # 以下の処理を行わない
            return

        # 取得したデータを記録
        if form_id not in forms:
            forms[form_id] = f_outline
        else:
            forms[form_id].add_ids(f_outline.ids)
        if f_outline.success:
            # 取得に成功した場合、最終アクセス日時を更新
            forms[form_id].last_access = last_access

        # 一時ファイルに保存
        self._tmp_io.save_form_outline(forms)

    def _update_form_detail(self) -> Optional[ie.JDIErrorData]:
        """申請書データ (詳細) の取得＆更新"""
        if not self._is_future_progress(APIType.REQUEST_DETAIL):
            # 申請書データ (詳細) の取得をスキップ
            return

        forms = self._tmp_io.load_form_outline()

        ignore = set()
        if (self._previous_progress.get()[1]
                == ps.get_detailed_progress_status(APIType.REQUEST_DETAIL)):
            ignore = {str(i) for i in self._previous_progress.specifics}
        print(f"{ignore=}")
        # TODO: ignoreから一部除外 (前回取得に失敗したデータは再取得を試みる)

        # 申請書データ (詳細) 取得
        err = self._gateway.update_form_detail(
            forms, ignore=ignore, issue_callback=self._update_issue,
            progress_callback=lambda a, c, t, sc, st: self._update_progress(
                ps.get_progress_status(a), ps.get_detailed_progress_status(a), c, t, sc, st
            ),
            id_progress_callback=lambda s, fid, rid, fs=forms: self._rid_progress_callback(
                s, fid, rid, fs
            )
        )

        return err

    def _rid_progress_callback(self,
                               stat:Literal["fetch-failure", "save-failure",
                                                "success-req", "success-form"],
                               form_id:int,
                               request_id:Optional[str]=None,
                               forms:Optional[dict[int, FormOutline]]=None) -> None:
        """申請書データ (詳細) 取得の進捗状況を更新する

        Parameters
        ----------
        stat : Literal["fetch-failure", "save-failure", "success-req", "success-form"]
            進捗状況
        form_id : int
            申請書ID
        request_id : Optional[str]
            申請ID
        forms : Optional[dict[int, FormOutline]]
            申請書データ (概要)、取得したデータを一時保存する場合に使用
        """
        if forms is None:
            forms = dict()

        if request_id is None:
            if stat == "success-form" and form_id in forms:
                self.config.app_status.form_api_last_access[form_id] = forms[form_id].last_access
            return

        if stat == "fetch-failure":
            self.config.app_status.fetch_failure_record.add(
                APIType.REQUEST_DETAIL, form_id=form_id, target={request_id})
        elif stat == "save-failure":
            self.config.app_status.db_save_failure_record.add(
                APIType.REQUEST_DETAIL, form_id=form_id, target={request_id})
        elif stat == "success-req":
            self.config.app_status.progress.add_specifics(request_id)
            # 一時ファイルを更新
            forms[form_id].remove_id(request_id)
            self._tmp_io.save_form_outline(forms)
