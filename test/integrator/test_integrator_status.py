import pytest

from integrator.progress_status import (
    APIType,
    ProgressStatus,
    InitializingStatus, TerminatingStatus
)
from integrator.integrator_status import AppProgress, FetchFailureRecord, JobcanDIStatus



# AppProgressのテスト
def test_app_progress():
    progress = AppProgress()
    progress.add_specifics([1, 2, 3])
    assert progress.get() == (ProgressStatus.TERMINATING, TerminatingStatus.COMPLETED)
    assert progress.is_completed() is True
    assert progress.specifics == [1, 2, 3]

    # 辞書形式との相互変換
    data = progress.asdict()
    new_progress = AppProgress(**data)
    assert new_progress.get() == (ProgressStatus.TERMINATING, TerminatingStatus.COMPLETED)
    assert new_progress.specifics == [1, 2, 3]

    # 進捗を更新
    # 終了判定がFalseになることと、specificsがクリアされることを確認
    progress.set(ProgressStatus.INITIALIZING, InitializingStatus.COMPLETED)
    assert progress.is_completed() is False
    assert progress.specifics == []

    # 進捗を更新
    # 更新前と同じ進捗を設定した場合、specificsが初期化されないことを確認
    new_progress.set(ProgressStatus.TERMINATING, TerminatingStatus.COMPLETED)
    assert new_progress.specifics == [1, 2, 3]

# FetchFailureRecordのテスト
def test_fetch_failure_record():
    record = FetchFailureRecord()

    # 基本データの追加と取得のテスト
    record.add(APIType.USER_V3, "123")
    assert record.get(APIType.USER_V3) == ["123"]

    # 申請書詳細の追加と取得のテスト
    record.add(APIType.REQUEST_DETAIL, "456", form_id=789)
    assert record.get(APIType.REQUEST_DETAIL, form_id=789) == ["456"]

    # asdict()メソッドのテスト
    expected_dict = {
        'basic_data': {v.name: [] for v in APIType if v != APIType.REQUEST_DETAIL},
        'request_detail': {789: ['456']}
    }
    expected_dict["basic_data"][APIType.USER_V3.name] = ['123']
    print(expected_dict)
    print(record.asdict())
    assert record.asdict() == expected_dict

    # 辞書からの復元テスト
    record2 = FetchFailureRecord(**record.asdict())
    assert record2.asdict() == expected_dict

    # clearメソッドのテスト
    record.clear()
    assert record.get(APIType.USER_V3) == []
    assert record.get_request_detail() == {}

# JobcanDIStatusのテスト
def test_jobcan_di_status(tmp_path):
    status = JobcanDIStatus(str(tmp_path))

    # 初期状態の確認
    assert status.progress.get() == (ProgressStatus.INITIALIZING, None)
    expected_dict = {
        'basic_data': {v.name: [] for v in APIType if v != APIType.REQUEST_DETAIL},
        'request_detail': {}
    }
    assert status.fetch_failure_record.asdict() == expected_dict
    assert status.form_api_last_access == {}

    # データの設定
    status.progress.set(ProgressStatus.INITIALIZING, InitializingStatus.COMPLETED)
    status.progress.add_specifics([1, 2, 3])
    status.fetch_failure_record.add(APIType.USER_V3, "123")
    last_access = {1: "2021-01-01T00:00:00", 2: "2021-01-02T00:00:00"}
    status.form_api_last_access = last_access

    # 保存と読み込みのテスト
    status.save()
    new_status = JobcanDIStatus(str(tmp_path))
    new_status.load()

    assert new_status.progress.get() == (ProgressStatus.INITIALIZING,
                                         InitializingStatus.COMPLETED)
    assert new_status.progress.specifics == [1, 2, 3]
    assert new_status.fetch_failure_record.get(APIType.USER_V3) == ["123"]
    assert new_status.form_api_last_access == last_access

    # 保存と読み込みのテスト (前回保存時に最後まで実行された場合、進捗を初期化)
    status.progress.set(ProgressStatus.TERMINATING, TerminatingStatus.COMPLETED)
    status.save()
    new_status.load()
    assert new_status.progress.get() == (ProgressStatus.INITIALIZING, None)
    assert new_status.progress.specifics == []

# エラーケースのテスト
def test_fetch_failure_record_errors():
    record = FetchFailureRecord()

    # REQUEST_DETAILにform_idなしで追加しようとするとエラー
    with pytest.raises(ValueError):
        record.add(APIType.REQUEST_DETAIL, "456")

    # REQUEST_DETAILからform_idなしで取得しようとするとエラー
    with pytest.raises(ValueError):
        record.get(APIType.REQUEST_DETAIL)
