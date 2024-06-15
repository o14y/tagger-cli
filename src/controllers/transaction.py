from dataclasses import dataclass
import sqlite3

@dataclass
class Txn:
    conn: sqlite3.Connection
    @classmethod
    def begin(cls, conn: sqlite3.Connection) -> 'Txn':
        return cls(conn)
    def __enter__(self) -> sqlite3.Cursor:
        return self.conn.cursor()
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()