import os
import psycopg2
import psycopg2.extras


def conectar_pg():
    url = os.environ.get("DATABASE_URL")
    conn = psycopg2.connect(url)
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    return conn
