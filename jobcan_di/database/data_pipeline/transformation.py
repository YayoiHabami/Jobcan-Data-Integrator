"""
This module provides functions for transforming data based on a given profile.

Functions
---------
- recursive_get: Recursively retrieve a value from nested data structures
- get_indices: Get the indices of a value in a list
- transform_named_data: Transform named data based on the given profile
- transform_positional_data: Transform positional data based on the given profile

Enums
-----
- ErrorHandlingOptions: Error handling options for data extraction

Constants
---------
- DEFAULT_ERROR_HANDLING: Default error handling options for recursive data extraction
  - Raises an error if a non-string dictionary key is used
  - Raises an error if a non-integer list index is used
  - Raises an error if a list index is out of range
  - Raises an error if nested access is attempted on a non-container type

Examples
--------
>>> extracted = {
...     "user_api": [
...         {
...             "user_code": "foo",
...             "last_name": "Doe",
...             "first_name": "John",
...             "user_positions": [
...                 {"position_code": "manager", "group_code": "100"},
...                 {"position_code": "officer", "group_code": "200"}
...             ],
...             "extra_items": [{"key": "value1"}, {"key": "value2"}]
...         },
...         {
...             "user_code": "bar",
...             "last_name": "Smith",
...             "first_name": "Jane",
...             "user_positions": [
...                 {"position_code": "manager", "group_code": "200"}
...             ],
...             "extra_items": [{"key": "value3"}]
...         }
...     ]
... }

>>> source_name = "user_api"
>>> named_parameters = {
...     "user_code": ["user_code"],
...     "position_code": ["user_positions", -1, "position_code"],
...     "group_code": ["user_positions", -1, "group_code"],
...     "extra_key": ["extra_items", -1, "key"]
... }
>>> positional_parameters = [
...     ["user_code"],
...     ["user_positions", -1, "position_code"],
...     ["user_positions", -1, "group_code"],
...     ["extra_items", -1, "key"]
... ]

>>> transform_named_data(extracted, source_name, named_parameters)
[
    {"user_code": "foo", "position_code": "manager", "group_code": "100", "extra_key": "value1"},
    {"user_code": "foo", "position_code": "manager", "group_code": "100", "extra_key": "value2"},
    {"user_code": "foo", "position_code": "officer", "group_code": "200", "extra_key": "value1"},
    {"user_code": "foo", "position_code": "officer", "group_code": "200", "extra_key": "value2"},
    {"user_code": "bar", "position_code": "manager", "group_code": "200", "extra_key": "value3"}
]
>>> transform_positional_data(extracted, source_name, positional_parameters)
[
    ["foo", "manager", "100", "value1"],
    ["foo", "manager", "100", "value2"],
    ["foo", "officer", "200", "value1"],
    ["foo", "officer", "200", "value2"],
    ["bar", "manager", "200", "value3"]
]

Notes
-----
An "aggregate key" is a key that indicates that the data corresponding to `profile` is a list,
and all elements of that list should be processed.
This key is used for exploding data or generating Cartesian products.

For example, consider the following `item` and `profile`:

```python
item = {
    "user_code": "foo",
    "last_name": "Doe",
    "first_name": "John",
    "user_positions": [
        {
            "position_code": "dep. manager",
            "group_code": "100",
            "roles": ["finance", "hr"]
        },
        {
            "position_code": "officer",
            "group_code": "200",
            "roles": ["sales"]
        }
    ]
}
profile = {
    "user_code": ["user_code"],
    "p_code": ["user_positions", -1, "position_code"],
    "roles": ["user_positions", -1, "roles", -1]
}
```

In this case, `"p_code"` and `"roles"` become "aggregate keys".
These keys process the entire list (`-1` specifies this) of
`"user_positions"` and `"roles"` respectively. On the other hand,
`"user_code"` is not an "aggregate key" because it refers to a single value.

In the transform stage, combinations (Cartesian product) of all elements
in the lists specified by the "aggregate keys" are generated. As a result,
the following output is expected:

```python
# Expected result
[
    {"user_code": "foo", "p_code": "dep. manager", "roles": "finance"},
    {"user_code": "foo", "p_code": "dep. manager", "roles": "hr"},
    {"user_code": "foo", "p_code": "officer", "roles": "sales"}
]
```

This output will have 3 times the number of elements due to the product
of `"roles"` and `"position_code"` (`position_code="dep. manager"` has 2 roles,
and `position_code="officer"` has 1 role) in the input, resulting in 3 elements.
By using "aggregate keys", such complex data structure expansion and combination
can be performed efficiently.
"""
from collections.abc import Sequence, Mapping
from copy import deepcopy
from enum import Flag, auto
from typing import Any, Union, Optional

