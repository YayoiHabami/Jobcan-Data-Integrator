"""
This module provides temporary file I/O classes.

Classes:
    TempFileIO: Temporary file I/O class
    JobcanTempFileIO: Jobcan temporary file I/O class
"""
import json
from os import path, makedirs, remove
import shutil
from typing import Dict, Union, Iterable



class TempFormOutline:
    """Data class for form outline (temporary)"""
    def __init__(self,
                 success: bool = False,
                 ids: Union[list[str], set[str], None] = None,
                 last_access: str = ""):
        """Constructor

        Parameters
        ----------
        success : bool
            Success flag
        ids : list[str] | set[str] | None
            list or set of request_id
        last_access : str
            Last access datetime
        """
        self.success: bool = success
        """Success flag"""
        self.ids: set[str] = set(ids) if ids else set()
        """set of request_id"""
        self.last_access: str = last_access
        """Last access datetime"""

    def add_ids(self, ids: Iterable[str]):
        """Add request_id to the set

        Parameters
        ----------
        ids : Iterable[str]
            list or set of request_id
        """
        self.ids.update(ids)

    def asdict(self, json_format: bool = False) -> dict:
        """Convert to dictionary

        Parameters
        ----------
        json_format : bool
            If True, convert to dictionary for JSON format

        Returns
        -------
        dict
            Converted dictionary
        """
        if json_format:
            return {"success": self.success,
                    "ids": list(self.ids),
                    "last_access": self.last_access}
        return {"success": self.success,
                "ids": self.ids,
                "last_access": self.last_access}

    @property
    def is_empty(self) -> bool:
        """Check if the set of request_id is empty

        Returns
        -------
        bool
            True if the set is empty, otherwise False
        """
        return not bool(self.ids)



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
        if self._remove_files():
            # If the files are removed, remove the directory
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

    def save_form_outline(self, data: Dict[int, TempFormOutline]):
        """Save form outline to temporary file

        Parameters
        ----------
        data : dict
            Form outline data.
            Key: form_id, Value: TempFormOutline
        """
        with open(self._form_outline_tmp_file, "w", encoding="utf-8") as f:
            json.dump(
                {k: v.asdict(json_format=True) for k, v in data.items()},
                f, indent=None, ensure_ascii=False
            )

    def load_form_outline(self) -> Dict[int, TempFormOutline]:
        """Load form outline from temporary file

        Returns
        -------
        dict
            Form outline data.
            Key: form_id, Value: TempFormOutline
        """
        try:
            with open(self._form_outline_tmp_file, "r", encoding="utf-8") as f:
                return {int(k): TempFormOutline(**v) for k, v in json.load(f).items()}
        except FileNotFoundError:
            return {}

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
            if all([f.is_empty for f in fo.values()]):
                try:
                    remove(self._form_outline_tmp_file)
                except FileNotFoundError:
                    pass
            else:
                s *= False

        return s
