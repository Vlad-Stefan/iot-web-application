import mysql.connector
import bcrypt
import os
from dotenv import load_dotenv

load_dotenv()

def get_mysql_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

conn = get_mysql_connection()
cursor = conn.cursor(dictionary=True)

# Selectezi toți utilizatorii care NU au deja parola hash-uită
cursor.execute("SELECT id, password FROM tbl_user")
users = cursor.fetchall()

for user in users:
    if not user["password"].startswith("$2b$"):  # verificăm dacă nu e deja bcrypt
        hashed = bcrypt.hashpw(user["password"].encode('utf-8'), bcrypt.gensalt())
        hashed_str = hashed.decode("utf-8")
        cursor.execute("UPDATE tbl_user SET password = %s WHERE id = %s", (hashed_str, user["id"]))
        print(f"User {user['id']} - parola hash-uită")

conn.commit()
conn.close()
