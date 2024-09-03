"""
リクエスト間隔を調整してリクエストを送信するクラス ThrottledRequests を定義するモジュール

Usage
-----

1. インスタンスの作成（リクエスト間隔を 1 秒に設定する場合）

```python
throttled_requests = ThrottledRequests(interval_seconds=1.0)
```

2. GET リクエストを送信する。前回のリクエストから 1 秒以上経過していない場合はリクエスト間隔を調整する。

```python
response = throttled_requests.get("https://example.com")
```
"""
import time
import requests

class ThrottledRequests:
    """
    リクエスト間隔を調整してリクエストを送信するクラス
    """
    def __init__(self, interval_seconds: float):
        """
        Parameters
        ----------
        interval_seconds : float
            リクエスト間隔（秒）
        """
        self._interval_seconds = interval_seconds
        self.last_request_time = time.perf_counter()

    def get(self,
            url: str,
            timeout: int = 30,
            **kwargs):
        """
        GET リクエストを送信する

        Parameters
        ----------
        url : str
            リクエスト先 URL
        timeout : int
            タイムアウト時間（秒）
        **kwargs
            requests.get に渡す引数
        """
        current_time = time.perf_counter()
        time_since_last_request = current_time - self.last_request_time

        if time_since_last_request < self._interval_seconds:
            time.sleep(self._interval_seconds - time_since_last_request)

        response = requests.get(url, timeout=timeout, **kwargs)
        self.last_request_time = time.perf_counter()

        return response

    def update_interval(self, interval_seconds: float):
        """
        リクエスト間隔を更新する

        Parameters
        ----------
        interval_seconds : float
            リクエスト間隔（秒）
        """
        self._interval_seconds = interval_seconds
