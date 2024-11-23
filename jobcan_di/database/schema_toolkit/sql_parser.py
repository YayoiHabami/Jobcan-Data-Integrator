"""
This module defines a SQL parser that can analyze CREATE TABLE statements
and extract detailed information about table structures,
including columns, constraints, and relationships.
It uses regular expressions and string manipulation to parse SQL statements
and organize the extracted information into structured data classes.

## Functions

- `get_create_table_clauses`: Extract CREATE TABLE clauses from SQL strings.
- `parse_sql`: Parse SQL CREATE TABLE statements and extract table structures.

## Parsed SQL Elements

The parser can extract the following elements from SQL CREATE TABLE statements:

1. **Table Names**: The names of the tables being created.

2. **Column Definitions**:
   - Column name
   - Data type
   - NOT NULL constraint
   - AUTOINCREMENT property
   - DEFAULT values
   - UNIQUE constraint (per column)
   - PRIMARY KEY constraint (per column)

3. **Table-level Constraints**:
   - Composite UNIQUE keys
   - Composite PRIMARY KEYs
   - FOREIGN KEYs

4. **Relationships**:
   - Foreign key relationships between tables

## Notes

- This parser ignores options like `IF NOT EXISTS` and `WITHOUT ROWID`.

## Example SQL Statement and Parsed Output

Here's an example SQL statement that demonstrates the capabilities of the parser:

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE (user_id, created_at)
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE post_tags (
    post_id INTEGER,
    tag_id INTEGER,
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
```

When parsed, this SQL statement would produce the following output:

```
Table: users
Columns:
  - id: INTEGER
    NOT NULL
    AUTOINCREMENT
  - username: TEXT
    NOT NULL
  - email: TEXT
    NOT NULL
  - password: TEXT
    NOT NULL
  - created_at: TIMESTAMP
    DEFAULT: CURRENT_TIMESTAMP
Unique Keys:
  - username
  - email
Primary Keys:
  - id

Table: posts
Columns:
  - id: INTEGER
    NOT NULL
    AUTOINCREMENT
  - user_id: INTEGER
    NOT NULL
    FOREIGN KEY: ('users', 'id')
  - title: TEXT
    NOT NULL
  - content: TEXT
  - created_at: TIMESTAMP
    DEFAULT: CURRENT_TIMESTAMP
Unique Keys:
  - user_id, created_at
Primary Keys:
  - id

Table: tags
Columns:
  - id: INTEGER
    NOT NULL
    AUTOINCREMENT
  - name: TEXT
    NOT NULL
Unique Keys:
  - name
Primary Keys:
  - id

Table: post_tags
Columns:
  - post_id: INTEGER
    FOREIGN KEY: ('posts', 'id')
  - tag_id: INTEGER
    FOREIGN KEY: ('tags', 'id')
Primary Keys:
  - post_id, tag_id
```
"""
import re
from typing import Optional

from ._core import ColumnStructure, TableStructure, SQLDialect



#
# SQL Splitting Functions
#

def get_create_table_clauses(sql: str) -> list[str]:
    """
    Extract CREATE TABLE clauses from the given SQL string.

    This function uses a simple parsing approach and may not handle all edge cases.
    For complex SQL, consider using a dedicated SQL parser.

    Args
    ----
    sql : str
        The SQL string containing CREATE TABLE statements.

    Returns
    -------
    list[str]
        A list of CREATE TABLE clauses found in the SQL string.

    Note
    ----
        This function does not handle escaped quotes or nested CREATE TABLE statements.
    """
    pattern: str = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    clauses: list[str] = []
    current_clause: str = ""
    paren_count: int = 0
    in_string: bool = False
    string_delimiter: str = ""

    for match in re.finditer(pattern, sql, re.IGNORECASE):
        start: int = match.start()
        current_clause = sql[start:]

        for i, char in enumerate(current_clause):
            if char in ("'", '"') and not in_string:
                # Start of a string literal
                in_string = True
                string_delimiter = char
            elif char == string_delimiter and in_string:
                # End of a string literal
                in_string = False
            elif not in_string:
                # Check for parentheses and semicolons (outside of string literals)
                if char == "(":
                    paren_count += 1
                elif char == ")":
                    paren_count -= 1
                elif char == ";" and paren_count == 0:
                    # End of the CREATE TABLE clause
                    clauses.append(current_clause[:i+1])
                    break

    return clauses

