"""
backend/db_manager.py
"""
import pymysql
from pymysql import Error
from pymysql.cursors import DictCursor
import os
from dotenv import load_dotenv

load_dotenv()

class DatabaseConnection:
    def __init__(self):
        self._connection = None

    def connect(self, database: str = "hr_oltp"):
        try:
            # Close existing connection if one exists before reconnecting
            if self._connection and self._connection.open:
                self._connection.close()

            self._connection = pymysql.connect(
                host       = os.getenv("DB_HOST", "127.0.0.1"),
                port       = int(os.getenv("DB_PORT", "3306")),
                user       = os.getenv("DB_USER", "root"),
                password   = os.getenv("DB_PASSWORD", ""),
                database   = database,
                autocommit = False,
            )
        except Error as e:
            print(f"[DB ERROR] Connection failed: {e}")
            raise

    def disconnect(self):
        if self._connection and self._connection.open:
            self._connection.close()

    def use_database(self, database: str):
        # Perform a clean reconnect to switch databases to prevent packet collisions
        self.connect(database)

    def execute(self, query: str, params: tuple = None) -> int:
        cursor = None
        try:
            cursor = self._connection.cursor()
            cursor.execute(query, params or ())
            self._connection.commit()
            return cursor.lastrowid
        except Error as e:
            self._connection.rollback()
            raise
        finally:
            if cursor: cursor.close()

    def execute_many(self, query: str, data: list) -> int:
        cursor = None
        try:
            cursor = self._connection.cursor()
            cursor.executemany(query, data)
            self._connection.commit()
            return cursor.rowcount
        except Error as e:
            self._connection.rollback()
            raise
        finally:
            if cursor: cursor.close()

    def fetch_one(self, query: str, params: tuple = None) -> dict | None:
        cursor = None
        try:
            cursor = self._connection.cursor(DictCursor)
            cursor.execute(query, params or ())
            return cursor.fetchone()
        except Error as e:
            raise
        finally:
            if cursor: cursor.close()

    def fetch_all(self, query: str, params: tuple = None) -> list[dict]:
        cursor = None
        try:
            cursor = self._connection.cursor(DictCursor)
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except Error as e:
            raise
        finally:
            if cursor: cursor.close()

    def call_procedure(self, proc_name: str, args: tuple = ()):
        cursor = None
        try:
            cursor = self._connection.cursor()
            cursor.callproc(proc_name, args)
            self._connection.commit()
        except Error as e:
            self._connection.rollback()
            raise
        finally:
            if cursor: cursor.close()

    def is_alive(self) -> bool:
        try:
            return self._connection is not None and self._connection.open
        except Exception:
            return Falses