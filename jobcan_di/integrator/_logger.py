"""
ログ出力モジュール

Classes
-------
- `Logger` : ロガー
"""
import datetime
from os import path, makedirs

from jobcan_di.status.progress import ProgressStatus, MAX_STATUS_LENGTH
from .integrator_config import LogLevel, MAX_LOG_LEVEL_LENGTH



class Logger:
    """ロガー"""
    def __init__(self, default_log_path:str):
        """ロガーの初期化

        Parameters
        ----------
        default_log_path : str
            ログファイルのデフォルトのパス
            .init_logger()で指定されたパスが不正な場合に使用する。
            アクセス可能であることが保証されている必要がある。
        """
        self._path = None
        self._encoding = "utf-8"
        self._logging_to_console = False
        self._default_log_path = default_log_path

    def init_logger(self, log_path:str, encoding:str="utf-8",
                    init_log:bool=False, logging_to_console:bool=False) -> bool:
        """ロガーの初期化

        Parameters
        ----------
        path : str
            ログファイルのパス
        encoding : str, default "utf-8"
            ログファイルのエンコーディング
        init_log : bool, default False
            ログファイルを初期化するかどうか
        logging_to_console : bool, default False
            コンソールにもログを出力するかどうか

        Returns
        -------
        bool
            指定されたパスでのログファイルの初期化が成功したかどうか
        """
        success = True
        try:
            # ログファイルのディレクトリが存在しない場合は作成
            if not path.exists(path.dirname(log_path)):
                makedirs(path.dirname(log_path))
        except OSError:
            # アクセス権限がない場合などはデフォルトのログファイルパスを使用
            success = False
            self._path = self._default_log_path

        if init_log and path.exists(log_path):
            # ログファイルを初期化
            with open(log_path, "w", encoding=encoding) as f:
                f.write("")

        self._path = log_path
        self._encoding = encoding
        self._logging_to_console = logging_to_console

        return success

    def log(self, status:ProgressStatus, message:str,
            level:LogLevel=LogLevel.INFO) -> bool:
        """ログの出力

        Parameters
        ----------
        status : ProgressStatus
            進捗ステータス
        message : str
            ログメッセージ
        level : LogLevel, default LogLevel.INFO
            ログのレベル

        Returns
        -------
        bool
            ログの出力が成功したかどうか
        """
        if self._path is None:
            return False

        text = (f"[{level.name}]".ljust(MAX_LOG_LEVEL_LENGTH+3)
               + f"{datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')}, "
               + f"{status.name},".ljust(MAX_STATUS_LENGTH+2)
               + message)

        if self._logging_to_console:
            print(text)

        try:
            with open(self._path, "a", encoding=self._encoding) as f:
                f.write(text + "\n")
        except OSError:
            return False
