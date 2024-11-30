"""
Database definition

Define classes to store data after parsing the TOML file that defines the DB.

Classes
-------
- DBDefinition: Database definition
- SQLiteDBDefinition: SQLite database definition
"""
from typing import ClassVar, Optional

from jobcan_di.database.schema_toolkit import TableStructure, SQLDialect



class DBDefinition:
    """Database definition
    (Base class for all database definitions)

    Attributes
    ----------
    ttype : ClassVar[SQLDialect]
        Database type (e.g. SQLITE, ...)
    tables : list[TableStructure]
        List of table structures
    """
    ttype: ClassVar[SQLDialect] = SQLDialect.OTHER

    def __init__(self, tables: list[TableStructure],
                 *, authentication: Optional[dict[str, str]] = None):
        """Initialize the database definition

        Parameters
        ----------
        tables : list[TableStructure]
            List of table structures
        authentication : dict[str, str], optional
            Authentication information
        """
        self.tables = tables
        """List of table structures"""
        self._authentication = authentication or {}
        """Authentication information"""

    def authentication(self, key:str) -> Optional[str]:
        """Return the authentication information for the given key

        Parameters
        ----------
        key : str
            Key for the authentication information

        Returns
        -------
        str, optional
            Authentication information for the given key
        """
        return self._authentication.get(key, None)

    @property
    def authentications(self) -> dict[str, str]:
        """Return the authentication information

        Returns
        -------
        dict[str, str]
            Authentication information
        """
        return self._authentication

    def __repr__(self) -> str:
        """Return the string representation of the database definition

        Returns
        -------
        str
            String representation of the database definition
        """
        return f"DBDefinition(tables={self.tables}, authentication={self._authentication})"

class SQLiteDBDefinition(DBDefinition):
    """SQLite database definition

    Attributes
    ----------
    ttype : ClassVar[SQLDialect]
        Database type (e.g. SQLITE, ...)
    tables : list[TableStructure]
        List of table structures
    path : str
        Path to the SQLite database
    """
    ttype: ClassVar[SQLDialect] = SQLDialect.SQLITE

    def __init__(self, tables: list[TableStructure], path: str,
                 *, authentication: Optional[dict[str, str]] = None):
        """Initialize the SQLite database definition

        Parameters
        ----------
        tables : list[TableStructure]
            List of table structures
        path : str
            Path to the SQLite database
        authentication : dict[str, str], optional
            Authentication information

        Notes
        -----
        - The value of the "path" key in the authentication dictionary is set to the path
        """
        if authentication is None:
            authentication = {}
        authentication["path"] = path
        super().__init__(tables, authentication=authentication)

    @property
    def path(self) -> str:
        """Return the path to the SQLite database

        Returns
        -------
        str
            Path to the SQLite database
        """
        return self.authentication("path")

    @path.setter
    def path(self, path:str) -> None:
        """Set the path to the SQLite database

        Parameters
        ----------
        path : str
            Path to the SQLite database
        """
        self._authentication["path"] = path

    def __repr__(self) -> str:
        return "SQLite" + super().__repr__()