from ._insertion_profile import ParameterConversionMethod



#
# Base
#

class ErrorHandlingOptions(Flag):
    """Error handling options for data extraction

    Attributes
    ----------
    NONE : int
        No error handling
    NON_EXISTING_DICT_KEY : int
        Raise an error when a non-existing dictionary key is accessed
    NON_STRING_DICT_KEY : int
        Raise an error when a non-string dictionary key is used
    NON_INTEGER_LIST_INDEX : int
        Raise an error when a non-integer list index is used
    LIST_INDEX_OUT_OF_RANGE : int
        Raise an error when a list index is out of range
        (only applicable for non-negative indices)
    NESTED_ACCESS_ON_NON_CONTAINER : int
        Raise an error when trying to access nested data on
        a non-container type
    """
    NONE = 0
    """No error handling"""
    NON_EXISTING_DICT_KEY = auto()
    """Raise an error when a non-existing dictionary key is accessed"""
    NON_STRING_DICT_KEY = auto()
    """Raise an error when a non-string dictionary key is used"""
    NON_INTEGER_LIST_INDEX = auto()
    """Raise an error when a non-integer list index is used"""
    LIST_INDEX_OUT_OF_RANGE = auto()
    """Raise an error when a list index is out of range
    (only applicable for non-negative indices)"""
    NESTED_ACCESS_ON_NON_CONTAINER = auto()
    """Raise an error when trying to access nested data on
    a non-container type

    Examples
    --------
    >>> data = {"user": {"name": "John", "age": 30}}
    >>> keys = ["user", "age", "invalid_key"]
    >>> _recursive_get(data, keys, strict=ErrorHandlingOptions.INVALID_DICT_KEY)
    KeyError: 'invalid_key'
    """

DEFAULT_ERROR_HANDLING = ErrorHandlingOptions.NON_STRING_DICT_KEY | \
                         ErrorHandlingOptions.NON_INTEGER_LIST_INDEX | \
                         ErrorHandlingOptions.LIST_INDEX_OUT_OF_RANGE | \
                         ErrorHandlingOptions.NESTED_ACCESS_ON_NON_CONTAINER
"""Default error handling options for recursive data extraction

- Raises an error if a non-string dictionary key is used
- Raises an error if a non-integer list index is used
- Raises an error if a list index is out of range
- Raises an error if nested access is attempted on a non-container type
"""

#
# Base functions
#

