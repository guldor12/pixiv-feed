import sqlite3
from textwrap import dedent


def get_db(db_path):
    db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row

    # initialize db if necessary
    db.executescript(
        dedent(
            """
            CREATE TABLE IF NOT EXISTS data (
                key TEXT PRIMARY KEY UNIQUE,
                value TEXT,
                expires INTEGER
            );
            """
        )
    )

    return db
