"""
This module contains classes for storing data before saving it to the database.
These classes are used to store data temporarily before inserting them into the database.
All the data are stored in various layers of JSON data (GET request data).

The classes are as follows:
    - FileDataList: Used to store file data and file associations.
    - CommentDataList: Used to store comment data and comment associations.
    - GenericMasterDataList: Used to store generic master data and additional items.
"""
from typing import Union

class FileDataList:
    """This class is used to store file data and file associations.

    Attributes
    ----------
        request_id: str
            Request ID
        files: list
            List of file data.
        f_info: list
            List of file associations.

    Usage
    -----
        At first, create an instance of this class with the request ID.

        ```python
        f_data_list = FileDataList(request_id)
        ```

        Then, add file data to the list using the add_file method.

        ```python
        f_data_list.add_file(file_data, parent_type, parent_id)
        ```

        Finally, get the file data and file association data using the get_file_data
        and get_file_association_data methods.

        ```python
        file_data = f_data_list.get_file_data()
        file_association_data = f_data_list.get_file_association_data()
        ```

        The file data and file association data are returned as a list of tuples.
    """
    def __init__(self, request_id:str):
        self.request_id = request_id
        self.files = []
        """file data. ``files[i]`` contains the following information:
        ```python
        [
            file_id,
            name,
            type,
            user_name,
            date,
            deleted
        ]
        ```
        """
        self.f_info = []
        """ file associations. ``f_info[i]`` contains the following information:
        ```python
        [
            request_id,
            file_id,
            customized_item_id,
            expense_specific_row_id,
            payment_specific_row_id,
            approval_step_id,
            approval_after_completion_id,
            default_attachment
        ]
        ```
        """

    def add_file(self, file_data:dict, parent_type:int, parent_id) -> None:
        """Add file data to the list.

        Args:
            file_data: File data: it may contain the following keys:
                "id": File ID (int, Not NULL)
                "name": File name (str, Not NULL)
                "type": File type (str, Not NULL)
                "user_name": User name (str)
                "date": DateTime (str)
                "deleted": Deleted or not (bool)
            parent_type: 0 for customized_items, 1 for expense_specific_rows,
                         2 for payment_specific_rows, 3 for approval_steps,
                         4 for approval_process(after_completion),
                         5 for default_attachment
            parent_id: ID of the element holding the list of files,
                       or None for default_attachment_files (parent_type=5).
                       ex) If parent_type is 0, parent_id is customized_item_id"""
        file_id = file_data['id']
        name = file_data['name']
        _type = file_data['type']
        user_name = file_data.get('user_name', None)
        date = file_data.get('date', None)
        deleted = file_data.get('deleted', False)

        idx = -1
        for i, _ in enumerate(self.files):
            if self.files[i][0] == file_id:
                # the file is already in the list
                idx = i

        if idx == -1:
            self.files.append([file_id, name, _type, user_name, date, deleted])
            self.f_info.append([self.request_id, file_id, None, None, None, None, None, 0])
        else:
            # update the file data (if it is not None)
            if user_name is not None:
                self.files[idx][3] = user_name
            if date is not None:
                self.files[idx][4] = date
            if deleted is not None:
                self.files[idx][5] = deleted

        # update the file association data
        if parent_type in [0, 1, 2, 3, 4]:
            self.f_info[idx][parent_type + 2] = parent_id
        elif parent_type == 5:
            self.f_info[idx][7] += 1

    def get_file_data(self) -> list[tuple]:
        """Return the file data.

        Returns:
            List of file data.
        """
        return [tuple(f) for f in self.files]

    def get_file_association_data(self) -> list[tuple]:
        """Return the file association data.

        Returns:
            List of file association data.
        """
        return [tuple(f) for f in self.f_info]

