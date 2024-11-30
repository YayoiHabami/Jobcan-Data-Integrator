"""
Data classes for loading and storing files describing DB definitions
and how to store them in the DB

Classes
-------
- DataLink: Define data sources and how to store them in the DB
- PipelineDefinition: Table definition and data link
"""
from dataclasses import dataclass, field

from ._db_definition import DBDefinition
from ._data_source import DataSource
from ._insertion_profile import InsertionProfile



@dataclass
class DataLink:
    """Define data sources (e.g., which APIs and DBs to use and how)
    and how to store them in the DB

    Attributes
    ----------
    sources: list[DataSource]
        List of data sources
    """
    sources: list[DataSource] = field(default_factory=list)
    """List of data sources"""
    insertion_profiles: dict[str, InsertionProfile] = field(default_factory=dict)
    """Insertion profiles for the data sources. The key is the table name"""

    def add_source(self, source: DataSource) -> bool:
        """Add a data source

        Parameters
        ----------
        source: DataSource
            Data source to add

        Returns
        -------
        bool
            False if the source with the same name already exists
        """
        if source.name in [s.name for s in self.sources]:
            return False
        self.sources.append(source)
        return True

@dataclass
class PipelineDefinition:
    """Pipeline definition.

    Attributes
    ----------
    table_definition: DBDefinition
        DB and tables definitions
    data_link: DataLink
        Define data sources (e.g., which APIs and DBs to use and how)
        and how to store them in the DB
    """
    table_definition: DBDefinition
    """DB and tables definitions"""
    data_link: DataLink
    """Define data sources (e.g., which APIs and DBs to use and how)s"""
