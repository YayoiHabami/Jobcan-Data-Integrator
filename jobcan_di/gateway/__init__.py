"""
jobcan_di.gateway パッケージ

ジョブカン経費精算/ワークフローAPIとの通信を行うクラスを提供する

Modules
-------
- `api_client`: ジョブカンAPIとの通信を行うクラスを提供
- `throttled_request`: リクエスト送信を制御するクラスを提供

Classes
-------
- `ApiResponse`: APIのレスポンスデータ
- `FormOutline`: 申請書(概要)のデータクラス
- `JobcanApiClient`: ジョブカンAPIとの通信を行うクラス
- `JobcanApiGateway`: ジョブカンAPIとの通信・DBへのデータ保存を行うクラス

Constants
---------
- `UNIQUE_IDENTIFIER_KEYS`: 各APIごとのユニーク識別子のキー
- `get_unique_identifier`: ユニーク識別子を取得する関数
"""
from ._core import ApiResponse, FormOutline, UNIQUE_IDENTIFIER_KEYS, get_unique_identifier
from .api_client import JobcanApiClient
from .gateway import JobcanApiGateway
