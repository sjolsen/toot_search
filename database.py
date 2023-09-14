from collections.abc import Iterator
import dataclasses
import os
import pickle
import sqlite3
from typing import Optional

from status import Status


@dataclasses.dataclass
class Database:
    """SQLite store for Status dicts."""
    path: str

    def create(self, *, recreate: bool = False):
        """Initialize the database tables."""
        if os.path.exists(self.path):
            if recreate:
                os.unlink(self.path)
            else:
                return
        with sqlite3.connect(self.path) as connection:
            c = connection.cursor()
            c.executescript("""
                CREATE TABLE status(
                    id INTEGER NOT NULL PRIMARY KEY,
                    pickled BLOB NOT NULL
                );
            """)

    def max_id(self) -> Optional[str]:
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            c = connection.cursor()
            c.execute('SELECT MAX(id) FROM status')
            row = c.fetchone()
            if row is None:
                return None
            return row['MAX(id)']

    def get(self, id: str) -> Status:
        """Look up a status by id."""
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            c = connection.cursor()
            c.execute('SELECT pickled FROM status WHERE id = ?', (id,))
            row = c.fetchone()
            if row is None:
                raise KeyError(id)
            return Status(pickle.loads(row['pickled']))

    def insert(self, status: Status):
        """Insert a status into the store."""
        with sqlite3.connect(self.path) as connection:
            c = connection.cursor()
            c.execute('INSERT INTO status(id, pickled) VALUES(?, ?)',
                      (status.id, pickle.dumps(status.raw)))

    def items(self) -> Iterator[tuple[str, Status]]:
        """List stored statuses by id."""
        with sqlite3.connect(self.path) as connection:
            connection.row_factory = sqlite3.Row
            c = connection.cursor()
            for row in c.execute('SELECT * FROM status'):
                id = row['id']
                status = Status(pickle.loads(row['pickled']))
                yield id, status
