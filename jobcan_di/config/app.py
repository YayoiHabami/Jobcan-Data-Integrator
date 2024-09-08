"""
This module is the entry point for the application. It creates the main window
"""
import ctypes
import os
from os import path
import sys

from gui.config_editor_gui import ConfigEditorGui



try:
    if sys.platform.startswith('win'):
        # Set DPI awareness (for high DPI displays)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    print("Failed to set DPI awareness")



if __name__ == "__main__":
    icon_dir = path.join(os.getcwd(), "resources/icons")
    if not path.exists(icon_dir):
        icon_dir = path.join(path.dirname(__file__), "resources/icons")
    app = ConfigEditorGui(icon=path.join(icon_dir, "setting48.ico"))
    app.mainloop()
