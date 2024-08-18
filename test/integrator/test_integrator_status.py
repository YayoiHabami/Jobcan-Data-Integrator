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
    assert progress.status_outline == ProgressStatus.TERMINATING
    assert progress.status_detail == TerminatingStatus.COMPLETED
    assert progress.is_completed() == True

    progress.status_detail = InitializingStatus.COMPLETED
    assert progress.is_completed() == False

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
    assert status.progress.status_outline == ProgressStatus.TERMINATING
    assert status.progress.status_detail == TerminatingStatus.COMPLETED
    expected_dict = {
        'basic_data': {v.name: [] for v in APIType if v != APIType.REQUEST_DETAIL},
        'request_detail': {}
    }
    assert status.fetch_failure_record.asdict() == expected_dict

    # データの設定
    status.progress.status_outline = ProgressStatus.INITIALIZING
    status.progress.status_detail = InitializingStatus.COMPLETED
    status.fetch_failure_record.add(APIType.USER_V3, "123")

    # 保存と読み込みのテスト
    status.save()
    new_status = JobcanDIStatus(str(tmp_path))
    new_status.load()

    assert new_status.progress.status_outline == ProgressStatus.INITIALIZING
    assert new_status.progress.status_detail == InitializingStatus.COMPLETED
    assert new_status.fetch_failure_record.get(APIType.USER_V3) == ["123"]

# エラーケースのテスト
def test_fetch_failure_record_errors():
    record = FetchFailureRecord()

    # REQUEST_DETAILにform_idなしで追加しようとするとエラー
    with pytest.raises(ValueError):
        record.add(APIType.REQUEST_DETAIL, "456")

    # REQUEST_DETAILからform_idなしで取得しようとするとエラー
    with pytest.raises(ValueError):
        record.get(APIType.REQUEST_DETAIL)
