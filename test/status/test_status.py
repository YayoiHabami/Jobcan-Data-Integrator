"""statusモジュールのテスト"""
import pytest

from jobcan_di.status.progress import (
    APIType, ProgressStatus,
    InitializingStatus, GetBasicDataStatus, GetFormOutlineStatus,
    GetFormDetailStatus, TerminatingStatus,
    get_progress_status, get_detailed_progress_status
)
from jobcan_di.status.status import (
    AppProgress, FailureRecord, FetchFailureRecord, DBSaveFailureRecord,
    JobcanDIStatus,
    merge_failure_record, merge_status
)



def test_app_progress():
    """AppProgressのテスト"""
    progress = AppProgress()
    progress.add_specifics([1, 2, 3])
    assert progress.get() == (ProgressStatus.TERMINATING, TerminatingStatus.COMPLETED)
    assert progress.is_completed() is True
    assert progress.specifics == {1, 2, 3}

    # 重複したspecificsの追加ができないことを確認
    progress.add_specifics([1, 2, 3, 4])
    assert progress.specifics == {1, 2, 3, 4}
    progress.add_specifics(1)
    assert progress.specifics == {1, 2, 3, 4}

    # 辞書形式との相互変換
    data = progress.asdict()
    new_progress = AppProgress(**data)
    assert new_progress.get() == (ProgressStatus.TERMINATING, TerminatingStatus.COMPLETED)
    assert new_progress.specifics == {1, 2, 3, 4}

    # 進捗を更新
    # 終了判定がFalseになることと、specificsがクリアされることを確認
    progress.set(ProgressStatus.INITIALIZING, InitializingStatus.COMPLETED)
    assert progress.is_completed() is False
    assert progress.specifics == set()

    # 進捗を更新
    # 更新前と同じ進捗を設定した場合、specificsが初期化されないことを確認
    new_progress.set(ProgressStatus.TERMINATING, TerminatingStatus.COMPLETED)
    assert new_progress.specifics == {1, 2, 3, 4}

class TestAppProgress:
    """AppProgressのis_future_progressメソッドのテスト"""

    @pytest.fixture
    def app_progress(self):
        """AppProgressのインスタンスを返すfixture"""
        return AppProgress(outline = ProgressStatus.BASIC_DATA,
                           detail = GetBasicDataStatus.GET_POSITION)

    def test_is_future_process_api_type(self, app_progress):
        """APITypeを指定した場合のテスト"""
        assert app_progress.is_future_process(APIType.USER_V3) is False
        assert app_progress.is_future_process(APIType.POSITION_V1) is True
        assert app_progress.is_future_process(APIType.FORM_V1) is True

    def test_is_future_process_progress_tuple(self, app_progress):
        """ProgressStatusとGetBasicDataStatusのタプルを指定した場合のテスト"""
        assert app_progress.is_future_process((ProgressStatus.BASIC_DATA,
                                               GetBasicDataStatus.GET_USER)) is False
        assert app_progress.is_future_process((ProgressStatus.BASIC_DATA,
                                               GetBasicDataStatus.GET_POSITION)) is True
        assert app_progress.is_future_process((ProgressStatus.FORM_DETAIL,
                                               GetFormDetailStatus.GET_DETAIL)) is True

    def test_is_future_process_with_specific(self, app_progress):
        """ProgressStatusとGetBasicDataStatusのタプルとspecificを指定した場合のテスト"""
        app_progress.add_specifics(["user1", "user2"])
        assert app_progress.is_future_process((ProgressStatus.BASIC_DATA,
                                               GetBasicDataStatus.GET_POSITION),
                                              specific="user1") is False
        assert app_progress.is_future_process((ProgressStatus.BASIC_DATA,
                                               GetBasicDataStatus.GET_POSITION),
                                              specific="user3") is True

    @pytest.mark.parametrize("outline,detail,specifics,progress,specific,expected", [
        (   # 処理済み1
            ProgressStatus.INITIALIZING, InitializingStatus.LOADING_CONFIG, [],
            APIType.USER_V3, None, True
        ),
        (   # 処理済み2
            ProgressStatus.BASIC_DATA, GetBasicDataStatus.GET_USER, [],
            APIType.GROUP_V1, None, True
        ),
        (   # 処理中 (specificsなし) -> 処理中
            ProgressStatus.FORM_OUTLINE, GetFormOutlineStatus.GET_OUTLINE, [],
            APIType.REQUEST_OUTLINE, None, True
        ),
        (   # 処理中 (specificsあり、specific指定なし) -> 処理中
            ProgressStatus.FORM_OUTLINE, GetFormOutlineStatus.GET_OUTLINE, [1, 2, 3],
            APIType.REQUEST_OUTLINE, None, True
        ),
        (   # 処理中 (specificsあり、specific指定ありかつ一致) -> 処理済み
            ProgressStatus.FORM_OUTLINE, GetFormOutlineStatus.GET_OUTLINE, [1, 2, 3],
            APIType.REQUEST_OUTLINE, 1, False
        ),
        (   # 処理中 (specificsあり、specific指定ありかつ不一致) -> 未処理/処理中
            ProgressStatus.FORM_OUTLINE, GetFormOutlineStatus.GET_OUTLINE, [1, 2, 3],
            APIType.REQUEST_OUTLINE, 5, True
        ),
        (   # 未処理
            ProgressStatus.TERMINATING, TerminatingStatus.COMPLETED, [],
            APIType.FORM_V1, None, False
        ),
    ])
    def test_is_future_process_various_states(self, outline, detail, specifics,
                                              progress, specific, expected):
        """様々な状態でspecificを指定した/しなかった場合のテスト
        主にAPITypeとの兼ね合いを確認する"""
        app_progress = AppProgress(outline=outline, detail=detail, specifics=specifics)
        assert app_progress.is_future_process(progress, specific=specific) is expected

