import psycopg2
from config import DATABASE_URL


def get_db_connection():
    if not DATABASE_URL:
        raise Exception("Missing DATABASE_URL in .env")

    return psycopg2.connect(DATABASE_URL)