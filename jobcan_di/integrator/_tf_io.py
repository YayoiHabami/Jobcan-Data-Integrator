"""
This module provides temporary file I/O classes.

Classes:
    TempDataIO: Temporary data I/O class
    JobcanTempDataIO: Jobcan temporary data I/O class

Notes:
    If `prioritize_memory` is True, the data is stored in memory and not saved to files.
"""
import json
from os import path, makedirs, remove
import shutil
from typing import Dict, Optional

from jobcan_di.gateway import FormOutline



class TempDataIO:
    """Temporary file I/O class
    """
    def __init__(self, app_dir: str, *, prioritize_memory: bool = False):
        """Constructor

        Parameters
        ----------
        app_dir : str
            Application directory path.
            All temporary files are stored under this directory.
        prioritize_memory : bool
            If True, prioritize memory over files (i.e. do not save to files).
        """
        # TODO: Rename files when temporary directory with different processing contents exist.
        self._temp_dir = path.join(app_dir, "temp")
        """Temporary directory path"""

        self._prioritize_memory = prioritize_memory
        """Prioritize memory over files"""
        self._raw_data: Dict[str, Optional[dict]] = {}
        """Raw data. The key is the file name.
        If prioritize_memory is True or the temporary file is not available, use this data"""

        self._init_directories()

    def _init_directories(self):
        """Initialize directories"""
        if not path.exists(self._temp_dir):
            makedirs(self._temp_dir)

    def _save_files(self, data: dict, file_name: str):
        """Save data to a file

        Parameters
        ----------
        data : dict
            Data to save. The data should be JSON serializable.
        file_name : str
            File name
        """
        if self._prioritize_memory:
            # If prioritize_memory is True, save the data to memory
            self._raw_data[file_name] = data
            return

        try:
            with open(path.join(self._temp_dir, file_name), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=None, ensure_ascii=False)
            self._raw_data[file_name] = None
        except OSError:
            self._raw_data[file_name] = data

    def _load_files(self, file_name: str) -> dict:
        """Load data from a file

        Parameters
        ----------
        file_name : str
            File name

        Returns
        -------
        dict
            Loaded data. {} if the file does not exist
        """
        if self._prioritize_memory:
            # If prioritize_memory is True, return the data in memory
            return self._raw_data.get(file_name, dict())

        try:
            with open(path.join(self._temp_dir, file_name), "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return dict()
        except OSError:
            return self._raw_data.get(file_name, dict())

    def _remove_files(self) -> bool:
        """Remove temporary files if they are in the initial state

        Returns
        -------
        bool
            True if the files are removed, otherwise False
        """
        return True

    def cleanup(self):
        """Clear temporary directory"""
        if self._remove_files() or self._prioritize_memory:
            # If the files are removed or not used, remove the directory
            shutil.rmtree(self._temp_dir, ignore_errors=True)

class JobcanTempDataIO(TempDataIO):
    """Jobcan temporary file I/O class
    """
    def __init__(self, app_dir: str, *, prioritize_memory: bool = False):
        """Constructor

        Parameters
        ----------
        app_dir : str
            Application directory path.
            All temporary files are stored under this directory.
        prioritize_memory : bool
            If True, prioritize memory over files (i.e. do not save to files).
        """
        super().__init__(app_dir=app_dir, prioritize_memory=prioritize_memory)
        self._form_outline_tmp_file = "form_outline_temp.json"
        """temporary file name for form outline"""

    def save_form_outline(self, data: Dict[int, FormOutline]):
        """Save form outline to temporary file

        Parameters
        ----------
        data : dict
            Form outline data.
            Key: form_id, Value: FormOutline
        """
        j_data = {k: v.asdict(json_format=True) for k, v in data.items()}
        self._save_files(j_data, self._form_outline_tmp_file)


    def load_form_outline(self) -> Dict[int, FormOutline]:
        """Load form outline from temporary file

        Returns
        -------
        dict
            Form outline data.
            Key: form_id, Value: FormOutline
        """
        j_data = self._load_files(self._form_outline_tmp_file)

        return {int(k): FormOutline(**v) for k, v in j_data.items()}

    def _remove_files(self):
        """Remove temporary files if they are in the initial state

        Returns
        -------
        bool
            True if the files are removed, otherwise False
        """
        s = super()._remove_files()

        # form outline
        if (fo := self.load_form_outline()):
            # If the form outline is empty, remove the file
            if all([f.is_empty for f in fo.values()]) and not self._prioritize_memory:
                try:
                    remove(self._form_outline_tmp_file)
                except FileNotFoundError:
                    pass
            else:
                s *= False

        return s