def test_fetch_failure_record():
    """FetchFailureRecordのテスト"""
    record = FetchFailureRecord()

    # 基本データの追加と取得のテスト
    assert record.is_failed(APIType.GROUP_V1) is False
    record.is_failed(APIType.GROUP_V1, True)
    assert record.is_failed(APIType.GROUP_V1) is True
    record.add(APIType.USER_V3, "123")
    assert record.get(APIType.USER_V3) == {"123"}

    # 申請書詳細の追加と取得のテスト
    record.add(APIType.REQUEST_DETAIL, "456", form_id=789)
    assert record.get(APIType.REQUEST_DETAIL, form_id=789) == {"456"}
    # 同一のform_idに複数のデータを追加した場合、取得時に結合されることを確認
    record.add(APIType.REQUEST_DETAIL, "789", form_id=789)
    assert record.get(APIType.REQUEST_DETAIL, form_id=789) == {"456", "789"}
    # 同一のform_idに同一のデータを追加した場合でも重複しないことを確認
    record.add(APIType.REQUEST_DETAIL, "456", form_id=789)
    assert record.get(APIType.REQUEST_DETAIL, form_id=789) == {"456", "789"}


    # asdict()メソッドのテスト
    expected_dict = {
        'basic_data': {v.name: set() for v in APIType if v != APIType.REQUEST_DETAIL},
        'request_detail': {789: {'456', '789'}}
    }
    expected_dict["basic_data"][APIType.USER_V3.name] = {'123'}
    expected_dict["basic_data"][APIType.GROUP_V1.name] = {""}
    print(expected_dict)
    print(record.asdict())
    assert record.asdict() == expected_dict

    # 辞書からの復元テスト
    record2 = FetchFailureRecord(**record.asdict())
    assert record2.asdict() == expected_dict

    # clearメソッドのテスト
    record.clear()
    assert record.get(APIType.USER_V3) == set()
    assert record.get_request_detail() == {}