def _recursive_get(data: Any,
                   keys: Sequence[Union[str, int]],
                   error_handling:ErrorHandlingOptions) -> Any:
    """
    Recursively retrieve a value from nested data structures (dictionaries and lists).

    This function navigates through nested dictionaries and lists using the provided keys,
    allowing for flexible data extraction from complex data structures.

    Parameters
    ----------
    data : Any
        The data structure to traverse. Can be a dictionary, list, or any other type.
    keys : list[Union[str, int]]
        A list of keys to navigate through the data structure:
        - `str`: Used as a key for dictionaries
        - `int`: Used as an index for lists
          (negative indices are treated specially, see the function body)
    error_handling : ErrorHandlingOptions
        Error handling options for data extraction

    Returns
    -------
    Any
        The value found at the specified location in the data structure.
        Returns None if the path is invalid or the value doesn't exist.

    Raises
    ------
    TypeError
        If the key is not an integer for list access or not a string for dictionary access
        (For error handling options: `NON_INTEGER_LIST_INDEX`, `NON_STRING_DICT_KEY`)

        If nested access is attempted on a non-container type
        (For error handling option: `NESTED_ACCESS_ON_NON_CONTAINER`)
    KeyError
        If the key doesn't exist in the dictionary
        (For error handling option: `NON_EXISTING_DICT_KEY`)
    IndexError
        If the list index is out of range
        (For error handling option: `LIST_INDEX_OUT_OF_RANGE`)

    Examples
    --------
    >>> data = {
    ...     "user": {"name": "John", "age": 30},
    ...     "groups": [
    ...         {"name": "Group 1", "members": ["Alice", "Bob"]},
    ...         {"name": "Group 2", "members": ["Charlie", "David"]}
    ...     ]
    ... }
    >>> _recursive_get(data, ["user", "name"])
    'John'
    >>> _recursive_get(data, ["groups", 0, "members", 1])
    'Bob'
    >>> # Using negative indices to list the last group members
    >>> _recursive_get(data, ["groups", -1, "members"]) # or ["groups", "members"]
    [['Alice', 'Bob'], ['Charlie', 'David']]
    >>> _recursive_get(data, ["groups", -1, "members", 1]) # or ["groups", "members", 1]
    ['Bob', 'David']
    """
    # Base case: if no keys left, return the current data
    if not keys:
        return data

    # If data is None, we can't proceed further
    if data is None:
        if error_handling & ErrorHandlingOptions.NESTED_ACCESS_ON_NON_CONTAINER:
            raise TypeError("Nested access is only supported on dictionaries and lists")
        return None

    # Get the first key
    key = keys[0]

    if isinstance(data, list):
        if isinstance(key, int) and key >= 0:
            # If key is a non-negative integer, use it as a list index
            # Check if the index is within the bounds of the list
            if key >= len(data):
                if error_handling & ErrorHandlingOptions.LIST_INDEX_OUT_OF_RANGE:
                    raise IndexError(f"List index out of range: {key}")
                else:
                    return None

            return _recursive_get(data[key], keys[1:], error_handling)
        else:
            # For negative integers or non-integer keys, apply the function to all list items
            if isinstance(key, int):
                # Skip the current key if it's an integer (even if negative)
                keys = keys[1:]
            elif error_handling & ErrorHandlingOptions.NON_INTEGER_LIST_INDEX:
                # Raise an error if the key is not an integer
                raise TypeError(f"List index must be an integer: {key}")

            return [_recursive_get(item, keys, error_handling) for item in data]
    elif isinstance(data, dict):
        # Check if the key is a string (required for dictionary access)
        if (not isinstance(key, str)) and \
                error_handling & ErrorHandlingOptions.NON_STRING_DICT_KEY:
            raise TypeError(f"Dictionary key must be a string: {key}")

        # Check if the key exists in the dictionary
        if key not in data:
            if error_handling & ErrorHandlingOptions.NON_EXISTING_DICT_KEY:
                raise KeyError(f"Key not found: {key}")
            else:
                return None

        # For dictionaries, use the key to get the next level of data
        return _recursive_get(data[key], keys[1:], error_handling)
    else:
        # If data is neither a list nor a dict, we can't proceed further
        if error_handling & ErrorHandlingOptions.NESTED_ACCESS_ON_NON_CONTAINER:
            raise TypeError("Nested access is only supported on dictionaries and lists")
        else:
            return None

def recursive_get(data: Any,
                  keys: Sequence[Union[str, int]],
                  error_handling: ErrorHandlingOptions = DEFAULT_ERROR_HANDLING
                 ) -> Any:
    """Recursively retrieve a value from nested data structures (dictionaries and lists).

    This function navigates through nested dictionaries and lists using the provided keys,
    allowing for flexible data extraction from complex data structures.

    Parameters
    ----------
    data : Any
        The data structure to traverse. Can be a dictionary, list, or any other type.
    keys : list[Union[str, int]]
        A list of keys to navigate through the data structure:
        - `str`: Used as a key for dictionaries
        - `int`: Used as an index for lists
          (negative indices are treated specially, see the function body)
    error_handling : ErrorHandlingOptions
        Error handling options for data extraction

    Raises
    ------
    TypeError
        If the key is not an integer for list access or not a string for dictionary access
        (For error handling options: `NON_INTEGER_LIST_INDEX`, `NON_STRING_DICT_KEY`)

        If nested access is attempted on a non-container type
        (For error handling option: `NESTED_ACCESS_ON_NON_CONTAINER`)
    KeyError
        If the key doesn't exist in the dictionary
        (For error handling option: `NON_EXISTING_DICT_KEY`)
    IndexError
        If the list index is out of range
        (For error handling option: `LIST_INDEX_OUT_OF_RANGE`)

    Returns
    -------
    Any
        The value found at the specified location in the data structure.
        Returns None if the path is invalid or the value doesn't exist.

    Examples
    --------
    >>> data = {
    ...     "user": {"name": "John", "age": 30},
    ...     "groups": [
    ...         {"name": "Group 1", "members": ["Alice", "Bob"]},
    ...         {"name": "Group 2", "members": ["Charlie", "David"]}
    ...     ]
    ... }
    >>> _recursive_get(data, ["user", "name"])
    'John'
    >>> _recursive_get(data, ["groups", 0, "members", 1])
    'Bob'
    >>> # Using negative indices to list the last group members
    >>> _recursive_get(data, ["groups", -1, "members"]) # or ["groups", "members"]
    [['Alice', 'Bob'], ['Charlie', 'David']]
    >>> _recursive_get(data, ["groups", -1, "members", 1]) # or ["groups", "members", 1]
    ['Bob', 'David']
    """
    return _recursive_get(data, keys, error_handling)

