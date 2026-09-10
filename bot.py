import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import datetime
import os
import re
import urllib.parse
import sys

# === КОНФИГ ===
VK_TOKEN = "vk1.a.z1AGhRJTlOfwdx4ldltGvv10FPkpmfgUHproUb6uREpo0Ao2TH8PCldeXPDFY7O7qVVkd2NdhCtOd1EJ321WsxAXw_BfL8U13lkhK3JC77rUvMuHAhqiaGB4VPMFnMvb9qhEjWXyXwzf4RtQIshOIxxFbKUJUjaEQgX9aouqhvaHYM0zvVLzTDE_9qEmIlFVIE7x7oGrqNuTYDWXGj2T4A"
GROUP_ID = 241386335

# === ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ ===
def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        import sqlite3
        return sqlite3.connect("canteen.db"), "sqlite"
    
    import psycopg2
    result = urllib.parse.urlparse(db_url)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port
    )
    return conn, "postgresql"

def init_db():
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    
    if db_type == "sqlite":
        cur.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vk_id INTEGER UNIQUE,
                full_name TEXT,
                department TEXT
            );
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
            );
        ''')
    else:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                vk_id BIGINT UNIQUE,
                full_name TEXT,
                department TEXT
            );
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                class_name TEXT,
                order_date DATE,
                meal_type TEXT,
                count_plat INTEGER DEFAULT 0,
                count_bes INTEGER DEFAULT 0,
                count_svo INTEGER DEFAULT 0,
                count_ovz INTEGER DEFAULT 0,
                status TEXT DEFAULT 'новый'
            );
        ''')
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def add_user(vk_id, name, dept="не указан"):
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute("INSERT OR IGNORE INTO users (vk_id, full_name, department) VALUES (?, ?, ?)", (vk_id, name, dept))
    else:
        cur.execute("INSERT INTO users (vk_id, full_name, department) VALUES (%s, %s, %s) ON CONFLICT (vk_id) DO NOTHING", (vk_id, name, dept))
    conn.commit()
    conn.close()

def get_user(vk_id):
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute("SELECT id, full_name FROM users WHERE vk_id = ?", (vk_id,))
    else:
        cur.execute("SELECT id, full_name FROM users WHERE vk_id = %s", (vk_id,))
    row = cur.fetchone()
    conn.close()
    return row

def create_order(user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz):
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute('''
            INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'новый')
        ''', (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz))
    else:
        cur.execute('''
            INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'новый')
        ''', (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz))
    conn.commit()
    conn.close()

