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
"""
from ._core import ApiResponse, FormOutline
from .api_client import JobcanApiClient