def _split_sql_column_parts(content: str) -> list[str]:
    """Split SQL content into parts.

    Args
    ----
    content : str
        SQL content to split

    Returns
    -------
    list[str]
        List of SQL parts

    Examples
    --------
    >>> _split_sql_column_parts("id INTEGER PRIMARY KEY, username TEXT NOT NULL, UNIQUE (id, username)")
    ['id INTEGER PRIMARY KEY', 'username TEXT NOT NULL', 'UNIQUE (id, username)']
    >>> _split_sql_column_parts("user_id INTEGER DEFAULT(1, 2, 3), name TEXT")
    ['user_id INTEGER DEFAULT(1, 2, 3)', 'name TEXT']
    """
    parts = []
    current_part = []
    paren_count = 0
    in_single_quotes = False
    in_double_quotes = False

    for char in content:
        if char == "'" and not in_double_quotes:
            in_single_quotes = not in_single_quotes
        elif char == '"' and not in_single_quotes:
            in_double_quotes = not in_double_quotes

        if not in_single_quotes and not in_double_quotes:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1

        # Only split on commas that are outside of parentheses and quotes
        if char == ',' and paren_count == 0 and not in_single_quotes and not in_double_quotes:
            parts.append(''.join(current_part).strip())
            current_part = []
        else:
            current_part.append(char)

    if current_part:
        parts.append(''.join(current_part).strip())

    return parts

def _parse_create_table_clause(clause: str) -> Optional[tuple[str, list[str], list[str]]]:
    """Parse CREATE TABLE clause.

    Args
    ----
    clause : str
        CREATE TABLE clause to parse

    Returns
    -------
    str
        Table name
    list[str]
        List of column definitions
        (e.g. ['id INTEGER PRIMARY KEY', 'name TEXT NOT NULL'])
    list[str]
        List of table-level constraints and options
        (e.g. "COMMENT='User information'", "WITHOUT ROWID")

    Examples
    --------
    `CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL) WITHOUT ROWID;`
    should return:

    ('users', ['id INTEGER PRIMARY KEY', 'name TEXT NOT NULL'], ['WITHOUT ROWID'])
    """
    clause = clause.strip()
    # split clause into `CREATE TABLE (IF NOT EXISTS) table_name` and other parts
    create_table_match = re.match(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*(.+)",
        clause, re.IGNORECASE | re.DOTALL
    )
    if not create_table_match:
        return

    table_name = create_table_match.group(1)
    table_content = create_table_match.group(2)
    if not table_content.startswith('('):
        return

    # Split table_content into columns and table-level constraints
    column_def = ""
    table_constraints = ""
    paren_count = 0
    for i, char in enumerate(table_content):
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
            if paren_count == 0:
                column_def = table_content[1:i]
                table_constraints = table_content[i+1:].strip()
                break
    if not column_def:
        # No column definitions found
        return

    columns = _split_sql_column_parts(column_def)
    constraints = [c.strip() for c in table_constraints.split(',')]
    return table_name, columns, constraints

#
# SQL Parsing Functions
#

