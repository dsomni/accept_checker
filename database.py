"""Contains MongoDB database class instances"""

import motor.motor_asyncio
import asyncio

from local_secrets import SECRETS_MANAGER


class Database:
    """Manages database stuff"""

    def _connect(self):
        self.client = motor.motor_asyncio.AsyncIOMotorClient(
            SECRETS_MANAGER.get_connection_string()
        )
        self.client.get_io_loop = asyncio.get_running_loop
        self.database = self.client.Accept

    def __init__(self) -> None:
        self._connect()

    def get_collection(self, collection_name: str):
        """Returns requested collection

        Args:
            collection_name (str): collection name
        """

        return self.database[collection_name]

    async def find_one(
        self, collection_name: str, match_dict: dict, filter_dict: dict = {}
    ):
        """Returns one element from collection

        Args:
            collection_name (str): collection name
            match_dict (dict): match dictionary
            filter_dict (dict): filter dictionary

        Returns:
            dict: result
        """

        collection = self.get_collection(collection_name)

        return await collection.find_one(match_dict, filter_dict)

    async def delete_one(self, collection_name: str, match_dict: dict):
        """Deletes one element from collection

        Args:
            collection_name (str): collection name
            match_dict (dict): match dictionary

        Returns:
            dict: result
        """

        collection = self.get_collection(collection_name)

        return await collection.delete_one(match_dict)

    async def insert_one(self, collection_name: str, element: dict):
        """Inserts one element to collection

        Args:
            collection_name (str): collection name
            element (dict): element to insert

        Returns:
            dict: result
        """

        collection = self.get_collection(collection_name)

        return await collection.insert_one(element)

    async def update_one(
        self,
        collection_name: str,
        match_dict: dict,
        update_dict: dict,
        upsert: bool = False,
    ):
        """Updates one element from collection

        Args:
            collection_name (str): collection name
            match_dict (dict): match dictionary
            update_dict (dict): update dictionary
            upsert (bool): upsert value

        Returns:
            dict: result
        """

        collection = self.get_collection(collection_name)

        return await collection.update_one(match_dict, update_dict, upsert)


DATABASE = Database()
