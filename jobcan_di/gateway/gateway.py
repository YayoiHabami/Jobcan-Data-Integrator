"""
jobcan_di.gateway.gateway

ジョブカン経費精算/ワークフローAPIとの通信を行うクラスを提供する

Classes
-------
- `JobcanApiGateway`: ジョブカンAPIとの通信・DBへのデータ保存を行うクラス
"""
from copy import copy
from datetime import datetime
import sqlite3
from typing import Callable, Dict, Literal, Optional, Tuple, Union

from jobcan_di.database import (
    forms as f_io,
    group as g_io,
    positions as p_io,
    requests as r_io,
    users as u_io
)
from jobcan_di.status import (
    errors as ie,
    warnings as iw
)
from jobcan_di.status.progress import APIType
from ._core import get_unique_identifier, FormOutline
from .api_client import JobcanApiClient



class JobcanApiGateway:
    """
    ジョブカン経費精算/ワークフローAPIとの通信・データベースとの接続を行うクラス

    Usage
    -----
    1. インスタンスの作成

    ```python
    gateway = JobcanApiGateway()
    ```

    2. ジョブカンAPIとの通信に使用するトークンを設定・DBの初期化などを行う

    ```python
    err = gateway.prepare(token="your_token",
                          db_path="path/to/database.db")
    ```

    3. 終了後; データベースとの接続を切断する

    ```python
    gateway.cleanup()
    ```
    """
    def __init__(self,
                 *,
                 interval_seconds:float=0.72,
                 client:Optional[JobcanApiClient]=None) -> None:
        """コンストラクタ

        Parameters
        ----------
        interval_seconds : float, optional, default 0.72 (60*60秒/5000回)
            ジョブカンAPIとの通信間隔 (秒)
        client : JobcanApiClient, optional
            ジョブカンAPIとの通信を行うクラス
            指定された場合はこちらを優先 (interval_secondsは無視)
        """
        self._client = JobcanApiClient(interval_seconds=interval_seconds)
        """ジョブカンAPIとの通信を行うクラス"""
        self._conn: Optional[sqlite3.Connection] = None
        """データベースとの接続"""

        if client is not None:
            self.set_api_client(client)

    def set_api_client(self, api_client: JobcanApiClient):
        """
        ジョブカンAPIとの通信を行うクラスを設定する
        """
        self._client = api_client

    def update_token(self, token: str) -> Optional[ie.JDIErrorData]:
        """
        ジョブカンAPIとの通信に使用するトークンを更新する
        """
        return self._client.update_token(token)

    def init_connection(self, db_path: str) -> Optional[ie.JDIErrorData]:
        """
        データベースとの接続を初期化する
        """
        try:
            self._conn = sqlite3.connect(db_path)
        except sqlite3.Error as e:
            return ie.DatabaseConnectionFailed(e)

    def init_tables(self) -> Optional[ie.JDIErrorData]:
        """
        データベースのテーブルを初期化する
        """
        if self._conn is None:
            return ie.DatabaseConnectionNotPrepared()

        try:
            u_io.create_tables(self._conn)
            p_io.create_tables(self._conn)
            g_io.create_tables(self._conn)
            f_io.create_tables(self._conn)
            r_io.create_tables(self._conn)
        except sqlite3.Error as e:
            return ie.DatabaseTableCreationFailed(e)

        # TODO: テーブルが正しく作成されたか確認 -> ie.DatabaseTableCreationFailed

    def cleanup(self) -> None:
        """
        データベースとの接続を切断する
        """
        if isinstance(self._conn, sqlite3.Connection):
            self._conn.close()

        self._client.cleanup()

    def prepare(self, *,
                token: str,
                db_path: str) -> Optional[ie.JDIErrorData]:
        """
        本クラスの使用準備を行う

        Parameters
        ----------
        token : str
            ジョブカンAPIとの通信に使用するトークン
        db_path : str
            データベースのパス

        Notes
        -----
        - 既に設定が完了している場合も再度設定を行う
        """
        if self.is_prepared:
            self.cleanup()

        if (err:=self.update_token(token)) is not None:
            return err
        if (err:=self.init_connection(db_path)) is not None:
            return err
        if (err:=self.init_tables()) is not None:
            return err

    #
    # プロパティ
    #

    @property
    def is_connected(self) -> bool:
        """
        データベースとの接続が完了しているか
        """
        return self._conn is not None

    @property
    def is_prepared(self) -> bool:
        """
        ジョブカンAPIとの通信を行うクラスの設定が完了しているか (通信可能か)
        """
        return (self._client.is_prepared
                and self.is_connected)

    # 設定が完了していない理由のエラー
    def not_prepared_error(self) -> Optional[ie.JDIErrorData]:
        """
        設定が完了していない理由のエラー
        """
        if not self._client.is_prepared:
            return ie.ApiClientNotPrepared()
        if not self.is_connected:
            return ie.DatabaseConnectionNotPrepared()

    #
    # データベース操作
    #

    def _update_data(
            self, update_func: Callable[[sqlite3.Connection, dict], None],
            data:dict, api_type: APIType, *,
            issue_callback: Optional[Callable[[Union[ie.JDIErrorData, iw.JDIWarningData]],
                                              None]]=None
    ) -> Union[ie.JDIErrorData, iw.JDIWarningData, None]:
        """DBへデータの更新を試みる。
        一部のエラーが発生した場合、それをキャッチし`JDIErrorData`か`JDIWarningData`を返す

        Parameters
        ----------
        update_func : function
            更新処理を行う関数、引数は (conn, data)
        data : dict
            更新するデータ、APIのレスポンスの'results'内のデータなど
        api_type : APIType
            更新するデータの種類
        issue_callback : function, optional
            エラー/警告が発生した場合に呼び出されるコールバック関数

        Returns
        -------
        Union[ie.JDIErrorData, iw.JDIWarningData, None]
            エラー/警告が発生した場合はエラー/警告情報、それ以外はNone

        Notes
        -----
        - キャッチする例外は以下の通り
          - sqlite3.Error -> warning
        """
        if self._conn is None:
            return ie.DatabaseConnectionNotPrepared()

        try:
            update_func(self._conn, data)
        except sqlite3.Error as e:
            warning = iw.DBUpdateFailed(api_type, e)
            if issue_callback is not None:
                issue_callback(warning)
            return warning

        # 正常終了
        return None

    def _update_func(self,
                     api_type:Literal[APIType.USER_V3, APIType.GROUP_V1, APIType.POSITION_V1,
                                      APIType.FORM_V1]
        ) -> Callable[[sqlite3.Connection, dict], None]:
        """更新処理を返す関数を返す

        Parameters
        ----------
        api_type : APIType
            更新するデータの種類

        Returns
        -------
        function
            更新処理を行う関数、引数は (conn, data)
        """
        if api_type == APIType.USER_V3:
            return u_io.update
        elif api_type == APIType.GROUP_V1:
            return g_io.update
        elif api_type == APIType.POSITION_V1:
            return p_io.update
        elif api_type == APIType.FORM_V1:
            return f_io.update

    def update_basic_data(
            self,
            api_type: Literal[APIType.USER_V3, APIType.GROUP_V1, APIType.POSITION_V1,
                              APIType.FORM_V1],
            *,
            issue_callback: Optional[Callable[[Union[ie.JDIErrorData,
                                                     iw.JDIWarningData]], None]]=None,
            progress_callback: Optional[Callable[[APIType, int, Optional[int]], None]]=None
        ) -> Tuple[Optional[ie.JDIErrorData], bool, list[str]]:
        """基本データの取得＆更新

        Parameters
        ----------
        api_type : APIType
            取得するデータの種類
        issue_callback : func(Union[ie.JDIErrorData, iw.JDIWarningData]) -> None, optional
            エラー/警告が発生した場合に呼び出されるコールバック関数
        progress_callback : func(APIType, int, int) -> None, optional
            進捗状況を報告するコールバック関数、currentは現在の進捗、totalは総数(未知の場合はNone)
            func(api_type, current, total) -> None

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラーが発生した場合はエラー情報、それ以外はNone
        bool
            APIからのデータ取得が正常に完了したか、エラー等が発生した場合はFalse
        list[str]
            取得に失敗したデータのunique_identifierのリスト
        """
        r_suc = True # APIからのデータ取得が正常に完了したか
        u_ids = []   # 取得に失敗したデータのunique_identifierのリスト

        if not self.is_prepared:
            # 設定が完了していない
            return self.not_prepared_error(), False, u_ids

        # データをAPIから取得
        data = self._client.fetch_basic_data(
            api_type, issue_callback=issue_callback, progress_callback=progress_callback
        )
        if isinstance(data.error, ie.JDIErrorData):
            # エラーが発生した場合は処理を終了
            return data.error, False, u_ids
        elif isinstance(data.error, iw.JDIWarningData):
            # 警告が発生した場合はコールバック関数を呼び出し、処理を続行
            r_suc = False
            if issue_callback is not None:
                issue_callback(data.error)

        # 取得したデータをDBに反映
        for res in data.results:
            err = self._update_data(self._update_func(api_type),
                                    res, api_type, issue_callback=issue_callback)
            if isinstance(err, ie.JDIErrorData):
                # エラーが発生した場合は処理を終了
                return err, r_suc, u_ids
            elif isinstance(err, iw.JDIWarningData):
                # 警告が発生した場合はコールバック関数を呼び出し、処理を続行
                if issue_callback is not None:
                    issue_callback(err)
                    u_ids.append(get_unique_identifier(res, api_type))
        return None, r_suc, u_ids

    def get_form_outline(
            self,
            *,
            applied_after: Optional[Dict[int, str]] = None,
            ignore: Optional[set[str]]=None,
            issue_callback: Optional[Callable[[Union[ie.JDIErrorData,
                                                     iw.JDIWarningData]], None]]=None,
            progress_callback: Optional[Callable[[APIType, int, Optional[int], int, int],
                                                 None]]=None
        ) -> Tuple[Optional[ie.JDIErrorData], list[str], Dict[int, FormOutline]]:
        """申請書(概要)の取得＆更新

        Parameters
        ----------
        applied_after : Dict[int, str], optional
            この日時以降に申請されたデータ (および更新されたデータ) のみ取得
            キーはform_id、値の形式は "YYYY/MM/DD HH:MM:SS"
        ignore : list[str], optional
            除外するform_idのリスト
        issue_callback : func(Union[ie.JDIErrorData, iw.JDIWarningData]) -> None, optional
            エラー/警告が発生した場合に呼び出されるコールバック関数
        progress_callback : func(APIType, int, int, int, int) -> None, optional
            進捗状況を報告するコールバック関数、currentは現在の進捗、totalは総数(未知の場合はNone)、
            sub_countは処理中のform_idが何番目か、sub_totalは処理するform_idの総数
            `func(api_type, current, total, sub_count, sub_total) -> None`

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラーが発生した場合はエラー情報、それ以外はNone
        list[str]
            申請書(概要)データの取得に失敗したものが存在するform_idのリスト
            (ある種類の申請書について、対象となる全request_idを取得できた場合、そのform_idは含まれない)
        Dict[int, FormOutline]
            取得したデータのリスト

        Notes
        -----
        - progress_callback について
          - 申請書が75種類あるとし、無視する申請書(ignore)を10種類とする。このとき、`sub_total` は 65 となる。
          - 指定された条件(applied_after)により、例えば65種類中の何種類かの申請書の取得件数が0件だった場合でも、
            `sub_total` は 65 となる。
          - `sub_count` はコールバック関数呼び出し時点で何個目の申請書であるかを示す。
            例えば読み込む対象のform_idが `[1234567, 1235678, ...]` と続くときに、
            form_id が`1235678`である申請書を取得している際の `sub_count` は 2 となる。
          - `total`は指定された条件(applied_after)のもとで取得される申請書の総数を示す。
            例えば "2021/01/01 00:00:00" 以降に申請されたform_id=1235678の申請書が567件ある場合、
            `total` は 6 となる (ジョブカンのAPIでは1回のリクエストで最大100件のデータを取得するため)。
          - `current` は現在の進捗を示す。567件中300~399件目の申請書を取得している際には、`current` は 300 となる。
        """
        ignore = set() if ignore is None else ignore
        applied_after = {} if applied_after is None else applied_after
        f_ids = [] # 取得に失敗したデータのform_idのリスト
        forms: Dict[int, FormOutline] = dict() # 取得したデータのリスト

        if not self.is_prepared:
            return self.not_prepared_error(), f_ids, forms

        # 対象となるform_idを取得 (ignoreで指定されたform_idはこの時点で除外)
        ids = [id for id in f_io.retrieve_form_ids(self._conn) if str(id) not in ignore]
        if progress_callback:
            progress_callback(APIType.FORM_V1, 0, None, 0, len(ids))

        for i, form_id in enumerate(ids):
            def pgc(a:APIType, c:int, t:Optional[int], sc=i+1, st=len(ids)) -> None:
                if progress_callback:
                    progress_callback(a, c, t, sc, st)

            # 取得開始時刻を記録し、データ取得開始
            last_access = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
            f_outline, err = self._client.fetch_form_outline(
                form_id, applied_after=applied_after.get(form_id),
                issue_callback=issue_callback, progress_callback=pgc
            )
            if isinstance(err, ie.JDIErrorData):
                # エラーが発生した場合は処理を終了
                return err, f_ids, forms
            elif isinstance(err, iw.JDIWarningData):
                # 取得できなかったrequest_idがある場合、form_idを記録して処理を続行
                f_ids.append(form_id)

            # 取得したデータを記録
            if form_id not in forms:
                forms[form_id] = f_outline
            else:
                forms[form_id].add_ids(f_outline.ids)

            if f_outline.success:
                # 取得に成功した場合、最終アクセス日時を設定
                forms[form_id].last_access = last_access

        return None, f_ids, forms

    def update_form_detail(
            self,
            forms: Dict[int, FormOutline],
            *,
            ignore: Optional[set[str]]=None,
            issue_callback: Optional[Callable[[Union[ie.JDIErrorData,
                                                     iw.JDIWarningData]], None]]=None,
            progress_callback: Optional[Callable[[APIType, int, Optional[int], int, int],
                                                 None]]=None
        ) -> Tuple[Optional[ie.JDIErrorData],
                   Dict[int, set[str]], Dict[int, set[str]], Dict[int, set[str]], list[int]]:
        """申請書の詳細データの取得＆更新

        Parameters
        ----------
        forms : Dict[int, FormOutline]
            申請書(概要)のデータ、キーはform_id
            .update_form_outline() で取得したデータを指定
        ignore : set[str], optional
            除外するrequest_idのリスト
        issue_callback : func(Union[ie.JDIErrorData, iw.JDIWarningData]) -> None, optional
            エラー/警告が発生した場合に呼び出されるコールバック関数
        progress_callback : func(APIType, int, int, int, int) -> None, optional
            進捗状況を報告するコールバック関数、currentは現在の進捗、totalは総数(未知の場合はNone)、
            sub_countは処理中のform_idが何番目か、sub_totalは処理するform_idの総数
            `func(api_type, current, total, sub_count, sub_total) -> None`

        Returns
        -------
        Optional[ie.JDIErrorData]
            エラーが発生した場合はエラー情報、それ以外はNone
        Dict[int, set[str]]
            取得に失敗したデータのrequest_id、キーはform_id
        Dict[int, set[str]]
            保存に失敗したデータのrequest_id、キーはform_id
        Dict[int, set[str]]
            処理に成功したデータのrequest_id、キーはform_id
            あるrequest_idの処理中に警告が発生した場合でも、保存まで完了したものはここに含まれる
        list[int]
            処理が正常に完了した申請書のform_id
            一つ目の戻り値がNoneであればすべてのform_idが含まれるが、エラーが発生した場合は発生した
            直前のform_idまでが含まれる

        Notes
        -----
        - progress_callback について
          - formsに含まれる申請書が75種類 (キーのform_idが75個) ある場合、`sub_total` は 75 となる。
          - formsのキーが `1234567, 1235678, ...` と続くときに、form_id=1235678の申請書を取得している際の
            `sub_count` は 2 となる。
          - `total`は取得する申請書の総数を示す。例えば、form_id=1235678の申請書が567件あり、
            ignoreによる除外の総数が 100 件だった場合、`total` は 467 となる。
          - `current` は現在の進捗を示す。request_id="sa-10"の申請書が300件目である場合、`current` は 300 となる。
        """
        # 取得に失敗したデータのrequest_id、キーはform_id
        r_ids_f: Dict[int, set[str]] = {f_id: set() for f_id in forms.keys()}
        # 保存に失敗したデータのrequest_id、キーはform_id
        r_ids_d: Dict[int, set[str]] = {f_id: set() for f_id in forms.keys()}
        # 処理に成功したデータのrequest_id、キーはform_id
        r_ids_s: Dict[int, set[str]] = {f_id: set() for f_id in forms.keys()}
        # 処理が正常に完了した申請書のform_id
        suc_f_ids: list[int] = []

        if not self.is_prepared:
            return self.not_prepared_error(), r_ids_f, r_ids_d, r_ids_s, suc_f_ids

        if progress_callback:
            progress_callback(APIType.REQUEST_DETAIL, 0, None, 0, len(forms))

        for i, (form_id, f_outline) in enumerate(forms.items()):
            # 対象となるrequest_idを取得
            # 指定されたforms + 前回時点で終了していない ("in_progress", "returned") 申請書
            target_ids = copy(f_outline.ids)
            ant_stat = {r_io.RequestStatus.COMPLETED, r_io.RequestStatus.REJECTED,
                        r_io.RequestStatus.CANCELED, r_io.RequestStatus.CANCELED_AFTER_COMPLETION}
            target_ids.update(r_io.retrieve_ids(self._conn.cursor(), form_id, ant_status=ant_stat))
            if ignore: # 除外指定がある場合は除外
                target_ids -= set(ignore)

            for j, request_id in enumerate(target_ids):
                # APIにより申請書データを取得
                res = self._client.fetch_form_detail(request_id, issue_callback=issue_callback)
                if isinstance(res.error, ie.JDIErrorData):
                    return res.error, r_ids_f, r_ids_d, r_ids_s, suc_f_ids
                elif isinstance(res.error, iw.JDIWarningData):
                    r_ids_f[form_id].add(request_id)
                    continue

                # 取得したデータをDBに反映
                err = self._update_data(r_io.update, res.results[0], APIType.REQUEST_DETAIL,
                                        issue_callback=issue_callback)
                if isinstance(err, ie.JDIErrorData):
                    return err, r_ids_f, r_ids_d, r_ids_s, suc_f_ids
                elif isinstance(err, iw.JDIWarningData):
                    r_ids_d[form_id].add(request_id)

                # 処理が完了したデータのrequest_idを記録
                if progress_callback:
                    progress_callback(APIType.REQUEST_DETAIL, j+1, len(target_ids), i+1, len(forms))
                r_ids_s[form_id].add(request_id)
            # 処理が正常に完了した申請書のform_idを記録
            suc_f_ids.append(form_id)

        return None, r_ids_f, r_ids_d, r_ids_s, suc_f_ids
