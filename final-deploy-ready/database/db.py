import mysql.connector
from mysql.connector import Error
from config import Config

def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            database=Config.DB_NAME,
            ssl_ca=Config.DB_SSL_CA
        )
        return conn
    except Error as e:
        print(f"[Database Connection Error]: {e}")
        return None