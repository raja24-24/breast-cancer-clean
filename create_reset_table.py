import sqlite3

conn = sqlite3.connect("database.db")
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS reset_tokens (
    email TEXT,
    token TEXT
)
""")

conn.commit()
conn.close()

print("reset_tokens table created successfully")