import pytest

from integrator.progress_status import (
    APIType, ProgressStatus,
    InitializingStatus, GetBasicDataStatus, GetFormOutlineStatus,
    GetFormDetailStatus, TerminatingStatus, ErrorStatus
)
from integrator.integrator_status import AppProgress, FetchFailureRecord, JobcanDIStatus



# AppProgressのテスト
def test_app_progress():
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

# AppProgressのテスト (.is_future_processメソッド)
class TestAppProgress:

    @pytest.fixture
    def app_progress(self):
        return AppProgress(outline = ProgressStatus.BASIC_DATA,
                           detail = GetBasicDataStatus.GET_POSITION)

    def test_is_future_process_api_type(self, app_progress):
        assert app_progress.is_future_process(APIType.USER_V3) is False
        assert app_progress.is_future_process(APIType.POSITION_V1) is True
        assert app_progress.is_future_process(APIType.FORM_V1) is True

    def test_is_future_process_progress_tuple(self, app_progress):
        assert app_progress.is_future_process((ProgressStatus.BASIC_DATA,
                                               GetBasicDataStatus.GET_USER)) is False
        assert app_progress.is_future_process((ProgressStatus.BASIC_DATA,
                                               GetBasicDataStatus.GET_POSITION)) is True
        assert app_progress.is_future_process((ProgressStatus.FORM_DETAIL,
                                               GetFormDetailStatus.GET_DETAIL)) is True

    def test_is_future_process_with_specific(self, app_progress):
        app_progress.add_specifics(["user1", "user2"])
        assert app_progress.is_future_process((ProgressStatus.BASIC_DATA,
                                               GetBasicDataStatus.GET_POSITION),
                                              specific="user1") is False
        assert app_progress.is_future_process((ProgressStatus.BASIC_DATA,
                                               GetBasicDataStatus.GET_POSITION),
                                              specific="user3") is True

    def test_is_future_process_error_cases(self, app_progress):
        assert app_progress.is_future_process((ProgressStatus.FAILED,
                                               ErrorStatus.UNKNOWN_ERROR)) is False
        app_progress.set(ProgressStatus.FAILED, ErrorStatus.UNKNOWN_ERROR)
        assert app_progress.is_future_process(APIType.USER_V3) is False

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
        app_progress = AppProgress(outline=outline, detail=detail, specifics=specifics)
        assert app_progress.is_future_process(progress, specific=specific) is expected

# FetchFailureRecordのテスト
def test_fetch_failure_record():
    record = FetchFailureRecord()

    # 基本データの追加と取得のテスト
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

# JobcanDIStatusのテスト
def test_jobcan_di_status(tmp_path):
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
    last_access = {1: "2021-01-01T00:00:00", 2: "2021-01-02T00:00:00"}
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

# エラーケースのテスト
def test_fetch_failure_record_errors():
    record = FetchFailureRecord()

    # REQUEST_DETAILにform_idなしで追加しようとするとエラー
    with pytest.raises(ValueError):
        record.add(APIType.REQUEST_DETAIL, "456")

    # REQUEST_DETAILからform_idなしで取得しようとするとエラー
    with pytest.raises(ValueError):
        record.get(APIType.REQUEST_DETAIL)
