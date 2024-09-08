"""
jobcan_di.status パッケージ

Jobcan Data Integratorの進捗状況を管理するクラスを提供する

Modules
-------
- `errors`: エラークラスを提供
- `progress`: 進捗状況を定義するクラス等を提供
- `status`: 進捗状況を管理するクラスを提供
- `warnings`: 警告クラスを提供
"""
from .status import (
    AppProgress,
    FailureRecord, DBSaveFailureRecord, FetchFailureRecord,
    JobcanDIStatus,
    merge_status
)