def _parse_column_sql(
        column_sql: str
    ) -> Optional[tuple[ColumnStructure, bool, bool]]:
    """Parse column SQL.

    Args
    ----
    column_sql : str
        Column SQL to parse

    Returns
    -------
    ColumnStructure
        Column structure
    bool
        True if the column is UNIQUE
    bool
        True if the column is PRIMARY KEY
    tuple[str, str]
        (table_name, column_name) of the foreign key reference
    """
    column_sql = column_sql.strip()
    column_match = re.match(r'(\w+)\s+(.+)', column_sql)
    if not column_match:
        return

    column_name = column_match.group(1)
    column_def = column_match.group(2)
    column_def_u = column_def.upper()

    column_type = column_def_u.split()[0]
    not_null = 'NOT NULL' in column_def_u
    autoincrement = 'AUTOINCREMENT' in column_def_u

    # Extract DEFAULT value (string (by ' or "), number, or identifier)
    default_match = re.search(
        r'DEFAULT\s+((?:\'.*?\')|(?:".*?")|(?:-?\b\d+(?:\.\d+)?\b)|(?:[a-zA-Z_\d]+))',
        column_def, re.IGNORECASE
    )
    default = default_match.group(1) if default_match else None

    unique = 'UNIQUE' in column_def_u
    primary_key = 'PRIMARY KEY' in column_def_u

    foreign_key = None
    if 'FOREIGN KEY' in column_def:
        fk_match = re.match(
            r'FOREIGN KEY\s*(?:\(.+?\))?\s*REFERENCES\s*(\w+)\s*\((\w+)\)',
            column_def, re.IGNORECASE
        )
        if fk_match:
            foreign_key = (fk_match.group(1), fk_match.group(2))

    return ColumnStructure(
        name=column_name,
        ttype=column_type,
        not_null=not_null,
        autoincrement=autoincrement,
        default=default,
        foreign_key=foreign_key
    ), unique, primary_key

def _parse_table_sql(
        table_name: str,
        column_defs: list[str],
        sql_dialect: SQLDialect = SQLDialect.SQLITE
    ) -> TableStructure:
    """Parse CREATE TABLE SQL into a TableStructure.

    Args
    ----
    table_name : str
        Table name
    column_defs : list[str]
        List of column definitions

    Returns
    -------
    TableStructure
        Table structure
    """
    columns = []
    unique_keys = []
    primary_keys = []
    foreign_keys = {}

    for part in column_defs:
        part = part.strip()

        if part.upper().startswith('UNIQUE'):
            unique_key = re.findall(r'\((.+?)\)', part)
            if unique_key:
                unique_keys.append([col.strip() for col in unique_key[0].split(',')])
        elif part.upper().startswith('PRIMARY KEY'):
            primary_key = re.findall(r'\((.+?)\)', part)
            if primary_key:
                primary_keys = [col.strip() for col in primary_key[0].split(',')]
        elif part.upper().startswith('FOREIGN KEY'):
            fk_match = re.match(r'FOREIGN KEY\s*\((\w+)\)\s*REFERENCES\s*(\w+)\s*\((\w+)\)',
                                part, re.IGNORECASE)
            if fk_match:
                foreign_keys[fk_match.group(1)] = (fk_match.group(2), fk_match.group(3))
        else:
            if res := _parse_column_sql(part):
                column, uk, pk = res
                columns.append(column)
                if uk:
                    unique_keys.append([column.name])
                if pk:
                    primary_keys.append(column.name)

    table = TableStructure(
        name=table_name,
        columns=columns,
        unique_keys=unique_keys,
        primary_keys=primary_keys
    )

    # Set NOT NULL constraints for primary keys
    if sql_dialect == SQLDialect.SQLITE:
        pass
    else:
        for pk in primary_keys:
            for column in table.columns:
                if column.name == pk:
                    column.not_null = True

    # Set FOREIGN KEY constraints
    for column_name, (ref_table, ref_column) in foreign_keys.items():
        for column in table.columns:
            if column.name == column_name:
                column.foreign_key = (ref_table, ref_column)

    return table

def parse_sql(
        sql: str,
        sql_dialect: SQLDialect = SQLDialect.SQLITE
    ) -> list[TableStructure]:
    """Parse SQL into table structures.

    Args
    ----
    sql : str
        SQL to parse

    Returns
    -------
    list[TableStructure]
        List of table structures
        If no valid CREATE TABLE statements are found in the SQL, an empty list is returned
    """
    tables = []

    if ";" not in sql:
        sql += ";"  # Add a semicolon at the end if it's missing

    for clause in get_create_table_clauses(sql):
        if res := _parse_create_table_clause(clause):
            table_name, column_defs, _ = res
        else:
            continue

        tables.append(_parse_table_sql(table_name, column_defs, sql_dialect))
        tables[-1].raw_sql = clause

    return tables