def get_indices(data:Sequence[Any], value:Any) -> list[int]:
    """Get the indices of a value in a list

    Parameters
    ----------
    data : list[Any]
        List of values
    value : Any
        Value to search for in the list

    Returns
    -------
    list[int]
        List of indices where the value is found in the list

    Examples
    --------
    >>> data = [1, 2, 3, 2, 4, 2]
    >>> get_indices(data, 2)
    [1, 3, 5]
    """
    res = []
    for _ in range(data.count(value)):
        index = res[-1] + 1 if res else 0
        res.append(data.index(value, index, len(data)))
    return res

#
# Transformation (JSON->JSON conversion)
#

def transform_named_data(
        extracted: Mapping[str, Sequence[dict]],
        source_name: str,
        profile: Mapping[str, Sequence[Union[str, int]]], *,
        conversion_method: Optional[Mapping[str, ParameterConversionMethod]] = None
    ) -> list[dict[str, Any]]:
    """
    Transform named data based on the given profile.

    Parameters
    ----------
    extracted : dict[str, list[dict]]
        Dictionary containing the source data
    source_name : str
        Name of the source to be processed
    profile : dict[str, list[Union[str, int]]]
        Dictionary defining the transformation rules
    conversion_method : dict[str, ParameterConversionMethod], optional
        Dictionary defining the conversion methods for each parameter

    Returns
    -------
    list[dict]
        List of transformed dictionaries

    Notes
    -----
    - This code is optimized for `recursive_get` with `DEFAULT_ERROR_HANDLING`
    """
    if source_name not in extracted:
        return []
    source = extracted[source_name]

    transformed = _transform_source(source, profile)

    # Convert the data types based on the conversion method
    if conversion_method:
        transformed = convert_data_type(transformed, conversion_method)

    return transformed

def transform_positional_data(
        extracted: Mapping[str, Sequence[dict]],
        source_name: str,
        profile: Sequence[Sequence[Union[str, int]]], *,
        conversion_method: Optional[Mapping[str, ParameterConversionMethod]] = None
    ) -> list[tuple[Any, ...]]:
    """
    Transform positional data based on the given profile.

    Parameters
    ----------
    extracted : dict[str, list[dict]]
        Dictionary containing the source data
    source_name : str
        Name of the source to be processed
    profile : list[list[Union[str, int]]]
        List defining the transformation rules
    conversion_method : dict[Union[int, str], ParameterConversionMethod], optional
        Dictionary defining the conversion methods for each parameter;
        The key is the index of the parameter in the profile

    Returns
    -------
    list[list]
        List of transformed lists

    Notes
    -----
    - This code is optimized for `recursive_get` with `DEFAULT_ERROR_HANDLING`
    """
    if source_name not in extracted:
        return []
    source = extracted[source_name]

    # Convert the profile to a dictionary with indexes as string keys
    profile_dict = {str(i): p for i, p in enumerate(profile)}
    transformed = _transform_source(source, profile_dict)

    # Convert the data types based on the conversion method
    if conversion_method:
        _conversion_method = {str(k): v for k, v in conversion_method.items()}
        transformed = convert_data_type(transformed, _conversion_method)

    # Convert each dictionary to a list of values based on the profile
    sorted_indexes = [sorted(map(int, tri.keys())) for tri in transformed]
    return [
        tuple(tri[str(index)] for index in sorted_index)
        for tri, sorted_index in zip(transformed, sorted_indexes)
    ]