class CommentDataList:
    """This class is used to store comment data and comment associations.

    Attributes
    ----------
        comments: list
            List of comment data.
        c_info: list
            List of comment associations.

    Usage
    -----
        At first, create an instance of this class.

        ```python
        c_data_list = CommentDataList()
        ```

        Then, add comment data to the list using the add_comment method.

        ```python
        c_data_list.add_comment(comment_data,
                                approval_step_id,
                                approval_after_completion_id)
        ```

        Next, save the comment data to the database and get the comment IDs.

        ```python
        # Save the comment data to the database
        data = c_data_list.get_comment_data()
        # ... (save the data to the database, and get the comment IDs as comment_ids)

        # Set the comment IDs
        c_data_list.set_comment_ids(comment_ids)
        ```

        Finally, get the comment association data using the get_comment_association_data method.

        ```python
        comment_association = c_data_list.get_comment_association_data()
        ```

        The comment data and comment association data are returned as a list of tuples.
    """
    def __init__(self):
        self.comments = []
        """comment data. ``comments[i]`` contains the following information:
        ```python
        [
            user_name,
            date,
            text,
            deleted
        ]
        ```
        """
        self.c_info = []
        """comment associations. ``c_info[i]`` contains the following information:
        ```python
        [
            comment_id,
            approval_step_id,
            approval_after_completion_id
        ]
        ```
        """

    def add_comment(self,
                    comment_data:dict,
                    approval_step_id:Union[int,None],
                    approval_after_completion_id:Union[int,None]
        ) -> None:
        """Add comment data to the list.

        Args:
            comment_data: Comment data: it must contain the following keys:
                "user_name": User name (str, Not NULL)
                "date": DateTime (str, Not NULL)
                "text": Comment text (str, Not NULL)
                "deleted": Deleted or not (bool, Not Null)
            approval_step_id: Approval step ID (int)
            approval_after_completion_id: Approval after completion ID (int)
        """
        user_name = comment_data['user_name']
        date = comment_data['date']
        text = comment_data['text']
        deleted = comment_data['deleted']

        idx = -1
        for i, _ in enumerate(self.comments):
            if (self.comments[i][0] == user_name
                and self.comments[i][1] == date
                and self.comments[i][2] == text):
                # the comment is already in the list
                idx = i

        if idx == -1:
            self.comments.append([user_name, date, text, deleted])
            self.c_info.append([None, approval_step_id, approval_after_completion_id])
        else:
            # update the comment data (if it is not None)
            if deleted is not None:
                self.comments[idx][3] = deleted

        # update the comment association data
        if approval_step_id is not None:
            self.c_info[idx][1] = approval_step_id
        if approval_after_completion_id is not None:
            self.c_info[idx][2] = approval_after_completion_id

    def set_comment_ids(self, comment_ids:list[int]) -> None:
        """Set comment IDs.

        Args:
            comment_ids: List of comment IDs (int)
        """
        for i, c_id in enumerate(comment_ids):
            self.c_info[i][0] = c_id

    def get_comment_data(self) -> list[tuple]:
        """Return the comment data.

        Returns:
            List of comment data.
        """
        return [tuple(c) for c in self.comments]

    def get_comment_association_data(self) -> list[tuple]:
        """Return the comment association data.
        Before calling this method, make sure that the comment IDs are set.

        Returns:
            List of comment association
        """
        # Assert if comment_ids are not None
        for c_i in self.c_info:
            assert c_i[0] is not None, 'Comment ID is not set.'

        return [tuple(c) for c in self.c_info]

class GenericMasterDataList:
    """This class is used to store generic master data and additional items.

    Attributes
    ----------
        generic_masters: list
            List of generic master data.
        additional_items: list
            List of additional items.

    Usage
    -----
        At first, create an instance of this class.

        ```python
        gm_data_list = GenericMasterDataList()
        ```

        Then, add generic master data to the list using the add_generic_master method.

        ```python
        gm_data_list.add_generic_master(data,
                                        customized_item_id,
                                        table_data_id)
        ```

        Next, save the generic master data to the database and get the generic master IDs.

        ```python
        # Save the generic master data to the database
        data = gm_data_list.get_generic_master_data()
        # ... (save the data to the database, and get the generic master IDs as generic_master_ids)

        # Set the generic master IDs
        gm_data_list.add_additional_item_ids(generic_master_ids)
        ```

        Finally, get the additional items data using the get_additional_items_data method.

        ```python
        additional_items = gm_data_list.get_additional_items_data()
        ```

        The generic master data and additional items data are returned as a list of tuples.
    """
    def __init__(self):
        self.generic_masters = []
        """generic_masters[i] -> [
            record_name,
            record_code,
            customized_item_id,
            table_data_id
        ]"""
        self.additional_items = []
        """additional_items[i] -> [
            generic_master_id,
            [item_value, ...]
        ]"""

    def add_generic_master(self,
                           data:dict,
                           customized_item_id:Union[int,None],
                           table_data_id:Union[int,None]
        ) -> None:
        """Add generic master data to the list.

        Args:
            data: Generic master data: it must contain the following keys:
                "record_name": Record name (str, Not NULL)
                "record_code": Record code (str, Not NULL)
            customized_item_id: Customized item ID (int)
            table_data_id: Table data ID (int)
        """
        record_name = data['record_name']
        record_code = data['record_code']
        additional_items = data['additional_items']

        idx = -1
        for i, _ in enumerate(self.generic_masters):
            if (self.generic_masters[i][0] == record_name and
                self.generic_masters[i][1] == record_code and
                self.additional_items[i][1] == additional_items):
                # the generic master is already in the list
                idx = i

        if idx == -1:
            self.generic_masters.append([record_name, record_code,
                                         customized_item_id, table_data_id])
            self.additional_items.append([None, additional_items])
        else:
            # update the generic master data (if it is not None)
            if customized_item_id is not None:
                self.generic_masters[idx][2] = customized_item_id
            if table_data_id is not None:
                self.generic_masters[idx][3] = table_data_id

    def add_additional_item_ids(self, generic_master_ids:list[int]):
        """Add additional item IDs.

        Args:
            generic_master_ids: List of generic master IDs (int)
            The length of the list must be the same as the length of the generic master data.
        """
        for i, gm_id in enumerate(generic_master_ids):
            self.additional_items[i][0] = gm_id

    def get_generic_master_data(self) -> list[tuple]:
        """Return the generic master data.

        Returns:
            List of generic master data.
        """
        return [tuple(g) for g in self.generic_masters]

    def get_additional_items_data(self) -> list[tuple]:
        """Return the additional items data.

        Returns:
            List of additional items data.
            [[generic_master_id, [item_value, ...]], ...]
        """
        return self.additional_items
