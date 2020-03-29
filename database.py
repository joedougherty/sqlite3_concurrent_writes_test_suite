import sqlite3


PATH_TO_DB = "race_condition.sqlite"


def create_table():
    with sqlite3.connect(PATH_TO_DB) as conn:
        c = conn.cursor()

        c.execute("""DROP TABLE IF EXISTS messages;""")
        conn.commit()

        c.execute(
            """
            CREATE TABLE messages (
                ts DATE DEFAULT (datetime('now','localtime')),
                msg TEXT 
            );
            """
        )
        conn.commit()


def insert_row(record):
    with sqlite3.connect(PATH_TO_DB) as conn:
        c = conn.cursor()

        c.execute(
            """
            INSERT INTO messages 
            (msg) 
            VALUES
            (?);
            """,
            record,
        )
        conn.commit()


def row_count():
    with sqlite3.connect(PATH_TO_DB) as conn:
        c = conn.cursor()
        res = c.execute("""select count(*) from messages;""")
        return res.fetchone()[0]
