"""
Base classes and functions for GUI components.

Classes
-------
- `ValidationType` : Validation type for ConfigVariableFrame
- `TextType` : Text type for ConfigEditorGui

Functions
---------
- `get_display_width` : Get display width for a character. East Asian characters are counted as 2.
- `count_text_width` : Count text width for display. East Asian characters are counted as 2.
- `is_ascii_only` : Check if the text is ASCII only

Constants
---------
- `EN_FONT_NAME` : Font name for English text
- `JP_FONT_NAME` : Font name for Japanese text
"""
from enum import Enum, auto
import unicodedata



EN_FONT_NAME = "Segoe UI"
JP_FONT_NAME = "游ゴシック"



#
# Enum classes
#

class ValidationType(Enum):
    """Validation type for ConfigVariableFrame"""
    SAVED = auto()
    OK = auto()
    INVALID_TYPE = auto()
    OUT_OF_RANGE = auto()

class TextType(Enum):
    """Text type for ConfigEditorGui"""
    PLAIN = auto()
    TITLE = auto()
    SUBTITLE = auto()



#
# Functions
#

def get_display_width(char:str):
    """Get display width for a character. East Asian characters are counted as 2."""
    return 2 if unicodedata.east_asian_width(char) in {'F', 'W', 'A'} else 1

def count_text_width(text:str):
    """Count text width for display. East Asian characters are counted as 2."""
    return sum(map(get_display_width, text))

def is_ascii_only(text):
    """Check if the text is ASCII only"""
    return all(ord(c) < 128 for c in text)
