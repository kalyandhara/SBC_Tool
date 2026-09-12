import sqlite3
conn = sqlite3.connect(r'D:\SBC_Tool - Copy\data\profiles.db')
cur = conn.cursor()
cur.execute('SELECT name, sql FROM sqlite_master WHERE type="table"')
for row in cur.fetchall():
    print(row)
conn.close()