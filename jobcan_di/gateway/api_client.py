"""
ジョブカン経費精算/ワークフローAPIとの通信を行うクラスを提供するモジュール

Classes
-------
- `JobcanApiClient`: ジョブカン経費精算/ワークフローAPIとの通信を行うクラス
"""
import json
from pathlib import Path
from typing import Callable, Dict, Literal, Optional, Union

from requests import exceptions as req_ex

from jobcan_di.status import errors as ie
from jobcan_di.status.progress import APIType, API_TYPE_NAME
from jobcan_di.status import warnings as iw
from .throttled_request import ThrottledRequests
from ._core import ApiResponse, FormOutline



DEFAULT_API_SUFFIX: Dict[APIType, str] = {
    APIType.USER_V3: "/v3/users/",
    APIType.GROUP_V1: "/v1/groups/",
    APIType.POSITION_V1: "/v1/positions/",
    APIType.FORM_V1: "/v1/forms/",
    APIType.REQUEST_OUTLINE: "/v2/requests/",
    APIType.REQUEST_DETAIL: "/v1/requests/"
}

def _generate_headers(token:str) -> dict:
    """APIリクエストのヘッダを生成

    Parameters
    ----------
    token : str
        トークン

    Returns
    -------
    dict
        APIリクエストのヘッダ
    """
    return {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }

