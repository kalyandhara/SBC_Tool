import os
os.remove(r'D:\SBC_Tool - Copy\data\profiles.db')
print('Removed profiles.db')
from sbc.db import _bootstrap, get_db
_bootstrap()
conn = get_db()
cur = conn.cursor()
cur.execute('SELECT name FROM sqlite_master WHERE type="table"')
print('Tables:', [r[0] for r in cur.fetchall()])
conn.close()