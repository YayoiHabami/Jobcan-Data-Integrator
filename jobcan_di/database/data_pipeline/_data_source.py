"""
Data source for the data pipeline

Classes
-------
- DataSource: Data source for the data pipeline
- APIDataSource: API data source
- DBDataSource: Database data source
- RawDataSource: Data source holding raw data
"""
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Union

from jobcan_di.database.schema_toolkit import SQLDialect
from ._source_result_format import SourceResultFormat

UnitOfResult = Union[dict[str, Any], tuple[Any, ...]]
"""Type alias for the unit of the result

Details
-------
In this program, as a preprocessing step in the data transformation
(ETL Transform) stage, the format of a single unit of data is standardized.
A single unit of data is assumed to be an object that essentially
consists of multiple elements in JSON format, specifically as
`dict[str, Any]` or `tuple[str, Any]`. For example, if information about
one user can be obtained as a single unit, it would be like:

- `{"userId": 12345, "userName": "John Doe", ...}`
- `[12345, "John Doe", ...]`

Such data is obtained as a single unit. In this program,
the data extraction process (ETL Extract) is performed by
the `extract_data` method of the `DataSource` class
(and its subclasses). Therefore, the result of the extraction process
is a list of single units (`list[UnitOfResult]`), and these are used
as input for the transformation process.
"""

class DataSource(ABC):
    """Data source for the data pipeline
    (Base class for API and database data sources)

    Attributes
    ----------
    name : str
        Name of the data source
    ttype : str
        Type of the data source
    result_format : SourceResultFormat
        Format of the result (multiple-results, single-result, ...)
    results_key : str
        Key name corresponding to the list of data in the JSON object.
        For `SourceResultFormat.NESTED_JSON` (Other formats ignore this attribute)
    """
    ttype: ClassVar[str] = ""

    def __init__(self, name: str, result_format: SourceResultFormat, results_key: str):
        self.name = name
        """Name of the data source"""
        self.result_format = result_format
        """Format of the result (multiple-results, single-result, ...)"""
        self.results_key = results_key
        """Key name corresponding to the list of data in the JSON object.
        For `SourceResultFormat.NESTED_JSON` (Other formats ignore this attribute)"""

    @abstractmethod
    def extract_data(self) -> list[UnitOfResult]:
        """Extract data from the data source at once"""


class APIDataSource(DataSource):
    """API data source

    Attributes
    ----------
    name : str
        Name of the data source
    ttype : str
        Type of the data source
    result_format : SourceResultFormat
        Format of the result (multiple-results, single-result, ...)
    results_key : str
        Key name corresponding to the list of data in the JSON object.
        For `SourceResultFormat.NESTED_JSON` (Other formats ignore this attribute)
    endpoint : str
        API endpoint
    headers : dict
        HTTP headers
    params : dict
        URL parameters
    """
    ttype: ClassVar[str] = "API"

    def __init__(self, name: str,
                 result_format: SourceResultFormat, results_key: str,
                 endpoint: str, headers: dict, params: dict):
        super().__init__(name, result_format, results_key)
        self.endpoint = endpoint
        """API endpoint"""
        self.headers = headers
        """HTTP headers"""
        self.params = params
        """URL parameters"""

    def extract_data(self) -> list[UnitOfResult]:
        raise NotImplementedError("API data extraction is not implemented yet")


class DBDataSource(DataSource):
    """Database data source

    Attributes
    ----------
    name : str
        Name of the data source
    ttype : str
        Type of the data source
    result_format : SourceResultFormat
        Format of the result (multiple-results, single-result, ...)
    results_key : str
        Key name corresponding to the list of data in the JSON object.
        For `SourceResultFormat.NESTED_JSON` (Other formats ignore this attribute)
    query : str
        SQL query to retrieve the data
    """
    sql_dialect: ClassVar[SQLDialect] = SQLDialect.OTHER

    def __init__(self, name: str,
                 result_format: SourceResultFormat, results_key: str,
                 query: str):
        super().__init__(name, result_format, results_key)
        self.query = query
        """SQL query to retrieve the data"""

    @abstractmethod
    def extract_data(self) -> list[UnitOfResult]:
        """Extract data from the source DB at once"""

class RawDataSource(DataSource):
    """Data source holding raw data

    Attributes
    ----------
    name : str
        Name of the data source
    ttype : str
        Type of the data source
    result_format : SourceResultFormat
        Format of the result (multiple-results, single-result, ...)
    results_key : str
        Key name corresponding to the list of data in the JSON object.
        For `SourceResultFormat.NESTED_JSON` (Other formats ignore this attribute)
    data : Any
        Raw data
    """
    ttype: ClassVar[str] = "RAW"

    def __init__(self, name: str,
                 result_format: SourceResultFormat, results_key: str,
                 data: Any):
        super().__init__(name, result_format, results_key)
        self.data = data
        """Raw data"""

    def extract_data(self) -> list[UnitOfResult]:
        """Extract data from the source at once"""
        return self.data
