"""
Module for managing app status

Classes
-------
- `ConfigEditorGuiStatus` : Class for managing app status
"""
import json
from os import path



class ConfigEditorGuiStatus:
    """Class for managing app status

    Attributes
    ----------
    status_path : str
        Path to app status file
    geometry : str
        Geometry of the window
    appearance_mode : str
        Appearance mode of the app
    scaling : str
        Scaling of the app
    num_columns : str
        Number of columns in the app
    """

    def __init__(self, status_path:str):
        """Create ConfigEditorGuiStatus instance

        Args
        ----
        path : str
            Path to app status file"""
        self.status_path = status_path
        if path.exists(status_path):
            self.load()
            return

        # Init status (If status file does not exist)
        self.geometry = "1500x800"
        self.appearance_mode = "Light"
        self.scaling = "100%"
        self.num_columns = "2"
        self.config_path = ""

    def load(self):
        """Load status from file"""
        with open(self.status_path, "r", encoding='utf-8') as f:
            data = json.load(f)
            self.geometry = data["geometry"]
            self.appearance_mode = data["appearanceMode"]
            self.scaling = data["scaling"]
            self.num_columns = data["numColumns"]
            self.config_path = data["configPath"]

    def save(self):
        """Save status to file"""
        data = {
            "geometry": self.geometry,
            "appearanceMode": self.appearance_mode,
            "scaling": self.scaling,
            "numColumns": self.num_columns,
            "configPath": self.config_path
        }
        with open(self.status_path, "w", encoding='utf-8') as f:
            json.dump(data, f)
