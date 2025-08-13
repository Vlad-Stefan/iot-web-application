import sqlite3

conn = sqlite3.connect('valori.db')
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS valori (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        senzor TEXT,
        valoare REAL,
        timestamp TEXT
    )
''')

conn.commit()
conn.close()