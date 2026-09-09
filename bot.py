import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import sqlite3
import datetime
import re

VK_TOKEN = "vk1.a.z1AGhRJTlOfwdx4ldltGvv10FPkpmfgUHproUb6uREpo0Ao2TH8PCldeXPDFY7O7qVVkd2NdhCtOd1EJ321WsxAXw_BfL8U13lkhK3JC77rUvMuHAhqiaGB4VPMFnMvb9qhEjWXyXwzf4RtQIshOIxxFbKUJUjaEQgX9aouqhvaHYM0zvVLzTDE_9qEmIlFVIE7x7oGrqNuTYDWXGj2T4A"
GROUP_ID = 241386335

DB_NAME = "canteen.db"
temp_data = {}

def init_db():
    conn = sqlite3.connect(DB_NAME)
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

def get_user(vk_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, full_name FROM users WHERE vk_id = ?", (vk_id,))
    row = cur.fetchone()
    conn.close()
    return row

def add_user(vk_id, name, dept="не указан"):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (vk_id, full_name, department) VALUES (?, ?, ?)", (vk_id, name, dept))
    conn.commit()
    conn.close()

def create_order(user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'новый')
    ''', (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz))
    conn.commit()
    conn.close()

def get_orders_for_staff(date_filter=None, meal_filter=None):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    query = '''
        SELECT u.full_name, o.class_name, o.meal_type, o.count_plat, o.count_bes, o.count_svo, o.count_ovz, o.status, o.order_date
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE 1=1
    '''
    params = []
    if date_filter:
        query += " AND DATE(o.order_date) = ?"
        params.append(date_filter)
    if meal_filter:
        query += " AND o.meal_type = ?"
        params.append(meal_filter)
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows

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

def handle_message(event, vk):
    global temp_data
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

        # === ОТЧЁТ ДЛЯ СОТРУДНИКОВ ===
        if msg.startswith("отчёт") or msg.startswith("!стафф"):
            staff_ids = [523723395]
            if from_id not in staff_ids:
                vk.messages.send(user_id=from_id, message="Доступ запрещён.", random_id=0)
                return
            parts = msg.split()
            date_str = None
            meal_filter = None
            label = "сегодня"
            if len(parts) > 1:
                date_str = parse_date(parts[1])
                if date_str:
                    label = parts[1]
                else:
                    meal_filter = parts[1]
                    if len(parts) > 2:
                        date_str = parse_date(parts[2])
                        if date_str:
                            label = parts[2]
            if not date_str:
                date_str = datetime.date.today().isoformat()
            
            rows = get_orders_for_staff(date_str, meal_filter)
            if not rows:
                reply = f"Заказов на {label} нет."
            else:
                reply = f"📋 ЗАКАЗЫ НА {label}:\n\n"
                total_plat = 0
                total_bes = 0
                total_svo = 0
                total_ovz = 0
                total_people = 0
                for row in rows:
                    # row: full_name, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, status, order_date
                    reply += f"🏫 {row[1]} ({row[2]}): "
                    parts_list = []
                    if row[3] > 0:
                        parts_list.append(f"💳 {row[3]} платн.")
                        total_plat += row[3]
                    if row[4] > 0:
                        parts_list.append(f"🆓 {row[4]} бесплатн.")
                        total_bes += row[4]
                    if row[5] > 0:
                        parts_list.append(f"⭐ {row[5]} СВО")
                        total_svo += row[5]
                    if row[6] > 0:
                        parts_list.append(f"♿ {row[6]} ОВЗ")
                        total_ovz += row[6]
                    reply += " + ".join(parts_list)
                    total_people += row[3] + row[4] + row[5] + row[6]
                    reply += f" – {row[7]}\n"
                reply += f"\n👥 Всего человек: {total_people}"
                reply += f"\n💳 Платников: {total_plat} | 🆓 Бесплатников: {total_bes} | ⭐ СВО: {total_svo} | ♿ ОВЗ: {total_ovz}"
            vk.messages.send(user_id=from_id, message=reply, random_id=0)
            return

        # === ЗАКАЗ НА КЛАСС ===
        if msg.startswith("заказать класс") or msg.startswith("заказать класс"):
            temp_data[from_id] = {"step": "class_name", "date": datetime.date.today().isoformat()}
            vk.messages.send(
                user_id=from_id,
                message="🏫 ЗАКАЗ НА КЛАСС\n\nШаг 1. Напиши название класса (например: 9А)",
                random_id=0
            )
            return

        if from_id in temp_data:
            step = temp_data[from_id].get("step")
            
            # Шаг 1: Название класса
            if step == "class_name":
                temp_data[from_id]["class_name"] = msg.upper()
                temp_data[from_id]["step"] = "date"
                vk.messages.send(
                    user_id=from_id,
                    message="📅 Шаг 2. Напиши дату:\n- сегодня\n- завтра\n- или ГГГГ-ММ-ДД",
                    random_id=0
                )
                return
            
            # Шаг 2: Дата
            if step == "date":
                date_str = parse_date(msg)
                if not date_str:
                    vk.messages.send(user_id=from_id, message="Неверный формат даты. Попробуй: сегодня, завтра или ГГГГ-ММ-ДД", random_id=0)
                    return
                temp_data[from_id]["date"] = date_str
                temp_data[from_id]["step"] = "meal_type"
                vk.messages.send(
                    user_id=from_id,
                    message="🍽 Шаг 3. Выбери приём пищи:\n- завтрак\n- обед\n\nМожно заказать оба сразу, но пока выбери один. После заказа сможешь заказать второй.",
                    random_id=0
                )
                return
            
            # Шаг 3: Приём пищи
            if step == "meal_type":
                if msg not in ["завтрак", "обед"]:
                    vk.messages.send(user_id=from_id, message="Напиши: завтрак или обед", random_id=0)
                    return
                temp_data[from_id]["meal_type"] = msg
                temp_data[from_id]["step"] = "counts"
                vk.messages.send(
                    user_id=from_id,
                    message="👥 Шаг 4. Напиши количество учеников по категориям в формате:\n\nПЛАТНИКИ, БЕСПЛАТНИКИ, СВО, ОВЗ\n\nПример: 10, 5, 2, 1\n\n(Если кого-то нет, пиши 0)",
                    random_id=0
                )
                return
            
            # Шаг 4: Количество по категориям
            if step == "counts":
                try:
                    parts = [int(p.strip()) for p in msg.split(',')]
                    if len(parts) != 4:
                        vk.messages.send(user_id=from_id, message="Нужно 4 числа: платники, бесплатники, СВО, ОВЗ. Пример: 10, 5, 2, 1", random_id=0)
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
                    reply = f"✅ ЗАКАЗ ОФОРМЛЕН!\n\n"
                    reply += f"Класс: {class_name}\n"
                    reply += f"Дата: {date_str}\n"
                    reply += f"Приём: {meal_type}\n"
                    reply += f"Платников: {count_plat}\n"
                    reply += f"Бесплатников: {count_bes}\n"
                    reply += f"СВО: {count_svo}\n"
                    reply += f"ОВЗ: {count_ovz}\n"
                    reply += f"Всего: {total} чел.\n\n"
                    reply += "Чтобы заказать второй приём (завтрак или обед), напиши снова 'заказать класс'."
                    
                    vk.messages.send(user_id=from_id, message=reply, random_id=0)
                    del temp_data[from_id]
                    
                except ValueError:
                    vk.messages.send(user_id=from_id, message="Ошибка! Пиши 4 числа через запятую. Пример: 10, 5, 2, 1", random_id=0)
                return

        # === ПОМОЩЬ ===
        vk.messages.send(
            user_id=from_id,
            message="📌 Команды:\n- заказать класс — сделать заказ на класс\n- отчёт — для сотрудников столовой (показать заказы)\n- отчёт завтра — заказы на завтра\n- отчёт обед — только обеды\n- отчёт обед завтра — обеды на завтра",
            random_id=0
        )

    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        vk.messages.send(user_id=from_id, message=f"Произошла ошибка. Попробуй ещё раз.", random_id=0)

if __name__ == "__main__":
    init_db()
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("SWILL BOT ACTIVE")
    print("Жду сообщений...")
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            handle_message(event, vk)