def test_jobcan_di_status(tmp_path):
    """JobcanDIStatusのテスト"""
    status = JobcanDIStatus(str(tmp_path))

    # 初期状態の確認
    assert status.progress.get() == (ProgressStatus.INITIALIZING, None)
    expected_dict = {
        'basic_data': {v.name: set() for v in APIType if v != APIType.REQUEST_DETAIL},
        'request_detail': {}
    }
    assert status.fetch_failure_record.asdict() == expected_dict
    assert status.form_api_last_access == {}

    # データの設定
    status.progress.set(ProgressStatus.INITIALIZING, InitializingStatus.COMPLETED)
    status.progress.add_specifics([1, 2, 3])
    status.fetch_failure_record.add(APIType.USER_V3, "123")
    status.fetch_failure_record.add(APIType.USER_V3, "123")
    status.fetch_failure_record.add(APIType.USER_V3, "456")
    last_access = {1: "2021/01/01 00:00:00", 2: "2021-01-02T00:00:00"}
    status.form_api_last_access = last_access

    # 保存と読み込みのテスト
    status.save()
    new_status = JobcanDIStatus(str(tmp_path))
    new_status.load()

    assert new_status.progress.get() == (ProgressStatus.INITIALIZING,
                                         InitializingStatus.COMPLETED)
    assert new_status.progress.specifics == {1, 2, 3}
    assert new_status.fetch_failure_record.get(APIType.USER_V3) == {"123", "456"}
    assert new_status.form_api_last_access == last_access

    # 保存と読み込みのテスト (前回保存時に最後まで実行された場合、進捗を初期化)
    status.progress.set(ProgressStatus.TERMINATING, TerminatingStatus.COMPLETED)
    status.save()
    new_status.load()
    assert new_status.progress.get() == (ProgressStatus.INITIALIZING, None)
    assert new_status.progress.specifics == set()

def test_fetch_failure_record_errors():
    """FetchFailureRecordのエラーケースのテスト"""
    record = FetchFailureRecord()

    # REQUEST_DETAILにform_idなしで追加しようとするとエラー
    with pytest.raises(ValueError):
        record.add(APIType.REQUEST_DETAIL, "456")

    # REQUEST_DETAILからform_idなしで取得しようとするとエラー
    with pytest.raises(ValueError):
        record.get(APIType.REQUEST_DETAIL)

@pytest.fixture
def failure_record_prev():
    """古い方のFetchFailureRecordのインスタンスを返すfixture"""
    fr = {
        "basic_data": {
            "USER_V3": {"1", "2", "3"},
            "GROUP_V1": {"1", "2", "3"},
            "POSITION_V1": {"1", "2", "3"},
            "FORM_V1": {"1", "2", "3"},
            "REQUEST_OUTLINE": {"1", "2", "3"},
        },
        "request_detail": {
            "789": {"1", "2", "3"},
            "123": {"1", "2", "3"},
        }
    }
    return FailureRecord(**fr)

@pytest.fixture
def failure_record_new():
    """新しい方のFetchFailureRecordのインスタンスを返すfixture"""
    fr = {
        "basic_data": {
            "USER_V3": {"1", "3", "5"},
            "GROUP_V1": {"1", "3", "5"},
            "POSITION_V1": {"1", "3", "5"},
            "FORM_V1": {"1", "3", "5"},
            "REQUEST_OUTLINE": {"1", "3", "5"},
        },
        "request_detail": {
            "789": {"1", "3", "5"},
            "123": {"1", "3", "5"},
        }
    }
    return FailureRecord(**fr)

