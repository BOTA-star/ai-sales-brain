import psycopg2
from psycopg2.extensions import connection

from config import DATABASE_URL, DB_CONNECT_TIMEOUT

def get_db_connection() -> connection:
    if not DATABASE_URL:
        raise RuntimeError(
            "Missing DATABASE_URL in .env"
        )

    return psycopg2.connect(
        DATABASE_URL,
        connect_timeout=DB_CONNECT_TIMEOUT,
    )