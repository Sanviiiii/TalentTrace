"""
db_manager.py
─────────────
Singleton DatabaseConnection class.

What Singleton means here:
  No matter how many times you call DatabaseConnection(),
  you always get THE SAME connection object — not a new one.
  This prevents opening 1000 connections when 1000 users hit
  the Streamlit app at once.

Usage:
    from backend.db_manager import DatabaseConnection
    db = DatabaseConnection()
    results = db.fetch_all("SELECT * FROM Employees")
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

load_dotenv()   # reads .env file for credentials


class DatabaseConnection:
    """
    Singleton MySQL connection manager.
    One instance, one connection, reused everywhere.
    """

    _instance   = None   # holds the single class instance
    _connection = None   # holds the actual MySQL connection

    # ── Singleton: __new__ runs before __init__ ──────────────
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    # ── Connect ───────────────────────────────────────────────
    def connect(self, database: str = "hr_oltp"):
        """
        Open a connection to the given schema.
        Credentials are read from environment variables / .env
        """
        try:
            if self._connection and self._connection.is_connected():
                # Already connected — switch database if needed
                self._connection.database = database
                return

            self._connection = mysql.connector.connect(
                host     = os.getenv("DB_HOST",     "localhost"),
                port     = int(os.getenv("DB_PORT", "3306")),
                user     = os.getenv("DB_USER",     "root"),
                password = os.getenv("DB_PASSWORD", ""),
                database = database,
                autocommit = False,          # we control commits manually
            )
            print(f"[DB] Connected to MySQL → {database}")

        except Error as e:
            print(f"[DB ERROR] Connection failed: {e}")
            raise

    # ── Disconnect ────────────────────────────────────────────
    def disconnect(self):
        try:
            if self._connection and self._connection.is_connected():
                self._connection.close()
                print("[DB] Connection closed.")
        except Error as e:
            print(f"[DB ERROR] Disconnect failed: {e}")

    # ── Switch schema (OLTP ↔ OLAP) ──────────────────────────
    def use_database(self, database: str):
        try:
            self._connection.database = database
        except Error as e:
            print(f"[DB ERROR] Could not switch to {database}: {e}")
            raise

    # ── Execute a write query (INSERT / UPDATE / DELETE) ──────
    def execute(self, query: str, params: tuple = None) -> int:
        """
        Run a write query. Returns last inserted row ID.
        Commits on success, rolls back on failure.
        """
        cursor = None
        try:
            cursor = self._connection.cursor()
            cursor.execute(query, params or ())
            self._connection.commit()
            return cursor.lastrowid

        except Error as e:
            self._connection.rollback()
            print(f"[DB ERROR] Execute failed:\n  Query : {query}\n  Params: {params}\n  Error : {e}")
            raise

        finally:
            if cursor:
                cursor.close()

    # ── Execute many rows at once (bulk INSERT) ───────────────
    def execute_many(self, query: str, data: list) -> int:
        """
        Bulk insert. Returns number of rows affected.
        """
        cursor = None
        try:
            cursor = self._connection.cursor()
            cursor.executemany(query, data)
            self._connection.commit()
            return cursor.rowcount

        except Error as e:
            self._connection.rollback()
            print(f"[DB ERROR] Bulk execute failed: {e}")
            raise

        finally:
            if cursor:
                cursor.close()

    # ── Fetch one row ─────────────────────────────────────────
    def fetch_one(self, query: str, params: tuple = None) -> dict | None:
        """
        Returns a single row as a dict, or None.
        """
        cursor = None
        try:
            cursor = self._connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            return cursor.fetchone()

        except Error as e:
            print(f"[DB ERROR] fetch_one failed: {e}")
            raise

        finally:
            if cursor:
                cursor.close()

    # ── Fetch all rows ────────────────────────────────────────
    def fetch_all(self, query: str, params: tuple = None) -> list[dict]:
        """
        Returns all matching rows as a list of dicts.
        """
        cursor = None
        try:
            cursor = self._connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            return cursor.fetchall()

        except Error as e:
            print(f"[DB ERROR] fetch_all failed: {e}")
            raise

        finally:
            if cursor:
                cursor.close()

    # ── Call a stored procedure ───────────────────────────────
    def call_procedure(self, proc_name: str, args: tuple = ()):
        """
        Calls a MySQL stored procedure.
        """
        cursor = None
        try:
            cursor = self._connection.cursor()
            cursor.callproc(proc_name, args)
            self._connection.commit()
            print(f"[DB] Procedure '{proc_name}' executed successfully.")

        except Error as e:
            self._connection.rollback()
            print(f"[DB ERROR] Procedure '{proc_name}' failed: {e}")
            raise

        finally:
            if cursor:
                cursor.close()

    # ── Health check ──────────────────────────────────────────
    def is_alive(self) -> bool:
        try:
            return self._connection is not None and self._connection.is_connected()
        except Exception:
            return False