@pytest.mark.parametrize("api_type", [
    APIType.USER_V3, APIType.GROUP_V1, APIType.POSITION_V1, APIType.FORM_V1,
    APIType.REQUEST_OUTLINE, APIType.REQUEST_DETAIL, None
])
def test_merge_failure_record(failure_record_prev, failure_record_new, api_type):
    """FailureRecordのマージのテスト

    - api_typeは現在の進捗、Noneの場合は最も進んでいる進捗を基準とする"""
    if api_type is not None:
        ap = AppProgress(outline = get_progress_status(api_type),
                         detail = get_detailed_progress_status(api_type))
    else:
        # api_typeがNoneの場合、進捗が最も進んでいるものを基準とする
        ap = AppProgress(outline = ProgressStatus.TERMINATING,
                         detail = TerminatingStatus.COMPLETED)

    merged = merge_failure_record(failure_record_prev, failure_record_new,
                                   FailureRecord(), ap)

    for at in APIType:
        if at == APIType.REQUEST_DETAIL:
            if api_type is None or api_type.value > at.value:
                # 進捗がREQUEST_DETAIL以降の場合、newのデータが優先される
                assert merged.get(at, form_id=123) == {"1", "3", "5"}
                assert merged.get(at, form_id=789) == {"1", "3", "5"}
            else:
                # 進捗がREQUEST_DETAIL以前の場合、prevとnewのデータが結合される
                assert merged.get(at, form_id=123) == {"1", "2", "3", "5"}
                assert merged.get(at, form_id=789) == {"1", "2", "3", "5"}
        else:
            if api_type is None or api_type.value > at.value:
                # 進捗(api_type)よりも前の要素の場合、newのデータが優先される
                assert merged.get(at) == {"1", "3", "5"}
            else:
                # 進捗(api_type)よりも後の要素の場合、prevとnewのデータが結合される
                assert merged.get(at) == {"1", "2", "3", "5"}

def test_merge_status(failure_record_prev, failure_record_new):
    """merge_statusのテスト"""
    # 古い方のステータス
    prev = JobcanDIStatus("prev-test")
    prev.fetch_failure_record = FetchFailureRecord(**failure_record_prev.asdict())
    prev.db_save_failure_record = DBSaveFailureRecord(**failure_record_prev.asdict())
    prev.progress = AppProgress(outline=ProgressStatus.BASIC_DATA,
                                detail=GetBasicDataStatus.GET_USER)
    prev.form_api_last_access = {1: "2021/01/01 00:00:00",
                                 3: "2021/01/03 00:00:00",
                                 4: "2021/01/04 00:00:00"}
    prev.config_file_path = "prev-config"

    # 新しい方のステータス
    new = JobcanDIStatus("new-test")
    new.fetch_failure_record = FetchFailureRecord(**failure_record_new.asdict())
    new.db_save_failure_record = DBSaveFailureRecord(**failure_record_new.asdict())
    new.progress = AppProgress(outline=ProgressStatus.BASIC_DATA,
                               detail=GetBasicDataStatus.GET_GROUP)
    new.form_api_last_access = {2: "2021/01/02 00:00:00",
                                3: "2021/01/01 00:00:00"}
    new.config_file_path = "new-config"

    # マージ
    merged = merge_status(new, prev)

    # failure_recordについてはmerge_failure_recordのテストと同様の結果となることを確認
    for at in APIType:
        if at == APIType.REQUEST_DETAIL:
            if APIType.GROUP_V1.value > at.value:
                assert merged.fetch_failure_record.get(at, form_id=123) == {"1", "3", "5"}
                assert merged.fetch_failure_record.get(at, form_id=789) == {"1", "3", "5"}
            else:
                assert merged.fetch_failure_record.get(at, form_id=123) == {"1", "2", "3", "5"}
                assert merged.fetch_failure_record.get(at, form_id=789) == {"1", "2", "3", "5"}
        else:
            if APIType.GROUP_V1.value > at.value:
                assert merged.fetch_failure_record.get(at) == {"1", "3", "5"}
            else:
                assert merged.fetch_failure_record.get(at) == {"1", "2", "3", "5"}

    # form_api_last_accessについては各要素について日時が最新のものが選択されることを確認
    # 例えばnewの方の日時が古ければprevの日時が選択され、new/prevの片方にしかない要素はそのまま残る
    assert merged.form_api_last_access == {1: "2021/01/01 00:00:00",
                                           2: "2021/01/02 00:00:00",
                                           3: "2021/01/03 00:00:00",
                                           4: "2021/01/04 00:00:00"}

    # その他についてはnewのデータが優先されることを確認
    assert merged.progress.get() == (ProgressStatus.BASIC_DATA, GetBasicDataStatus.GET_GROUP)
    assert merged.config_file_path == "new-config"
