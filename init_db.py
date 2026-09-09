import sqlite3
import datetime

conn = sqlite3.connect("canteen.db")
cur = conn.cursor()

cur.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vk_id INTEGER UNIQUE,
    full_name TEXT,
    department TEXT
)
''')

cur.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    class_name TEXT,
    order_date TEXT,
    meal_type TEXT,
    count_plat INTEGER DEFAULT 0,
    count_bes INTEGER DEFAULT 0,
    count_svo INTEGER DEFAULT 0,
    count_ovz INTEGER DEFAULT 0,
    status TEXT DEFAULT 'новый'
)
''')

conn.commit()
conn.close()
print("✅ База создана с новыми полями")