"""
ジョブカンのAPIからデータを取得し、データベースに保存するモジュール

Classes
-------
- `JobcanDataIntegrator`: ジョブカンのAPIからデータを取得し、データベースに保存するクラス
- `JobcanDIConfig`: ジョブカンデータインテグレータの設定クラス
- `LogLevel`: ログレベルを表すEnum

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
from .integrator import JobcanDataIntegrator
from .integrator_config import JobcanDIConfig, LogLevel
