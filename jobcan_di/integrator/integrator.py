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
from enum import Enum
import datetime
import os
import sqlite3
import sys
from typing import Union, Optional

from jobcan_di.database import (
    forms as f_io,
    group as g_io,
    positions as p_io,
    users as u_io,
    requests as r_io
)
from .integrator_config import JobcanDIConfig, LogLevel, MAX_LOG_LEVEL_LENGTH
from ._json_data_io import save_response_to_json
from . import progress_status as ps
from .progress_status import (
    ProgressStatus,
    InitializingStatus,
    GetBasicDataStatus,
    GetFormOutlineStatus,
    GetFormDetailStatus,
    APIType
)
from ._tf_io import JobcanTempFileIO
from .throttled_request import ThrottledRequests
from ._toast_notification import notify, clear_toast, NotificationData, ToastNotificationManager



#
# Data Integrator
#
class JobcanDataIntegrator:
    """
    JobcanのAPIを使用してデータを取得するクラス
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
        self._log_path = self.config.default_log_path
        self._headers = {}
        self._request = ThrottledRequests(self.config.requests_per_sec)
        self._conn = None
        self._notification_data = None
        self._notifier = None
        self._completed = False
        """全ての処理が完了したかどうか、中断された場合もFalse"""
        self._tmp_io = JobcanTempFileIO(os.getcwd())

        # 初期化処理
        self._init_logger()
        self._init_progress_notification()
        self._init_directories()
        self._init_token()
        self._init_connection()
        self._init_tables()
        self.logger(ProgressStatus.INITIALIZING,
                    "初期化が完了しました",
                    LogLevel.INFO)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.cleanup()

    def _init_logger(self):
        """ロガーの初期化 (出力先など)"""
        # 出力先の設定
        try:
            self._log_path = self.config.log_path
            if not os.path.exists(os.path.dirname(self.config.log_path)):
                os.makedirs(os.path.dirname(self.config.log_path))
        except OSError:
            pass

        if self.config.log_init == "ALWAYS_ON_STARTUP":
            # 毎回初期化する設定の場合はログファイルを初期化
            if os.path.exists(self._log_path):
                with open(self._log_path, "w", encoding=self.config.log_encoding) as f:
                    f.write("")

        # 本アプリケーションに関するトースト通知を全て削除
        if self.config.clear_previous_notifications_on_startup:
            clear_toast(app_id=self.app_id)

        # 'config.ini'のLOG_PATHが不正な場合はエラーを出力
        if self._log_path != self.config.log_path:
            self.logger(
                ProgressStatus.INITIALIZING,
                "'config.ini'で指定されたログファイルのパスが不正です。"
                +"デフォルトのログファイルを使用します: {self.config.default_log_path}",
                LogLevel.WARNING
            )

    def _init_progress_notification(self):
        """進捗に関するトースト通知の初期化"""
        # トースト通知の作成
        notify(progress = {
            'title': '初期化中...',
            'status': '初期化中...',
            'value': 0,
            'valueStringOverride': '0%',
            },
            app_id = self.app_id,
            group=LogLevel.INFO.name,
            scenario="reminder",
            icon=self.config.app_icon_png_path[LogLevel.INFO],
            title=self.app_id,
            body='しばらくお待ちください...',
            duration='short',
            suppress_popup=True # 通知センターにのみ表示
        )
        # 進捗状況の更新
        self.update_progress(ProgressStatus.INITIALIZING,
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
        self.update_progress(ProgressStatus.INITIALIZING,
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
                self.logger(ProgressStatus.INITIALIZING,
                            "'setting.ini'にトークン取得先の環境変数名が指定されていません。"
                            + "TOKEN_ENV_NAMEを指定するか、API_TOKENにトークンを設定してください。",
                            LogLevel.ERROR)
            elif self.config.api_token_env not in os.environ:
                self.logger(
                    ProgressStatus.INITIALIZING,
                    f"指定された環境変数 {self.config.api_token_env} が設定されていません。環境変数の設定を行ってください。",
                    LogLevel.ERROR
                )
            self.cleanup()
            sys.exit(1)

        # トークンの更新・有効性の確認
        self.update_token(token)

        # 進捗状況の更新
        self.update_progress(ProgressStatus.INITIALIZING,
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
            self.logger(ProgressStatus.INITIALIZING,
                        f"データベースの接続に失敗しました: {e}",
                        LogLevel.ERROR)
            self.cleanup()
            sys.exit(1)

        # 進捗状況の更新
        self.update_progress(ProgressStatus.INITIALIZING,
                             InitializingStatus.INIT_DB_CONNECTION, 1, 1)

    def _init_tables(self):
        """テーブルの初期化"""
        f_io.create_tables(self._conn)
        g_io.create_tables(self._conn)
        p_io.create_tables(self._conn)
        u_io.create_tables(self._conn)
        r_io.create_tables(self._conn)

        # 進捗状況の更新
        self.logger(ProgressStatus.INITIALIZING,
                    "データベースの準備が完了しました",
                    LogLevel.INFO)
        self.update_progress(ProgressStatus.INITIALIZING,
                             InitializingStatus.INIT_DB_TABLES, 1, 1)

    def update_token(self, token:str):
        """トークンの更新および有効性の確認

        Parameters
        ----------
        token : str
            新しいAPIトークン
        """
        headers = self._get_headers(token)

        # トークンの有効性を確認
        response = self._request.get(self.config.base_url+'/test/', headers=headers)
        if response.status_code != 200:
            self.logger(ProgressStatus.INITIALIZING,
                        f"APIトークンが無効です。設定を確認してください (トークン: {token[:3]}{'*'*(len(token)-3)})",
                        LogLevel.ERROR)
            print(response.json())
            self.cleanup()
            sys.exit(1)

        # トークンの更新
        self._headers = headers
        self.logger(ProgressStatus.INITIALIZING,
                    f"APIトークン ({token[:3]}{'*'*(len(token)-3)}) の認証に成功しました",
                    LogLevel.INFO)

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

    def logger(self, status:ProgressStatus,
               text:str,
               level:LogLevel=LogLevel.INFO):
        """ログ出力"""
        text = (f"[{level.name}]".ljust(MAX_LOG_LEVEL_LENGTH+3)
                + f"{datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')}, "
                + f"{status.name},".ljust(ps.MAX_STATUS_LENGTH+2)
                + text)
        # ログファイルに書き込み
        with open(self._log_path, "a", encoding=self.config.log_encoding) as f:
            f.write(text + "\n")

        # コンソールに出力
        if self.config.logging_to_console:
            print(text)

        # トースト通知
        if self.config.notify_log_level <= level.value:
            notify(title=self.app_id,
                   body=text,
                   app_id=self.app_id,
                   group=level.name,
                   icon=self.config.app_icon_png_path[level],)

    def update_progress(self, status:ProgressStatus, sub_status:Enum,
                        current:int, total:Union[int,None],
                        sub_count:int=0, sub_total_count:int=0):
        """進捗状況を更新する

        Parameters
        ----------
        status : ProgressStatus
            大枠の進捗状況
        sub_status : Enum
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
        # sub_statusのメッセージを取得
        status_msg = ps.get_progress_status_msg(status, sub_status, sub_count, sub_total_count)
        if total is None:
            value = 0 if current == 0 else 1
            str_value = f"{current}/?"
        elif total == 0:
            value = 1
            str_value = "0/0"
        else:
            value = current / total
            str_value = f"{current}/{total}"

        # NotificationDataとNotifierの初期化
        if self._notifier is None:
            self._notification_data = NotificationData()
            self._notifier = ToastNotificationManager.create_toast_notifier(self.app_id)

        self._notification_data.values['title'] = ps.PROGRESS_STATUS_MSG[status]
        self._notification_data.values['status'] = status_msg
        self._notification_data.values['value'] = str(value)
        self._notification_data.values['valueStringOverride'] = str_value
        self._notification_data.sequence_number = 2

        self._notifier.update(self._notification_data, 'my_tag', LogLevel.INFO.name)

    def _run(self):
        """メイン処理"""
        # 基本データの取得
        if not self._update_basic_data():
            self._completed = False
            return

        # 申請書データ (概要) の取得
        if not self._update_form_outline():
            self._completed = False
            return

        # 申請書データ (詳細) の取得
        if not self._update_form_detail():
            self._completed = False
            return

        # 全処理が完了
        self._completed = True

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
            self.logger(ProgressStatus.FAILED,
                        f"エラーが発生しました: {e}",
                        LogLevel.ERROR)
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
            第2段階進捗に可算する値 -> update_progress() に渡す
        sub_total_count : int, default 0
            第2段階進捗の全体数に可算する値 -> update_progress() に渡す

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
        target_data_name = ps.API_TYPE_NAME[api_type]

        url = self.config.api_base_url[api_type] + query
        page_num = 1
        total_count = 0
        self.logger(ProgressStatus.BASIC_DATA,
                    f"{target_data_name}を取得中...",
                    LogLevel.INFO)
        self.update_progress(ps.get_progress_status(api_type),
                             ps.get_detailed_progress_status(api_type),
                             total_count, None,
                             sub_count, sub_total_count)
        results = []
        while True:
            res = self._request.get(url, headers=self._headers)

            if (code:=res.status_code) != 200:
                # 正常なレスポンスが返ってこなかった場合
                error_message = res.json()['message']
                self.logger(ProgressStatus.BASIC_DATA,
                            f"{target_data_name}の取得に失敗しました: (code={code}, {error_message})",
                            LogLevel.ERROR)
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
            self.logger(ProgressStatus.BASIC_DATA,
                        f"{target_data_name}の取得完了: {total_count}/{res_j['count']}",
                        LogLevel.INFO)
            self.update_progress(ps.get_progress_status(api_type),
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
            self.logger(ProgressStatus.BASIC_DATA,
                        f"{ps.API_TYPE_NAME[api_type]}の更新に失敗しました: {e}",
                        LogLevel.ERROR)
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
        user_data = self._get_basic_data_with_API(APIType.USER_V3)
        succeeded &= user_data['success']
        # ユーザデータをデータベースに保存
        for res in user_data['results']:
            succeeded &= self._update_data(u_io.update, res, APIType.USER_V3)

        # グループデータ取得
        group_data = self._get_basic_data_with_API(APIType.GROUP_V1)
        succeeded &= group_data['success']
        # グループデータをデータベースに保存
        for res in group_data['results']:
            succeeded &= self._update_data(g_io.update, res, APIType.GROUP_V1)

        # 役職データ取得
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

        # 申請書様式データ取得
        form_data = self._get_basic_data_with_API(APIType.FORM_V1)
        succeeded &= form_data['success']
        # 申請書様式データをデータベースに保存
        for res in form_data['results']:
            succeeded &= self._update_data(f_io.update, res, APIType.FORM_V1)

        # 申請書データ (概要) 取得
        # TODO: 作成日時の範囲を指定可能にする（コンフィグファイルで指定？）
        #       最終更新日時に関しては、DBに保存されている
        ids = f_io.retrieve_form_ids(self._conn)
        tmp_data = {id: None for id in ids}
        # 取得開始日時を設定
        tmp_data["lastAccess"] = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
        for i, form_id in enumerate(ids):
            form_outline_data = self._get_basic_data_with_API(APIType.REQUEST_OUTLINE,
                                                              query=f"?form_id={form_id}",
                                                              sub_count=i+1,
                                                              sub_total_count=len(ids))
            succeeded &= form_outline_data['success']
            # 申請書データ (概要) を一時ファイルに保存
            tmp_data[form_id] = {
                'success': form_outline_data['success'],
                'ids': [res['id'] for res in form_outline_data['results']]
            }
        self._tmp_io.save_form_outline(tmp_data)

        return succeeded

    def _update_form_detail(self) -> bool:
        """申請書データ (詳細) の取得＆更新"""
        # 一時ファイルの読み込み
        request_ids = self._tmp_io.load_form_outline()

        for i, item in enumerate(request_ids.items()):
            form_id, data = item
            print(f"{form_id=}")
            if form_id == "lastAccess":
                continue
            for j, request_id in enumerate(data['ids']):
                # 申請書データ (詳細) 取得
                res = self._request.get(
                    self.config.api_base_url[APIType.REQUEST_DETAIL]+f"{request_id}/",
                    headers=self._headers
                )
                if (_code:=res.status_code) != 200:
                    self.logger(
                        ProgressStatus.FORM_DETAIL,
                        f"申請書データ (詳細) の取得に失敗しました: (code={_code}, {res.json()['message']})",
                        LogLevel.ERROR
                    )
                    continue
                # 申請書データ (詳細) をデータベースに保存
                self._update_data(r_io.update, res.json(), APIType.REQUEST_DETAIL)
                self.update_progress(ProgressStatus.FORM_DETAIL,
                                     ps.get_detailed_progress_status(APIType.REQUEST_DETAIL),
                                     j+1, len(data['ids']),
                                     i+1, len(request_ids)-1)

        return False # TODO: 未実装
        # 全申請書データの更新に成功したら最終更新日時を更新
        last_access = request_ids["lastAccess"]

        return True

    def cleanup(self):
        """終了処理"""
        # データベースとの接続を閉じる
        if self._conn:
            self._conn.close()

        # 全処理が正常に完了した場合、一時ファイルを削除
        if self._completed:
            self._tmp_io.cleanup()
