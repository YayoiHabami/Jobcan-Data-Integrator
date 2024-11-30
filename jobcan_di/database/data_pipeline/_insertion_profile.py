"""
Insertion profile for inserting data into the database

Classes
-------
- InsertionProfile: Insertion profile (Define how to insert data into the database)
- NamedInsertionProfile: Insertion profile with named parameters
- PositionalInsertionProfile: Insertion profile with positional parameters

Enums
-----
- ParameterConversionMethod: Parameter conversion method
"""
from enum import Enum, auto
from typing import Any, Optional, Union



class ParameterConversionMethod(Enum):
    """Parameter conversion method"""
    TO_INT = auto()
    TO_FLOAT = auto()
    TO_STRING = auto()
    TO_BOOL = auto()

class InsertionProfile:
    """Insertion profile

    Define how to insert data into the database

    Attributes
    ----------
    query: str
        SQL query to insert data into the table
    parameters: dict[str, list[Any]], optional
        Parameters for the query
        - For named parameters, the key is the parameter name
        - For positional parameters, the key is the position in the query
          (starting from 0; Converted to str internally)
        - The value is a list of keys (for json) or index (for list)
          - For json: `['key1', 'key2']` -> `json['key1']['key2']`
          - For list: `[0, 1]` -> `list[0][1]`
    conversion_method: dict[str, ParameterConversionMethod], optional
        Method of conversion to be performed when storing JSON or list data
        in DB (if conversion is required)
        - The key is the parameter name or position in the query
    """
    def __init__(self,
                 query:str, source:str, *,
                 parameters: Optional[dict[str, list[Union[str, int]]]] = None,
                 conversion_method: Optional[dict[str, ParameterConversionMethod]] = None):
        self.query = query
        """SQL query to insert data into the table"""
        self.source = source
        """Source of the data"""
        self._parameters = parameters or {}
        """Parameters for the query

        - For named parameters, the key is the parameter name
        - For positional parameters, the key is the position in the query
          (starting from 0; Converted to str internally)
        - The value is a list of keys (for json) or index (for list)
          - For json: `['key1', 'key2']` -> `json['key1']['key2']`
          - For list: `[0, 1]` -> `list[0][1]`
        """
        self._conversion_method = conversion_method or {}
        """Method of conversion to be performed when storing JSON or list data
        in DB (if conversion is required)

        - The key is the parameter name or position in the query"""

    def parameter(self, key:str) -> Optional[list[Union[str, int]]]:
        """Return the parameter for the given key

        Parameters
        ----------
        key : str
            Key for the parameters

        Returns
        -------
        list[Any]
            Parameters for the given key
            If the key does not exist, an empty list is returned
        """
        return self._parameters.get(key, None)

    def parameters(self) -> dict[str, list[Union[str, int]]]:
        """Return all parameters

        Returns
        -------
        dict[str, list[Any]]
            Parameters
        """
        return self._parameters

    def conversion_method(self, key:str) -> Optional[ParameterConversionMethod]:
        """Return the conversion method for the given key

        Parameters
        ----------
        key : str
            Key for the conversion method

        Returns
        -------
        ParameterConversionMethod, optional
            Conversion method for the given key
            If the key does not exist, None is returned
        """
        return self._conversion_method.get(key, None)

    def conversion_methods(self) -> dict[str, ParameterConversionMethod]:
        """Return all conversion methods

        Returns
        -------
        dict[str, ParameterConversionMethod]
            Conversion methods; The key is the parameter name
        """
        return self._conversion_method

    def __repr__(self):
        return f"InsertionProfile(query={repr(self.query)}, " \
               f"parameters={self._parameters}, " \
                f"conversion_method={self._conversion_method})"

class NamedInsertionProfile(InsertionProfile):
    """Named insertion profile

    Attributes
    ----------
    query: str
        SQL query to insert data into the table
    parameters: dict[str, list[Any]]
        Parameters for the query
        - The key is the parameter name
        - The value is a list of keys (for json) or index (for list)
          - For json: `['key1', 'key2']` -> `json['key1']['key2']`
          - For list: `[0, 1]` -> `list[0][1]
    conversion_method: dict[str, ParameterConversionMethod], optional
        Method of conversion to be performed when storing JSON or list data
        in DB (if conversion is required)
        - The key is the parameter name
    """
    def __init__(self,
                 query:str,
                 source:str,
                 parameters: dict[str, list[Union[str, int]]],
                 conversion_method: Optional[dict[str, ParameterConversionMethod]] = None):
        super().__init__(query, source=source,
                         parameters=parameters, conversion_method=conversion_method)

    def named_parameter(self, key:str) -> Optional[list[Union[str, int]]]:
        """Return the parameter for the given key

        Parameters
        ----------
        key : str
            Key for the parameters

        Returns
        -------
        list[Any]
            A list of indexes for the given placeholder.
            If the key does not exist, an empty list is returned
        """
        return self.parameter(key)

    def named_parameters(self) -> dict[str, list[Union[str, int]]]:
        """Return all named parameters

        Returns
        -------
        dict[str, list[Any]]
            Named parameters
        """
        return self._parameters

    def __repr__(self):
        return "Named" + super().__repr__()

class PositionalInsertionProfile(InsertionProfile):
    """Positional insertion profile

    Attributes
    ----------
    query: str
        SQL query to insert data into the table
    parameters: dict[str, list[Any]]
        Parameters for the query
        - The key is the position in the query (starting from 0; Converted to str internally)
        - The value is a list of keys (for json) or index (for list)
          - For json: `['key1', 'key2']` -> `json['key1']['key2']`
          - For list: `[0, 1]` -> `list[0][1]
    conversion_method: dict[str, ParameterConversionMethod], optional
        Method of conversion to be performed when storing JSON or list data
        in DB (if conversion is required)
        - The key is the position in the query
    """
    def __init__(self,
                 query:str,
                 source:str,
                 parameters: dict[str, list[Union[str, int]]],
                 conversion_method: Optional[dict[str, ParameterConversionMethod]] = None):
        super().__init__(query, source=source,
                         parameters=parameters, conversion_method=conversion_method)

    def positional_parameter(self, index:Union[int, str]) -> Optional[list[Union[str, int]]]:
        """Return the parameter for the given index

        Parameters
        ----------
        index : Union[int, str]
            Index for the parameters

        Returns
        -------
        list[Any]
            A list of indexes for the given placeholder.
            If the index does not exist, an empty list is returned
        """
        return self.parameter(str(index))

    def positional_parameters(self) -> list[list[Union[str, int]]]:
        """Return all positional parameters

        Returns
        -------
        list[list[Any]]
            Positional parameters
        """
        # Sort by index
        sorted_keys = sorted(map(int, self._parameters.keys()))
        return [self._parameters[str(key)] for key in sorted_keys]

    def conversion_method(self, key:Union[int, str]) -> Optional[ParameterConversionMethod]:
        """Return the conversion method for the given index

        Parameters
        ----------
        key : Union[int, str]
            Index for the conversion method

        Returns
        -------
        ParameterConversionMethod, optional
            Conversion method for the given index
            If the index does not exist, None is returned
        """
        return super().conversion_method(str(key))

    def conversion_methods_i(self) -> dict[int, ParameterConversionMethod]:
        """Return all conversion methods for positional parameters

        Returns
        -------
        dict[int, ParameterConversionMethod]
            Conversion methods; The key is the position in the query
        """
        return {int(key): value for key, value in self._conversion_method.items()}

    def __repr__(self):
        return "Positional" + super().__repr__()