def parse_date(text):
    text = text.lower().strip()
    if text == "сегодня":
        return datetime.date.today().isoformat()
    elif text == "завтра":
        return (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    elif text == "послезавтра":
        return (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
    else:
        match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', text)
        if match:
            try:
                d = datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                return d.isoformat()
            except:
                return None
    return None

temp_data = {}

def handle_message(event, vk):
    try:
        msg = event.obj.message['text'].lower().strip()
        from_id = event.obj.message['from_id']
        print(f"✅ Получено сообщение от {from_id}: {msg}")

        user_info = vk.users.get(user_ids=from_id)
        name = f"{user_info[0]['first_name']} {user_info[0]['last_name']}"
        
        user_data = get_user(from_id)
        if not user_data:
            add_user(from_id, name)
            vk.messages.send(
                user_id=from_id,
                message="👋 Привет! Ты можешь заказывать питание на класс.\n\nКоманды:\n- заказать класс — сделать заказ на класс\n- отчёт — для сотрудников столовой",
                random_id=0
            )
            return

        user_id = user_data[0]

        if msg.startswith("отчёт") or msg.startswith("!стафф"):
            staff_ids = [523723395, 768610229]
            if from_id not in staff_ids:
                vk.messages.send(user_id=from_id, message="Доступ запрещён.", random_id=0)
                return
            
            conn, db_type = get_db_connection()
            cur = conn.cursor()
            if db_type == "sqlite":
                cur.execute('''
                    SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, status
                    FROM orders
                    WHERE order_date = DATE('now')
                ''')
            else:
                cur.execute('''
                    SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, status
                    FROM orders
                    WHERE order_date = CURRENT_DATE
                ''')
            rows = cur.fetchall()
            conn.close()
            
            if not rows:
                vk.messages.send(user_id=from_id, message="Заказов на сегодня нет.", random_id=0)
                return
            
            reply = "📋 ЗАКАЗЫ НА СЕГОДНЯ:\n\n"
            total_plat = total_bes = total_svo = total_ovz = 0
            for row in rows:
                class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, status = row
                reply += f"🏫 {class_name} ({meal_type}): "
                parts = []
                if count_plat > 0:
                    parts.append(f"💳 {count_plat} платн.")
                    total_plat += count_plat
                if count_bes > 0:
                    parts.append(f"🆓 {count_bes} бесплатн.")
                    total_bes += count_bes
                if count_svo > 0:
                    parts.append(f"⭐ {count_svo} СВО")
                    total_svo += count_svo
                if count_ovz > 0:
                    parts.append(f"♿ {count_ovz} ОВЗ")
                    total_ovz += count_ovz
                reply += " + ".join(parts) + f" – {status}\n"
            
            total_people = total_plat + total_bes + total_svo + total_ovz
            reply += f"\n👥 Всего: {total_people} чел."
            reply += f"\n💳 {total_plat} | 🆓 {total_bes} | ⭐ {total_svo} | ♿ {total_ovz}"
            vk.messages.send(user_id=from_id, message=reply, random_id=0)
            return

        if msg.startswith("заказать класс"):
            temp_data[from_id] = {"step": "class_name"}
            vk.messages.send(
                user_id=from_id,
                message="🏫 ЗАКАЗ НА КЛАСС\n\nШаг 1. Напиши название класса (например: 9А)",
                random_id=0
            )
            return

        if from_id in temp_data:
            step = temp_data[from_id].get("step")
            
            if step == "class_name":
                temp_data[from_id]["class_name"] = msg.upper()
                temp_data[from_id]["step"] = "date"
                vk.messages.send(
                    user_id=from_id,
                    message="📅 Шаг 2. Напиши дату:\n- сегодня\n- завтра\n- или ГГГГ-ММ-ДД",
                    random_id=0
                )
                return
            
            if step == "date":
                date_str = parse_date(msg)
                if not date_str:
                    vk.messages.send(user_id=from_id, message="Неверный формат даты.", random_id=0)
                    return
                temp_data[from_id]["date"] = date_str
                temp_data[from_id]["step"] = "meal_type"
                vk.messages.send(
                    user_id=from_id,
                    message="🍽 Шаг 3. Выбери приём пищи:\n- завтрак\n- обед",
                    random_id=0
                )
                return
            
            if step == "meal_type":
                if msg not in ["завтрак", "обед"]:
                    vk.messages.send(user_id=from_id, message="Напиши: завтрак или обед", random_id=0)
                    return
                temp_data[from_id]["meal_type"] = msg
                temp_data[from_id]["step"] = "counts"
                vk.messages.send(
                    user_id=from_id,
                    message="👥 Шаг 4. Напиши количество по категориям:\n\nПЛАТНИКИ, БЕСПЛАТНИКИ, СВО, ОВЗ\n\nПример: 10, 5, 2, 1",
                    random_id=0
                )
                return
            
            if step == "counts":
                try:
                    parts = [int(p.strip()) for p in msg.split(',')]
                    if len(parts) != 4:
                        vk.messages.send(user_id=from_id, message="Нужно 4 числа.", random_id=0)
                        return
                    count_plat, count_bes, count_svo, count_ovz = parts
                    if count_plat < 0 or count_bes < 0 or count_svo < 0 or count_ovz < 0:
                        vk.messages.send(user_id=from_id, message="Количество не может быть отрицательным.", random_id=0)
                        return
                    if count_plat + count_bes + count_svo + count_ovz == 0:
                        vk.messages.send(user_id=from_id, message="Укажи хотя бы одного ученика.", random_id=0)
                        return
                    
                    class_name = temp_data[from_id]["class_name"]
                    date_str = temp_data[from_id]["date"]
                    meal_type = temp_data[from_id]["meal_type"]
                    
                    create_order(user_id, class_name, date_str, meal_type, count_plat, count_bes, count_svo, count_ovz)
                    
                    total = count_plat + count_bes + count_svo + count_ovz
                    reply = f"✅ ЗАКАЗ ОФОРМЛЕН!\n\nКласс: {class_name}\nДата: {date_str}\nПриём: {meal_type}\nПлатников: {count_plat}\nБесплатников: {count_bes}\nСВО: {count_svo}\nОВЗ: {count_ovz}\nВсего: {total} чел."
                    vk.messages.send(user_id=from_id, message=reply, random_id=0)
                    del temp_data[from_id]
                    
                except ValueError:
                    vk.messages.send(user_id=from_id, message="Ошибка! Пиши 4 числа через запятую.", random_id=0)
                return

        vk.messages.send(
            user_id=from_id,
            message="📌 Команды:\n- заказать класс — сделать заказ на класс\n- отчёт — для сотрудников столовой",
            random_id=0
        )

    except Exception as e:
        print(f"❌ ОШИБКА: {e}")

if __name__ == "__main__":
    init_db()
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("🤖 SWILL BOT ACTIVE")
    print("Жду сообщений...")
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            handle_message(event, vk)