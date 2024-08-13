"""
This module provides temporary file I/O classes.

Classes:
    TempFileIO: Temporary file I/O class
    JobcanTempFileIO: Jobcan temporary file I/O class
"""
import json
from os import path, makedirs
import shutil



class TempFileIO:
    """Temporary file I/O class
    """
    def __init__(self, app_dir: str):
        """Constructor

        Parameters
        ----------
        app_dir : str
            Application directory path.
            All temporary files are stored under this directory.
        """
        # TODO: Rename files when temporary directory with different processing contents exist.
        self._temp_dir = path.join(app_dir, "temp")
        """Temporary directory path"""

        self._init_directories()

    def _init_directories(self):
        """Initialize directories"""
        if not path.exists(self._temp_dir):
            makedirs(self._temp_dir)

    def cleanup(self):
        """Clear temporary directory"""
        shutil.rmtree(self._temp_dir, ignore_errors=True)

class JobcanTempFileIO(TempFileIO):
    """Jobcan temporary file I/O class
    """
    def __init__(self, app_dir: str):
        """Constructor

        Parameters
        ----------
        app_dir : str
            Application directory path.
            All temporary files are stored under this directory.
        """
        super().__init__(app_dir=app_dir)
        self._form_outline_tmp_file = path.join(self._temp_dir,
                                                "form_outline_temp.json")
        """temporary file path for form outline"""

    def save_form_outline(self, data: dict):
        """Save form outline to temporary file
        """
        with open(self._form_outline_tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=None, ensure_ascii=False)

    def load_form_outline(self) -> dict:
        """Load form outline from temporary file
        """
        with open(self._form_outline_tmp_file, "r", encoding="utf-8") as f:
            return json.load(f)
