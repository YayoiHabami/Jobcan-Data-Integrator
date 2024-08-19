"""
Test for integrator._tf_io.py
"""
import os
from shutil import rmtree
from tempfile import mkdtemp

import pytest

# Assuming the module is named temp_file_io.py
from integrator._tf_io import TempFormOutline, TempFileIO, JobcanTempFileIO



class TestTempFormOutline:
    def test_init(self):
        form = TempFormOutline(success=True, ids=["1", "2"], last_access="2024-08-19")
        assert form.success is True
        assert form.ids == {"1", "2"}
        assert form.last_access == "2024-08-19"

    def test_add_ids(self):
        form = TempFormOutline()
        form.add_ids(["1", "2"])
        form.add_ids(["2", "3"])
        assert form.ids == {"1", "2", "3"}

    def test_asdict(self):
        form = TempFormOutline(success=True, ids=["1", "2"], last_access="2024-08-19")
        assert form.asdict() == {
            "success": True,
            "ids": {"1", "2"},
            "last_access": "2024-08-19"
        }
        fj = form.asdict(json_format=True)
        assert fj["success"] is True
        assert len(fj["ids"]) == 2
        assert set(fj["ids"]) == set(["1", "2"])
        assert fj["last_access"] == "2024-08-19"

    def test_is_empty(self):
        form = TempFormOutline()
        assert form.is_empty is True
        form.add_ids(["1"])
        assert form.is_empty is False

class TestTempFileIO:
    @pytest.fixture
    def temp_dir(self):
        tmp_dir = mkdtemp()
        yield tmp_dir
        rmtree(tmp_dir)

    def test_init(self, temp_dir):
        _ = TempFileIO(temp_dir)
        assert os.path.exists(os.path.join(temp_dir, "temp"))

    def test_cleanup(self, temp_dir):
        io = TempFileIO(temp_dir)
        io.cleanup()
        assert not os.path.exists(os.path.join(temp_dir, "temp"))

class TestJobcanTempFileIO:
    @pytest.fixture
    def temp_dir(self):
        tmp_dir = mkdtemp()
        yield tmp_dir
        rmtree(tmp_dir)

    @pytest.fixture
    def jobcan_io(self, temp_dir):
        return JobcanTempFileIO(temp_dir)

    def test_save_load_form_outline(self, jobcan_io):
        data = {
            1: TempFormOutline(success=True, ids=["1", "2"], last_access="2024-08-19"),
            2: TempFormOutline(success=False, ids=["3", "4"], last_access="2024-08-20")
        }
        jobcan_io.save_form_outline(data)

        loaded_data = jobcan_io.load_form_outline()
        assert len(loaded_data) == 2
        assert loaded_data[1].success is True
        assert loaded_data[1].ids == {"1", "2"}
        assert loaded_data[1].last_access == "2024-08-19"
        assert loaded_data[2].success is False
        assert loaded_data[2].ids == {"3", "4"}
        assert loaded_data[2].last_access == "2024-08-20"

    def test_cleanup(self, jobcan_io, temp_dir):
        assert os.path.exists(os.path.join(temp_dir, "temp"))

        # ファイルのデータが空でない場合、ディレクトリは削除されない
        jobcan_io.save_form_outline({1: TempFormOutline(ids=["1"])})
        jobcan_io.cleanup()
        assert os.path.exists(os.path.join(temp_dir, "temp"))

        # ファイルのデータが空の場合、ディレクトリが削除される
        jobcan_io.save_form_outline({1: TempFormOutline()})
        jobcan_io.cleanup()
        assert not os.path.exists(os.path.join(temp_dir, "temp"))

if __name__ == "__main__":
    pytest.main()