def _transform_source(
        source: Sequence[dict],
        profile: Mapping[str, Sequence[Union[str, int]]]
    ) -> list[dict[str, Any]]:
    """Transform the source data based on the given profile.

    Parameters
    ----------
    source : list[dict]
        List of source data to process
    profile : dict[str, list[Union[str, int]]]
        Dictionary defining the transformation rules

    Returns
    -------
    list[dict]
        List of transformed dictionaries
    """
    aggregate_keys, rest_profile = _process_profile(profile)
    independent_placeholders = _get_independent_placeholders(profile, aggregate_keys)

    result = []
    for item in source:
        base_dict: dict[str, Any] = {
            ph: recursive_get(item, profile[ph]) for ph in independent_placeholders
        }
        base_items = [base_dict]

        result.extend(_transform_source_item(item, base_items,
                                             aggregate_keys, rest_profile))

    return result

def _process_profile(
        profile: Mapping[str, Sequence[Union[str, int]]]
    ) -> tuple[dict[tuple[Union[str, int], ...], list[str]],
               dict[tuple[Union[str, int], ...], list[list[Union[str, int]]]]
               ]:
    """Process the profile to identify aggregate keys and remaining profile.

    Parameters
    ----------
    profile : dict[str, list[Union[str, int]]]
        Dictionary defining the transformation rules

    Returns
    -------
    aggregate_keys : dict[tuple[Union[str, int], ...], list[str]]
        Dictionary of keys that need aggregation
    rest_profile : dict[tuple[Union[str, int], ...], list[list[Union[str, int]]]
        Dictionary of remaining profile for the aggregated keys

    Examples
    --------
    >>> profile = {
    ...     "group_code_k": ["user_positions", -1, "group_code"],
    ...     "position_code_k": ["user_positions", -1, "position_code"],
    ...     "extra_key": ["extra_items", -1, "key", "extra"]
    ... }
    >>> _process_profile(profile)
    ({
        ('user_positions',): ['group_code_k', 'position_code_k'],
        ('extra_items',): ['extra_key']
    }, {
        ('user_positions',): [['group_code'], ['position_code']],
        ('extra_items',): [['key', 'extra']]
    })
    """
    aggregate_keys: dict[tuple[Union[str, int], ...], list[str]] = {}
    rest_profile: dict[tuple[Union[str, int], ...], list[list[Union[str, int]]]] = {}

    for placeholder, keys in profile.items():
        for index in get_indices(keys, -1):
            # Find the index of the placeholder '-1'
            key_tuple = tuple(keys[:index])

            # Add the placeholder to the aggregate_keys dictionary
            aggregate_keys.setdefault(key_tuple, []).append(placeholder)
            # Add the remaining profile to the rest_profile dictionary
            rest_profile.setdefault(key_tuple, []).append(list(keys[index + 1:]))
            break

    return aggregate_keys, rest_profile

def _get_independent_placeholders(
        profile: Mapping[str, Sequence[Union[str, int]]],
        aggregate_keys: dict[tuple[Union[str, int], ...], list[str]]
    ) -> set[str]:
    """Identify placeholders that don't need to be aggregated.
    (Nearly placeholders whose corresponding keys (on `profile`) do not contain -1)

    Parameters
    ----------
    profile : dict[str, list[Union[str, int]]]
        Dictionary defining the transformation rules
    aggregate_keys : dict[tuple[Union[str, int], ...], list[str]]
        Dictionary of keys that need aggregation

    Returns
    -------
    set[str]
        Set of independent placeholders
    """
    return set(profile.keys()) - set(sum(aggregate_keys.values(), []))

