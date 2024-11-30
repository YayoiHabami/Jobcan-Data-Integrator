"""
This module defines the format of the result of the data source.

Enums
-----
- SourceResultFormat: Format of the result

Constants
----------
- DEFAULT_RESULTS_KEY: Default key name corresponding to
  the list of data in the JSON object

Examples
--------
SourceResultFormat has the following formats:

- DB_FLAT_ROWS: Mainly for `SELECT *` or `SELECT key1, key2, ...` queries
- JSON_OBJECT_RESULTS: For `SELECT json_object(key1, key2, ...)` queries
- NESTED_JSON: Mainly for cases where multiple data are retrieved as a single JSON object
- MULTIPLE_JSON_ENTRIES: Mainly for cases where one JSON is retrieved per request
"""
from enum import Enum, auto
from typing import Final

DEFAULT_RESULTS_KEY: Final = "results"
"""Default key name corresponding to the list of data in the JSON object"""


class SourceResultFormat(Enum):
    """Format of the result

    Attributes
    ----------
    - DB_FLAT_ROWS : Mainly for `SELECT *` or `SELECT key1, key2, ...` queries
    - JSON_OBJECT_RESULTS : For `SELECT json_object(key1, key2, ...)` queries
    - NESTED_JSON : Mainly for cases where multiple data are retrieved as a single JSON object
    - MULTIPLE_JSON_ENTRIES : Mainly for cases where one JSON is retrieved per request
    """
    DB_FLAT_ROWS = auto()
    """DB flat rows: `list[tuple[Any, ...]]`

    - For DB: for `SELECT *` or `SELECT key1, key2, ...` queries

    Example:
    ```python
    [('1-1', '1-2', ...), ('2-1', '2-2', ...), ...]
    ```
    """
    JSON_OBJECT_RESULTS = auto()
    """JSON object results: `list[tuple[dict[str, Any]]]`

    - For DB: for `SELECT json_object(key1, key2, ...)` queries.
              Each tuple contains only one JSON object.

    Example:
    ```python
    [({'key1': '1-1', 'key2': '1-2', ...},), ...]
    ```
    """
    NESTED_JSON = auto()
    """Nested JSON: `dict[str, Any]`

    - For API: for cases where multiple data are retrieved as a single JSON object.
               The key name corresponding to the list of data is specified by `results_key`.

    Example:
    ```python
    {'results': [{'key1': '1-1', 'key2': '1-2', ...}, ...], 'other_key': ...}
    ```
    """
    MULTIPLE_JSON_ENTRIES = auto()
    """Multiple JSON entries: `list[dict[str, Any]]`

    - For API: for cases where one JSON is retrieved per request.
               Store the results of all requests in a list (`v1/requests` API, etc.)

    Example:
    ```python
    [{'key1': '1-1', 'key2': '1-2', ...}, ...]
    ```
    """
