"""ThrottledRequests クラスのテストモジュール"""
import time
from unittest.mock import patch, Mock

import pytest
import requests

from jobcan_di.gateway.throttled_request import ThrottledRequests



@pytest.fixture
def throttled_requests():
    return ThrottledRequests(interval_seconds=1.0)

def test_request_interval(throttled_requests):
    """リクエスト間隔が正しく守られているかテスト"""
    with patch('requests.get') as mock_get:
        mock_get.return_value = Mock(status_code=200)

        start_time = time.time()
        throttled_requests.get('http://example.com')
        throttled_requests.get('http://example.com')
        end_time = time.time()

        assert end_time - start_time >= 1.0, "リクエスト間隔が1秒未満です"

def test_get_request_execution(throttled_requests):
    """GETリクエストが正しく実行されているかテスト"""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Hello, World!"
        mock_get.return_value = mock_response

        response = throttled_requests.get('http://example.com')

        assert response.status_code == 200
        assert response.text == "Hello, World!"
        mock_get.assert_called_once_with('http://example.com', timeout=30)

def test_timeout_functionality(throttled_requests):
    """タイムアウトが正しく機能しているかテスト"""
    with patch('requests.get', side_effect=requests.Timeout):
        with pytest.raises(requests.Timeout):
            throttled_requests.get('http://example.com', timeout=0.1)

def test_consecutive_requests(throttled_requests):
    """連続したリクエストの挙動をテスト"""
    with patch('requests.get') as mock_get, \
         patch('time.sleep') as mock_sleep:
        mock_get.return_value = Mock(status_code=200)

        throttled_requests.get('http://example.com')
        throttled_requests.get('http://example.com')
        throttled_requests.get('http://example.com')

        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 3  # 初回リクエスト時にも sleep が呼ばれる

def test_custom_timeout(throttled_requests):
    """カスタムタイムアウトが正しく適用されているかテスト"""
    with patch('requests.get') as mock_get:
        mock_get.return_value = Mock(status_code=200)

        throttled_requests.get('http://example.com', timeout=5)

        mock_get.assert_called_once_with('http://example.com', timeout=5)

def test_additional_kwargs(throttled_requests):
    """追加のkwargsが正しく渡されているかテスト"""
    with patch('requests.get') as mock_get:
        mock_get.return_value = Mock(status_code=200)

        headers = {'User-Agent': 'MyBot'}
        throttled_requests.get('http://example.com', headers=headers)

        mock_get.assert_called_once_with('http://example.com', timeout=30, headers=headers)
