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
import datetime
import os
import sqlite3
import sys
from typing import Union, Optional, Tuple

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
    ErrorStatus,
    APIType
)
from ._tf_io import JobcanTempFileIO
from .throttled_request import ThrottledRequests
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
    get_progress : Tuple[ProgressStatus, DetailedProgressStatus]
        進捗状況を取得する（致命的なエラーが発生した場合はエラー発生時の進捗状況を返す）
    get_current_progress : Tuple[ProgressStatus, DetailedProgressStatus]
        現在の進捗状況を取得する（致命的なエラーが発生した場合はエラーの詳細を返す）
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
        self._tmp_io = JobcanTempFileIO(os.getcwd())
        self._current_progress = AppProgress(
            *self.config.app_status.progress.get()
        )
        """現在の進捗状況、app_statusと異なり、失敗時にはFAILEDになる"""

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
        # 進捗を確認
        if self.get_current_progress[0] != ProgressStatus.INITIALIZING:
            # 初期化が既に完了している場合は何もしない
            return

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
                self._update_progress(ProgressStatus.FAILED, ie.TokenMissingEnvEmpty())
            elif self.config.api_token_env not in os.environ:
                self._update_progress(ProgressStatus.FAILED,
                                      ie.TokenMissingEnvNotFound(self.config.api_token_env))
            return self.cancel()

        # トークンの更新・有効性の確認
        if not self.update_token(token):
            # 指定されたトークンが無効な場合は終了
            return self.cancel()

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
            self._update_progress(ProgressStatus.FAILED, ie.DatabaseConnectionFailed(e))
            return self.cancel()

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

    def update_token(self, token:str) -> bool:
        """トークンの更新および有効性の確認

        Parameters
        ----------
        token : str
            新しいAPIトークン

        Returns
        -------
        bool
            トークンの更新が成功したかどうか
        """
        headers = self._get_headers(token)

        # トークンの有効性を確認
        response = self._request.get(self.config.base_url+'/test/', headers=headers)
        if response.status_code != 200:
            # トークンが無効
            self._update_progress(ProgressStatus.FAILED, ie.TokenInvalid(token))
            return False

        # トークンの更新
        self._headers = headers
        return True

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
            sub_status:Union[DetailedProgressStatus, ie.JDIErrorData, iw.JDIWarningData],
            current:int=0, total:Union[int,None]=None,
            sub_count:int=0, sub_total_count:int=0
        ) -> None:
        """進捗状況を更新する

        Parameters
        ----------
        status : ProgressStatus
            大枠の進捗状況
        sub_status : DetailedProgressStatus | JDIWarning
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
        """
        # ログメッセージを取得
        if isinstance(sub_status, ie.JDIErrorData):
            level = LogLevel.ERROR
            message = sub_status.error_message()
        elif isinstance(sub_status, iw.JDIWarningData):
            level = LogLevel.WARNING
            message = sub_status.warning_message()
        else:
            level = LogLevel.ERROR if isinstance(sub_status, ErrorStatus) else LogLevel.INFO
            message = ps.get_progress_status_msg(status, sub_status, sub_count, sub_total_count)

        # ログ出力
        self._logger.log(status, message, level)

        # トースト通知
        if self.config.notify_log_level <= level.value:
            self._notifier.notify(title=self.app_id, body=message, level=level)

        # 通知を更新
        if (level == LogLevel.INFO
            or (level == LogLevel.ERROR and self.config.clear_progress_on_error)):
            self._notifier.update(
                status,
                sub_status.status if isinstance(sub_status, ie.JDIErrorData) else sub_status,
                current, total, sub_count, sub_total_count
            )

        # 進捗状況を更新 (警告は無視)
        if isinstance(sub_status, DetailedProgressStatus):
            self._current_progress.set(status, sub_status)
        elif isinstance(sub_status, ie.JDIErrorData):
            self._current_progress.set(ProgressStatus.FAILED, sub_status.status)

        if (status != ProgressStatus.FAILED) and (isinstance(sub_status, DetailedProgressStatus)):
            # 失敗以外の場合、進捗状況を更新・保存
            self.config.app_status.progress.set(status, sub_status)
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
        `.is_cancel`が`False`かつ現在の進捗状況が`GetBasicDataStatus.GET_POSITION`の場合:
        - `APIType.USER_V3` ⇒ `False`
        - `APIType.POSITION` ⇒ `True`
        - `APIType.REQUEST_DETAIL` ⇒ `True`

        `.is_cancel`が`True`、または現在の進捗状況が`ProgressStatus.FAILED`の場合、常に`False`を返す。
        """
        if self.is_canceled or self.get_current_progress[0] == ProgressStatus.FAILED:
            # キャンセルされた場合、またはエラーが発生した場合はFalse
            return False

        stat_outline_v = ps.get_progress_status(api_type).value
        if stat_outline_v < self.get_current_progress[0].value:
            # 進捗状況が過去のものの場合はFalse
            return False
        elif stat_outline_v > self.get_current_progress[0].value:
            # 進捗状況が未来のものの場合はTrue
            return True

        # 進捗状況が同じ場合は詳細進捗状況で判定
        stat_detail_v = ps.get_detailed_progress_status(api_type).value
        return stat_detail_v >= self.get_current_progress[1].value

    #
    # プロパティ
    #

    @property
    def get_progress(self) -> Tuple[ProgressStatus, DetailedProgressStatus]:
        """進捗状況を取得する

        Returns
        -------
        Tuple[ProgressStatus, DetailedProgressStatus]
            進捗状況

        Notes
        -----
        - `.get_current_progress` とは異なり、致命的なエラーが発生した場合は
          発生時の進捗状況を返す。
          - 例) `GetFormOutlineStatus.Get_OUTLINE` でエラーが発生した場合、
            `ProgressStatus.FORM_OUTLINE` と `GetFormOutlineStatus.Get_OUTLINE` を返す
        """
        return self.config.app_status.progress.get()

    @property
    def get_current_progress(self) -> Tuple[ProgressStatus, DetailedProgressStatus]:
        """現在の進捗状況を取得する

        Returns
        -------
        Tuple[ProgressStatus, DetailedProgressStatus]
            現在の進捗状況

        Notes
        -----
        - `.get_progress` とは異なり、致命的なエラーが発生した場合は
          `ProgressStatus.FAILED`と `ErrorStatus` を返す
        """
        return self._current_progress.get()

    @property
    def is_canceled(self) -> bool:
        """処理がキャンセルされたかどうか"""
        return self._is_canceled

    @property
    def is_completed(self) -> bool:
        """全ての処理が完了したかどうか、中断された場合はFalse"""
        return self._completed


    #
    # メイン処理
    #

    def cancel(self):
        """処理をキャンセルする"""
        self._is_canceled = True
        self._completed = False
        self.cleanup()

    def _run(self):
        """メイン処理"""
        # 基本データの取得
        self._update_basic_data()

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
            # デバッグ用: エラーをキャッチしない
            return self._run()

        # 本番用: エラーをキャッチしてアプリケーションの終了を防ぐ
        try:
            self._run()
        except Exception as e:
            self._update_progress(ProgressStatus.FAILED, ie.UnknownError(e))
            self._completed = False
            return

    def _get_basic_data_with_API(
                self,
                api_type: APIType,
                query: str = "",
                skip_on_error: bool = False,
                sub_count: int = 0,
                sub_total_count: int = 0) -> dict:
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
        dict
            取得したデータ.
            `{'success': bool, 'results': list[dict]}` の形式

        Notes
        -----
        - この関数では申請書データ (詳細) は取得できません
        """
        assert api_type != APIType.REQUEST_DETAIL, "この関数では申請書データ (詳細) は取得できません"

        url = self.config.api_base_url[api_type] + query
        page_num = 1
        total_count = 0
        self._update_progress(ps.get_progress_status(api_type),
                              ps.get_detailed_progress_status(api_type),
                              total_count, None,
                              sub_count, sub_total_count)
        results = []
        while True:
            res = self._request.get(url, headers=self._headers)

            if (code:=res.status_code) != 200:
                # 正常なレスポンスが返ってこなかった場合)
                self._update_progress(ProgressStatus.FAILED,
                                      ie.get_api_error(api_type, code, res, query))
                if skip_on_error:
                    # エラーが発生した場合にスキップする場合、現時点で取得したデータを返す
                    return {'success': False, 'results': results}

            res_j = res.json()
            results.extend(res_j['results'])
            if self.config.save_json:
                save_response_to_json(res_j, api_type, page_num,
                                      self.config.json_indent, self.config.json_dir,
                                      self.config.json_encoding)

            total_count += len(res_j['results'])
            self._update_progress(ps.get_progress_status(api_type),
                                  ps.get_detailed_progress_status(api_type),
                                  total_count, res_j['count'],
                                  sub_count, sub_total_count)

            if not res_j['next']:
                # 次のページが存在しない場合にループを抜ける
                break
            url = res_j['next']
            page_num += 1

        return {'success': True, 'results': results}

    def _update_data(self, update_func, data:dict, api_type: APIType) -> bool:
        """DBへデータの更新を試みる。
        `IGNORE_BASIC_DATA_ERROR`が`True`のとき、発生したエラーはキャッチされ、Falseを返す

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
        bool
            処理が正常に完了したかどうか
        """
        if not self.config.ignore_basic_data_error:
            # エラーをキャッチしないケース
            update_func(self._conn, data)
            return True

        try:
            update_func(self._conn, data)
        except sqlite3.Error as e:
            self._update_progress(ProgressStatus.BASIC_DATA,
                                  iw.DBUpdateFailed(api_type, e))
            return False
        return True

    def _update_basic_data(self) -> bool:
        """基本データの取得＆更新

        Returns
        -------
        bool
            処理が正常に完了したかどうか。
            いずれかの段階でエラーが発生した場合はFalseを返す

        Notes
        -----
        - ユーザデータ
        - グループデータ
        - 役職データ
        """
        succeeded = True

        # ユーザデータ取得
        if self._is_future_progress(APIType.USER_V3):
            user_data = self._get_basic_data_with_API(APIType.USER_V3)
            succeeded &= user_data['success']
            # ユーザデータをデータベースに保存
            for res in user_data['results']:
                succeeded &= self._update_data(u_io.update, res, APIType.USER_V3)

        # グループデータ取得
        if self._is_future_progress(APIType.GROUP_V1):
            group_data = self._get_basic_data_with_API(APIType.GROUP_V1)
            succeeded &= group_data['success']
            # グループデータをデータベースに保存
            for res in group_data['results']:
                succeeded &= self._update_data(g_io.update, res, APIType.GROUP_V1)

        # 役職データ取得
        if self._is_future_progress(APIType.POSITION_V1):
            position_data = self._get_basic_data_with_API(APIType.POSITION_V1)
            succeeded &= position_data['success']
            # 役職データをデータベースに保存
            for res in position_data['results']:
                succeeded &= self._update_data(p_io.update, res, APIType.POSITION_V1)

        return succeeded

    def _update_form_outline(self) -> bool:
        """申請書データ (概要) の取得＆更新

        Returns
        -------
        bool
            処理が正常に完了したかどうか。
            いずれかの段階でエラーが発生した場合はFalseを返す

        Notes
        -----
        - 申請書様式データ
        - 申請書データ (概要)
        """
        succeeded = True

        if self._is_future_progress(APIType.FORM_V1):
            # 申請書様式データ取得
            form_data = self._get_basic_data_with_API(APIType.FORM_V1)
            succeeded &= form_data['success']
            # 申請書様式データをデータベースに保存
            for res in form_data['results']:
                succeeded &= self._update_data(f_io.update, res, APIType.FORM_V1)

        if self._is_future_progress(APIType.REQUEST_OUTLINE):
            # 申請書データ (概要) 取得
            ids = f_io.retrieve_form_ids(self._conn)
            tmp_data = {id: None for id in ids}
            # 取得開始日時を設定
            for i, form_id in enumerate(ids):
                query = f"?form_id={form_id}"
                # 前回の取得日時以降のデータのみ取得
                prev_access = self.config.app_status.form_api_last_access.get(form_id, None)
                if prev_access:
                    query += f"&applied_after={prev_access}"

                # 取得開始時刻を記録し、データ取得開始
                last_access = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
                form_outline_data = self._get_basic_data_with_API(
                    APIType.REQUEST_OUTLINE,
                    query=query,
                    sub_count=i+1,
                    sub_total_count=len(ids)
                )
                succeeded &= form_outline_data['success']

                # 申請書データ (概要) を一時ファイルに保存
                tmp_data[form_id] = {
                    'success': form_outline_data['success'],
                    'ids': [res['id'] for res in form_outline_data['results']],
                    'lastAccess': last_access
                }
                # NOTE: 新規記録対象が10000件程度でも保存にかかる時間は0.1s程度のため、毎回直接保存する
                self._tmp_io.save_form_outline(tmp_data)

        return succeeded

    def _update_form_detail(self) -> bool:
        """申請書データ (詳細) の取得＆更新"""
        if not self._is_future_progress(APIType.REQUEST_DETAIL):
            # 申請書データ (詳細) の取得をスキップ
            return True

        # 一時ファイルの読み込み
        self._update_progress(ProgressStatus.FORM_DETAIL,
                              GetFormDetailStatus.SEEK_TARGET, 0, None)
        request_ids = self._tmp_io.load_form_outline()

        for i, item in enumerate(request_ids.items()):
            form_id, data = item
            for j, request_id in enumerate(data['ids']):
                # 申請書データ (詳細) 取得
                res = self._request.get(
                    self.config.api_base_url[APIType.REQUEST_DETAIL]+f"{request_id}/",
                    headers=self._headers
                )
                if (_code:=res.status_code) != 200:
                    self._update_progress(
                        ProgressStatus.FORM_DETAIL,
                        iw.get_form_detail_api_warning(_code, res.json(), request_id)
                    )
                    continue
                # 申請書データ (詳細) をデータベースに保存
                self._update_data(r_io.update, res.json(), APIType.REQUEST_DETAIL)
                self._update_progress(ProgressStatus.FORM_DETAIL,
                                      ps.get_detailed_progress_status(APIType.REQUEST_DETAIL),
                                      j+1, len(data['ids']),
                                      i+1, len(request_ids)-1)

                # 最終更新日時を更新
                self.config.app_status.form_api_last_access[form_id] = data['lastAccess']

        self.cancel() # TODO: 未実装
        return False

        return True

    def cleanup(self):
        """終了処理"""
        # データベースとの接続を閉じる
        if self._conn:
            self._conn.close()

        # 全処理が正常に完了した場合、一時ファイルを削除
        if self._completed:
            self._tmp_io.cleanup()