class JobcanApiClient:
    """ジョブカン経費精算/ワークフローAPIとの通信を行うクラス

    Attributes
    ----------
    - `is_token_verified` : トークンの有効性が確認されているか
    - `is_prepared` : APIクライアントが準備されているか、`False`の場合、APIクライアントは使用できない

    Usage
    -----
    ```python
    # インスタンスを生成
    client = JobcanApiClient(interval_seconds=1)

    # トークンを更新
    token = "your_token"
    client.update_token(token)

    # JSON出力設定を更新 (JSON出力を行う場合)
    client.update_json_config(json_output_dir="json_output",
                              json_indent=2, json_encoding="utf-8")

    # 何かしらのAPIリクエストを行う
    res = client.fetch_basic_data(APIType.USER_V3)
    ```
    """

    def __init__(self,
                 interval_seconds: float,
                 *,
                 base_url = "https://ssl.wf.jobcan.jp/wf_api",
                 api_suffix: Optional[Dict[APIType, str]] = None,
                 json_output_dir: Optional[str] = None
            ) -> None:
        """コンストラクタ

        Parameters
        ----------
        interval_seconds : int
            リクエスト間隔 (秒)
        base_url : str, optional, default "https://ssl.wf.jobcan.jp/wf_api"
            ジョブカン経費精算/ワークフローAPIのベースURL
        api_suffix : Optional[Dict[APIType, str]], optional
            APIのエンドポイント、
            指定されない場合はデフォルト値 (DEFAULT_API_SUFFIX) が使用される
        json_output_dir : Optional[str], optional
            JSON出力ディレクトリ、指定された場合はJSON出力を行う
        """
        self._requests = ThrottledRequests(interval_seconds=interval_seconds)
        """リクエスト送信クラス"""
        self._headers = {}
        """APIリクエストのヘッダ。トークンを含み、空ではない場合はトークンが有効であることを示す"""
        self._base_url = base_url
        """Jobcan APIのベースURL"""
        api_suffix = api_suffix or DEFAULT_API_SUFFIX # 両方指定された場合はapi_suffixを優先
        self._api_base_url = {
            k: f"{base_url}{v}" for k, v in api_suffix.items()
        }
        """APIのベースURL"""
        self._api_test_url = f"{base_url}/test/"
        """APIのテスト用URL"""

        # JSON出力関連
        self._json_output_dir = json_output_dir
        """JSON出力ディレクトリ、指定された場合はJSON出力を行う"""
        self._json_indent = 2
        """JSON出力時のインデント"""
        self._json_encoding = "utf-8"
        """JSON出力時のエンコーディング"""

        # 実行に必要なフラグ
        self._is_token_verified = False
        """トークンの有効性が確認されているか"""

    #
    # 初期設定関連
    #

    def update_json_config(self,
                           json_output_dir: Optional[str] = None,
                           json_indent: Optional[int] = 2,
                           json_encoding: str = "utf-8") -> None:
        """JSON出力設定の更新

        Parameters
        ----------
        json_output_dir : Optional[str]
            JSON出力ディレクトリ、指定された場合はJSON出力を行う
        json_indent : int
            JSON出力時のインデント、Noneまたは負の値の場合はインデントなし
        json_encoding : str
            JSON出力時のエンコーディング
        """
        if json_output_dir is not None:
            self._json_output_dir = json_output_dir

        if json_indent is not None and json_indent >= 0:
            self._json_indent = json_indent
        else:
            self._json_indent = None

        if json_encoding is not None:
            self._json_encoding = json_encoding

    def update_token(self, token:str) -> Optional[ie.JDIErrorData]:
        """トークンの更新および有効性の確認

        Parameters
        ----------
        token : str
            トークン

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラー情報。エラーがない場合はNone

        Notes
        -----
        - トークンの有効性が確認されない場合、トークンは更新されない
        """
        headers = _generate_headers(token)

        # トークンの有効性を確認
        res = self._requests.get(self._api_test_url, headers=headers)
        if res.status_code != 200:
            return ie.TokenInvalid(token)

        # トークンの更新
        self._headers = headers
        self._is_token_verified = True
        return None

    def update_interval(self, interval_seconds: int) -> None:
        """リクエスト間隔の更新

        Parameters
        ----------
        interval_seconds : int
            リクエスト間隔 (秒)
        """
        self._requests.update_interval(interval_seconds)

    #
    # プロパティ
    #

    @property
    def is_token_verified(self) -> bool:
        """トークンの有効性が確認されているか"""
        return self._is_token_verified

    @property
    def is_prepared(self) -> bool:
        """APIクライアントが準備されているか"""
        return self.is_token_verified

    #
    # APIリクエスト関連
    #

    def _save_as_json(self, api_type:APIType, response:dict, *,
                      page:Optional[int]=None,
                      request_id:Optional[str]=None) -> None:
        """APIのレスポンスをJSONファイルに保存

        Parameters
        ----------
        api_type : APIType
            APIの種類
        response : dict
            APIのレスポンス
        page : int, optional
            ページ番号
        request_id : str, optional
            申請書のID、指定された場合はファイル名に含める

        Notes
        -----
        - JSON出力ディレクトリが指定されていない場合は何もしない
        """
        if self._json_output_dir is None:
            # JSON出力ディレクトリが指定されていない場合は何もしない
            return

        request_txt = f"-r{request_id}" if request_id is not None else ""
        file_name = f"{API_TYPE_NAME[api_type]}-p{page}{request_txt}.json"
        with open(Path(self._json_output_dir) / file_name, "w", encoding=self._json_encoding) as f:
            json.dump(response, f, indent=self._json_indent, ensure_ascii=False)

    def _fetch_data(
            self,
            url:str,
            api_type:APIType,
            *,
            issue_callback:Optional[Callable[[Union[ie.JDIErrorData, iw.JDIWarningData]],
                                             None]] = None
        ) -> ApiResponse:
        """APIを使用してデータを取得する

        Parameters
        ----------
        url : str
            APIのURL
        api_type : APIType
            取得するデータの種類
        issue_callback : func(Union[ie.JDIErrorData, iw.JDIWarningData]) -> None, optional
            エラー/警告が発生した場合に呼び出されるコールバック関数

        Returns
        -------
        ApiResponse
            取得したデータ、APIの種類などに関わらず.json()の内容を格納する
        """
        if not self.is_prepared:
            # APIクライアントが準備されていない場合
            msg = {
                "トークン認証": "済" if self.is_token_verified else "失敗"
            }
            return ApiResponse(error=ie.ApiClientNotPrepared(json.dumps(msg, ensure_ascii=False)))

        try:
            res = self._requests.get(url, headers=self._headers)
            j_res = res.json()

            if res.status_code != 200:
                # 正常なレスポンスが返ってこなかった場合
                warning = iw.get_api_error(api_type, res.status_code, j_res, url)
                if issue_callback is not None:
                    # 警告を発行
                    issue_callback(warning)
                return ApiResponse(error=warning)

            # 正常なレスポンスが返ってきた場合
            return ApiResponse(results=[j_res])
        except req_ex.ConnectionError as e:
            # 通信エラー
            return ApiResponse(error=ie.RequestConnectionError(e))
        except req_ex.ReadTimeout as e:
            # タイムアウト
            return ApiResponse(error=ie.RequestReadTimeout(e))

    def fetch_basic_data(
            self,
            api_type: Literal[APIType.USER_V3, APIType.GROUP_V1,
                              APIType.POSITION_V1, APIType.FORM_V1,
                              APIType.REQUEST_OUTLINE],
            query: str = "",
            return_on_error: bool = False,
            *,
            issue_callback: Optional[Callable[[Union[ie.JDIErrorData, iw.JDIWarningData]],
                                              None]] = None,
            progress_callback: Optional[Callable[[APIType, int, Optional[int]], None]] = None
        ) -> ApiResponse:
        """
        APIを使用して基本的なデータを取得する

        Parameters
        ----------
        api_type : APIType
            取得するデータの種類
        query : str, default ""
            クエリ文字列
            例) "?form_id=1234" (申請書データ (概要))
        return_on_error : bool, default False
            エラーが発生した場合に即座に返すかどうか
        issue_callback : func(Union[ie.JDIErrorData, iw.JDIWarningData]) -> None, optional
            エラー/警告が発生した場合に呼び出されるコールバック関数
        progress_callback : func(APIType, int, int) -> None, optional
            進捗状況を報告するコールバック関数、currentは現在の進捗、totalは総数(未知の場合はNone)
            func(api_type, current, total) -> None
        """
        url = f"{self._api_base_url[api_type]}{query}"
        page_num = 1
        if progress_callback:
            progress_callback(api_type, 0, None)

        result = ApiResponse()
        while True:
            res = self._fetch_data(url, api_type, issue_callback=issue_callback)
            if isinstance(res.error, iw.JDIWarningData):
                # 正常なレスポンスが帰ってこなかった場合
                result.error = res.error
                if return_on_error:
                    return result
                continue
            elif isinstance(res.error, ie.JDIErrorData):
                # 致命的なエラーが発生した場合
                result.error = res.error
                return result

            # 進捗状況の記録等
            res_j = res.results[0]
            result.results.extend(res_j.get("results", []))
            self._save_as_json(api_type, res_j, page = page_num)
            if progress_callback:
                progress_callback(api_type, len(result.results), res_j["count"])

            if not res_j["next"]:
                # 次のページがない場合は終了
                break
            url = res_j["next"]
            page_num += 1

        return result

    def fetch_form_outline(
            self,
            form_id: int,
            return_on_error: bool = False,
            *,
            applied_after: Optional[str] = None,
            include_canceled: bool = True,
            issue_callback: Optional[Callable[[Union[ie.JDIErrorData, iw.JDIWarningData]],
                                              None]] = None,
            progress_callback: Optional[Callable[[APIType, int, Optional[int]], None]] = None
        ) -> tuple[FormOutline, Union[ie.JDIErrorData, iw.JDIWarningData, None]]:
        """
        APIを使用して申請書(概要)データを取得する

        Parameters
        ----------
        api_type : APIType
            取得するデータの種類
        form_id : int
            申請書データのID
        return_on_error : bool, default False
            エラーが発生した場合に即座に返すかどうか
        applied_after : Optional[str], default None
            申請日時のフィルタ、指定した日時以降のデータのみ取得する。
            形式は "YYYY/MM/DD HH:MM:SS" (JST) で指定する。
            例) "2021/01/01 00:00:00"
        include_canceled : bool, default True
            取得するデータにキャンセルされたデータを含めるかどうか、APIのデフォルトはFalse
            これをFalseにした場合、独自の申請書ID (request_id) を採用している環境での通し番号の取得はできなくなる。
        issue_callback : func(Union[ie.JDIErrorData, iw.JDIWarningData]) -> None, optional
            エラー/警告が発生した場合に呼び出されるコールバック関数
        progress_callback : func(APIType, int, int) -> None, optional
            進捗状況を報告するコールバック関数、currentは現在の進捗、totalは総数(未知の場合はNone)
            func(api_type, current, total) -> None

        Returns
        -------
        FormOutline
            取得したデータ、APIのレスポンスに失敗があったかを示す `.success` と、
            取得した申請書データのIDのリスト `.ids` にのみ値が格納される
        Union[ie.JDIErrorData, iw.JDIWarningData, None]
            エラー/警告情報、エラー/警告が発生しなかった場合はNone

        Notes
        -----
        - 申請日時のフィルタは、指定した日時以降に申請されたデータ (applied_date) のみ取得する。
        - 申請日時のフィルタが指定されている場合、前回取得したデータの最終申請日時以降のデータ (final_approved_date) も取得する。
        """
        query = f"?form_id={form_id}"
        if applied_after:
            query += f"&applied_after={applied_after}"
        if include_canceled:
            query += "&include_canceled=true"

        f_outline = self.fetch_basic_data(APIType.REQUEST_OUTLINE, query=query,
                                          return_on_error=return_on_error,
                                          issue_callback=issue_callback,
                                          progress_callback=progress_callback)
        fo = FormOutline(success=f_outline.success,
                         ids= [res["id"] for res in f_outline.results]
        )
        if f_outline.error:
            return fo, f_outline.error

        if applied_after:
            # applied_afterが指定されている場合は、前回以降にキャンセルされたデータも取得する
            # NOTE: completed_after は final_approved_date に相当する
            query2 = f"?form_id={form_id}&include_canceled=true&status=canceled_after_completion" \
                     f"&completed_after={applied_after}"
            f_outline2 = self.fetch_basic_data(APIType.REQUEST_OUTLINE, query=query2,
                                               return_on_error=return_on_error,
                                               issue_callback=issue_callback,
                                               progress_callback=progress_callback)
            fo.add_ids([res["id"] for res in f_outline2.results])
            f_outline.error = f_outline2.error

        return fo, f_outline.error

    def fetch_form_detail(
            self, request_id: str, *,
            issue_callback: Optional[Callable[[Union[ie.JDIErrorData, iw.JDIWarningData]],
                                              None]] = None
        ) -> ApiResponse:
        """
        APIを使用して申請書(詳細)データを取得する

        Parameters
        ----------
        request_id : str
            申請書データのID

        Returns
        -------
        ApiResponse
            取得したデータ、APIの種類などに関わらず.json()の内容を格納する
        """
        url = f"{self._api_base_url[APIType.REQUEST_DETAIL]}{request_id}/"
        res = self._fetch_data(url, APIType.REQUEST_DETAIL, issue_callback=issue_callback)

        # JSON出力
        self._save_as_json(APIType.REQUEST_DETAIL, res.results[0], request_id=request_id)

        return res
