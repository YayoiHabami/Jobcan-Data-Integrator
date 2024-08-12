"""
Jobcan Data Integratorの設定を管理するクラス

Classes
-------
JobcanDIConfig:
    Jobcan Data Integratorの設定を管理するクラス
    大まかに以下の項目を管理する
- config.ini 由来
    - APIの設定
    - データ取得の設定
    - データベースの設定
    - ログの設定
    - 通知の設定
    - デバッグの設定
- config.ini 以外
    - Jobcanの各APIのベースURL
    - 画像などのパス

Enums
-----
LogLevel: ログレベル
"""
from enum import Enum
from os import path, makedirs

from jobcan_di.config.config_editor import ConfigEditor
from .progress_status import APIType



# ログレベル
class LogLevel(Enum):
    """
    ログレベル
    """
    INFO = 1
    WARNING = 2
    ERROR = 3
MAX_LOG_LEVEL_LENGTH = max([len(s.name) for s in LogLevel])


class JobcanDIConfig:
    """
    Jobcan Data Integratorの設定を管理するクラス
    """

    def __init__(self, app_dir:str):
        """
        Parameters
        ----------
        app_dir : str
            アプリケーションのディレクトリ
            この下に設定ファイルや前回の進捗状況などを保存するディレクトリが作成される
        """
        self.settings_dir = path.join(app_dir, 'config')
        """設定ファイルや前回の進捗状況などを保存するディレクトリ"""
        self.config_file = path.join(self.settings_dir, 'config.ini')
        """コンフィグファイル"""
        self.app_status_file = path.join(self.settings_dir, 'app_status')
        """前回の進捗状況などを保存するファイル"""

        # 上記ディレクトリ/ファイルが存在しない場合は作成
        if not path.exists(self.settings_dir):
            makedirs(self.settings_dir)
        if not path.exists(self.config_file):
            pass # TODO: config.iniの初期化（存在しない場合のみ）
        if not path.exists(self.app_status_file):
            pass # TODO: api_status.jsonの初期化（存在しない場合のみ）

        _c = ConfigEditor(self.config_file, encoding='utf-8')

        self.api_token_env = _c['API']['TOKEN_ENV_NAME'].value
        """APIのトークン取得先（環境変数名）"""
        self.api_token = _c['API']['API_TOKEN'].value
        """APIのトークン"""
        self.requests_per_hour = _c['API']['REQUESTS_PER_HOUR'].value
        """1時間あたりのリクエスト回数上限"""
        self.requests_per_sec = rps if (rps := _c['API']['REQUESTS_PER_SEC'].value) >= 0 else 3600 / self.requests_per_hour
        """リクエストの間隔 (秒)"""

        self.save_json = _c['DATA_RETRIEVAL']['SAVE_RAW_DATA'].value
        """APIによるデータ取得時にJSONファイルを保存するか"""
        self.json_dir = _c['DATA_RETRIEVAL']['RAW_DATA_DIR'].value.replace('{BASE_DIR}', app_dir)
        """JSONファイルの保存先ディレクトリ"""
        self.json_indent = _c['DATA_RETRIEVAL']['JSON_INDENT'].value
        """JSONファイルのインデント数"""
        self.json_padding = _c['DATA_RETRIEVAL']['JSON_PADDING'].value
        """JSONファイルのページ番号の桁数"""
        self.json_encoding = _c['DATA_RETRIEVAL']['JSON_ENCODING'].value
        """JSONファイルのエンコーディング方式"""
        self.include_canceled_forms = _c['DATA_RETRIEVAL']['INCLUDE_CANCELED_FORMS'].value
        """取り消した申請書も取得するかどうか"""
        self.ignore_basic_data_error = _c['DATA_RETRIEVAL']['IGNORE_BASIC_DATA_ERROR'].value
        """基礎データ (ユーザ・グループ・役職) の取得・保存エラーを無視するか"""

        self.db_path = _c['DATABASE']['DB_PATH'].value.replace('{BASE_DIR}', app_dir)
        """データベースファイルのパス"""
        self.form_table_path = _c['DATABASE']['FORM_TABLE_NAME_PATH'].value.replace(
            '{BASE_DIR}', app_dir
        )
        """各申請書テーブルのID-名前対応表のパス"""
        self.form_table_encoding = _c['DATABASE']['FORM_TABLE_NAME_ENCODING'].value
        """各申請書テーブルのID-名前対応表のエンコーディング方式"""
        self.form_table_delimiter = _c['DATABASE']['FORM_TABLE_NAME_DELIMITER'].value
        """各申請書テーブルのID-名前対応表の区切り文字"""

        self.log_init = _c['LOGGING']['LOG_INIT'].value
        """"
        ログの初期化をいつ行うか
        - "NEVER": 初期化しない
        - "ALWAYS_ON_STARTUP": 常に起動時に初期化
        """
        self.log_path = _c['LOGGING']['LOG_PATH'].value.replace('{BASE_DIR}', app_dir)
        """ログファイルのパス"""
        self.default_log_path = path.join(app_dir, 'jobcan-retrieval.log')
        """ログファイルのパス (エラー用; 上記のパスが不正な場合に使用)"""
        self.log_encoding = _c['LOGGING']['LOG_ENCODING'].value
        """ログファイルのエンコーディング方式"""

        self.enable_notification = _c['NOTIFICATION']['ENABLE_NOTIFICATION'].value
        """トースト通知を行うか"""
        self.clear_previous_notifications_on_startup = _c['NOTIFICATION']['CLEAR_PREVIOUS_NOTIFICATIONS_ON_STARTUP'].value
        """起動時に前回以前の通知を全て削除するか"""
        self.notify_log_level = 0 if (_lv:=_c['NOTIFICATION']['NOTIFY_LOG_LEVEL'].value) == "NEVER" else LogLevel[_lv].value
        """一定レベル以上のログをトースト通知するか
        - 0 ("NEVER"): 通知しない
        - 1 ("INFO"): INFO以上通知（すべて通知）
        - 2 ("WARNING"): 警告以上通知
        - 3 ("ERROR"): エラーのみ通知
        """ # TODO: LogLevelの値の差異を修正

        self.logging_to_console = _c['DEBUGGING']['LOG_TO_CONSOLE'].value
        """ログ出力をコンソールにも行うか"""
        self.catch_errors_on_run = _c['DEBUGGING']['CATCH_ERRORS_ON_RUN'].value
        """.run() メソッド実行時にエラーをcatchするか (False: デバッグ用)"""

        #
        # 定数定義 ('config.ini'以外)
        #

        self.base_url = 'https://ssl.wf.jobcan.jp/wf_api'
        """Jobcan APIのベースURL"""

        self.api_base_url = {
            APIType.USER_V3: f'{self.base_url}/v3/users/',
            APIType.GROUP_V1: f'{self.base_url}/v1/groups/',
            APIType.POSITION_V1: f'{self.base_url}/v1/positions/',
            APIType.FORM_V1: f'{self.base_url}/v1/forms/',
            APIType.REQUEST_OUTLINE: f'{self.base_url}/v2/requests/',
            APIType.REQUEST_DETAIL: f'{self.base_url}/v1/requests/',
        }
        """APIのベースURL"""

        self.app_icon_png_path = {
            LogLevel.INFO: path.join(app_dir, 'resources', 'normal_icon.png'),
            LogLevel.WARNING: path.join(app_dir, 'resources', 'warning_icon.png'),
            LogLevel.ERROR: path.join(app_dir, 'resources', 'error_icon.png')
        }
        """本アプリケーションのトースト通知用アイコンのパス"""