def _transform_source_item(
        source: dict,
        base_items: list[dict[str, Any]],
        aggregate_keys: dict[tuple[Union[str, int], ...], list[str]],
        rest_profile: dict[tuple[Union[str, int], ...], list[list[Union[str, int]]]]
    ) -> list[dict[str, Any]]:
    """Transform a single item based on aggregate keys and rest profile.

    Parameters
    ----------
    source : dict
        Source item to process
    base_items : list[dict[str, Any]]
        List of base dictionaries
    aggregate_keys : dict[tuple[Union[str, int], ...], list[str]]
        Dictionary of keys that need aggregation
    rest_profile : dict[tuple[Union[str, int], ...], list[list[Union[str, int]]]
        Dictionary of remaining profile for aggregated keys

    Returns
    -------
    list[dict[str, Any]]
        List of transformed dictionaries
    """
    for keys, placeholders in aggregate_keys.items():
        additional_items = _aggregate_additional_items(
            source, placeholders, keys, rest_profile[keys]
        )

        base_items = [
            {**base_item, **_additional}
            for base_item in base_items
            for _additional in additional_items
        ]

    return base_items

def _aggregate_additional_items(
        sources: dict,
        placeholders: Sequence[str],
        keys: Sequence[Union[str, int]],
        rest_profile: Sequence[list[Union[str, int]]]
    ) -> list[dict[str, Any]]:
    """Aggregate additional items based on the given keys and placeholders.

    Parameters
    ----------
    sources : dict
        Source data
    placeholders : list[str]
        List of placeholders
    keys : list[Union[str, int]]
        List of keys to navigate through the data structure
    rest_profile : list[list[Union[str, int]]]
        Remaining profile for the aggregated keys

    Returns
    -------
    list[dict[str, Any]]
        List of additional items
    """
    inner_sources = recursive_get(sources, keys)
    if inner_sources is None:
        # TODO: There are two possible behaviors for this case:
        #       (1) return [{placeholder: None}, ...] (current) => the result has the placeholders with null values
        #       (2) return [{}] (alternative) => the result misses the placeholders
        return [{k:None for k in placeholders}]
    elif not isinstance(inner_sources, list):
        raise ValueError("Invalid data structure: expected a list for '-1' index")

    additional_items = []
    all_items_independent = not any(-1 in rp for rp in rest_profile)

    for inner_source in inner_sources:
        if all_items_independent:
            # Single item for each inner source
            additional_items.append({
                placeholder: recursive_get(inner_source, rest_profile[i])
                for i, placeholder in enumerate(placeholders)
            })
        else:
            # Multiple items for each inner source
            additional_items.extend(_transform_source(
                [inner_source], dict(zip(placeholders, rest_profile))
            ))

    return additional_items

#
# Data type conversion
#

def convert_data_type(
        data: Sequence[Mapping[str, Any]],
        conversion_method: Mapping[str, ParameterConversionMethod]
    ) -> list[dict[str, Any]]:
    """Convert data types based on the given conversion method.

    Parameters
    ----------
    data : list[dict[str, Any]]
        List of dictionaries to convert
    conversion_method : dict[str, ParameterConversionMethod]
        Dictionary defining the conversion methods for each parameter

    Returns
    -------
    list[dict[str, Any]]
        List of dictionaries with converted data types
    """
    result = list(map(lambda x: dict(deepcopy(x)), data))
    for key, method in conversion_method.items():
        for item in result:
            if key not in item:
                continue
            item[key] = convert_data_type_specific(item[key], method)

    return result

def convert_data_type_specific(data: Any, method: ParameterConversionMethod) -> Any:
    """Convert data type based on the given conversion method.

    Parameters
    ----------
    data : Any
        Data to convert
    method : ParameterConversionMethod
        Conversion method

    Returns
    -------
    Any
        Converted data
    """
    if method == ParameterConversionMethod.TO_INT:
        return int(data)
    elif method == ParameterConversionMethod.TO_FLOAT:
        return float(data)
    elif method == ParameterConversionMethod.TO_STRING:
        return str(data)
    elif method == ParameterConversionMethod.TO_BOOL:
        if isinstance(data, str) & (data.lower() in ["true", "false"]):
            return data.lower() == "true"
        return bool(data)
    else:
        raise NotImplementedError(f"Unsupported conversion method: {method}")

def validate_conversion_method_string(
        method: str, ignore_case: bool = True
    ) -> bool:
    """Validate the conversion method string.

    Parameters
    ----------
    method : str
        Conversion method string
    ignore_case : bool, optional
        If True, ignore the case of the conversion method string

    Returns
    -------
    bool
        True if the conversion method string is valid, False otherwise
    """
    if ignore_case:
        method = method.lower()
        return method in [m.name.lower() for m in ParameterConversionMethod]
    else:
        return method in [m.name for m in ParameterConversionMethod]

