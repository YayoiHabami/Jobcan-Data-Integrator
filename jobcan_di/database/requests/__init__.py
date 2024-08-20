"""
This module provides functions to store and retrieve the response
of the `/v1/requests/{request_id}` API.

The data is stored in a SQLite database and is retrieved
as a dict object (like the API response).

Functions (main)
---------
- `create_tables`: Create `requests` tables and relationships in the database
- `update`: Insert or update `requests` data in the database
- `retrieve`: Retrieve `requests` data from the database

Functions (sub)
---------
- `retrieve_customized_items`: Retrieve customized items data
- `retrieve_expense`: Retrieve expense data
- `retrieve_payment`: Retrieve payment data
- `retrieve_ec`: Retrieve EC data
- `retrieve_approval_process`: Retrieve approval process data
- `retrieve_viewers`: Retrieve viewers data
- `retrieve_modify_logs`: Retrieve modify logs data
- `retrieve_default_attachment_files`: Retrieve default attachment files data
- `retrieve_ids`: Retrieve request IDs from `requests` table

Usage
------
1. Create tables in the database

```python
import sqlite3
from jobcan_di.database import req

conn = sqlite3.connect('jobcan_di.db')
req.create_tables(conn)
```

2. Insert or update data in the database

```python
# Before running this code, you need to retrieve the data from the API
# (Here, `response` is the response of the `/v1/requests/{request_id}` API)

data = response.json()
req.update(conn, data)
```

3. Retrieve data from the database

```python
cursor = conn.cursor()
request_id = "sa-10"
data = req.retrieve(cursor, request_id)
```
"""
from ._table_init import create_tables
from ._data_class import (
    CommentDataList,
    FileDataList,
    GenericMasterDataList
)
from ._customized_items import retrieve_customized_items
from ._expense import retrieve_expense
from ._payment import retrieve_payment
from ._ec import retrieve_ec
from ._approval_process import retrieve_approval_process
from ._viewers import retrieve_viewers
from ._modify_logs import retrieve_modify_logs
from ._default_attachment_files import retrieve_default_attachment_files
from ._requests import update, retrieve, retrieve_ids
