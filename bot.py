import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import datetime
import os
import re
import urllib.parse
import time

# === КОНФИГ ===
VK_TOKEN = "vk1.a.z1AGhRJTlOfwdx4ldltGvv10FPkpmfgUHproUb6uREpo0Ao2TH8PCldeXPDFY7O7qVVkd2NdhCtOd1EJ321WsxAXw_BfL8U13lkhK3JC77rUvMuHAhqiaGB4VPMFnMvb9qhEjWXyXwzf4RtQIshOIxxFbKUJUjaEQgX9aouqhvaHYM0zvVLzTDE_9qEmIlFVIE7x7oGrqNuTYDWXGj2T4A"
GROUP_ID = 241386335

STAFF_IDS = [523723395]

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
                count_podvoz INTEGER DEFAULT 0,
                names_plat TEXT DEFAULT '',
                names_bes TEXT DEFAULT '',
                names_svo TEXT DEFAULT '',
                names_ovz TEXT DEFAULT '',
                names_podvoz TEXT DEFAULT '',
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
                count_podvoz INTEGER DEFAULT 0,
                names_plat TEXT DEFAULT '',
                names_bes TEXT DEFAULT '',
                names_svo TEXT DEFAULT '',
                names_ovz TEXT DEFAULT '',
                names_podvoz TEXT DEFAULT '',
                status TEXT DEFAULT 'новый'
            );
        ''')
        for col, col_type in [
            ("count_podvoz", "INTEGER DEFAULT 0"),
            ("names_plat", "TEXT DEFAULT ''"),
            ("names_bes", "TEXT DEFAULT ''"),
            ("names_svo", "TEXT DEFAULT ''"),
            ("names_ovz", "TEXT DEFAULT ''"),
            ("names_podvoz", "TEXT DEFAULT ''"),
        ]:
            try:
                cur.execute(f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col} {col_type}")
            except:
                pass
    
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

def create_order(user_id, class_name, order_date, meal_type, cp, cb, cs, co, cpz, np, nb, ns, no, npz):
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute('''
            INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz,
                                names_plat, names_bes, names_svo, names_ovz, names_podvoz, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'новый')
        ''', (user_id, class_name, order_date, meal_type, cp, cb, cs, co, cpz, np, nb, ns, no, npz))
    else:
        cur.execute('''
            INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz,
                                names_plat, names_bes, names_svo, names_ovz, names_podvoz, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'новый')
        ''', (user_id, class_name, order_date, meal_type, cp, cb, cs, co, cpz, np, nb, ns, no, npz))
    conn.commit()
    conn.close()

def get_user_orders_today(user_id):
    today = datetime.date.today().isoformat()
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute('''SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz
                       FROM orders WHERE user_id = ? AND order_date = ?''', (user_id, today))
    else:
        cur.execute('''SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz
                       FROM orders WHERE user_id = %s AND order_date = %s''', (user_id, today))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_all_orders_today():
    today = datetime.date.today().isoformat()
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute('''SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz
                       FROM orders WHERE order_date = ? ORDER BY class_name''', (today,))
    else:
        cur.execute('''SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz
                       FROM orders WHERE order_date = %s ORDER BY class_name''', (today,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_order_names(order_id):
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute("SELECT names_plat, names_bes, names_svo, names_ovz, names_podvoz FROM orders WHERE id = ?", (order_id,))
    else:
        cur.execute("SELECT names_plat, names_bes, names_svo, names_ovz, names_podvoz FROM orders WHERE id = %s", (order_id,))
    row = cur.fetchone()
    conn.close()
    return row

def update_order_names(order_id, category, names_str, count):
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    try:
        if db_type == "sqlite":
            cur.execute(f"UPDATE orders SET names_{category} = ?, count_{category} = ? WHERE id = ?",
                        (names_str, count, order_id))
        else:
            cur.execute(f"UPDATE orders SET names_{category} = %s, count_{category} = %s WHERE id = %s",
                        (names_str, count, order_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False
    finally:
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

# === КЛАВИАТУРЫ ===
def get_main_keyboard(from_id):
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("🌅 Завтрак", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("🌞 Обед", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("✏️ Мои заказы", color=VkKeyboardColor.SECONDARY)
    if from_id in STAFF_IDS:
        keyboard.add_button("📋 Отчёт", color=VkKeyboardColor.POSITIVE)
        keyboard.add_line()
        keyboard.add_button("🛠 Редактировать", color=VkKeyboardColor.PRIMARY)
    return keyboard.get_keyboard()

def get_date_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Сегодня", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Завтра", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("Послезавтра", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_category_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("💳 Платники", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("🆓 Бесплатники", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("⭐ СВО", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("♿ ОВЗ", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("🚌 Подвоз", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("✅ Готово", color=VkKeyboardColor.POSITIVE)
    return keyboard.get_keyboard()

def get_edit_category_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Платники", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Бесплатники", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("СВО", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("ОВЗ", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("Подвоз", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("🔙 Назад", color=VkKeyboardColor.NEGATIVE)
    return keyboard.get_keyboard()

def get_names_action_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("➕ Добавить", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("➖ Удалить", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("🔙 Другая категория", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

temp_data = {}

def send(vk, user_id, message, keyboard=None):
    params = {'user_id': user_id, 'message': message, 'random_id': 0}
    if keyboard:
        params['keyboard'] = keyboard
    vk.messages.send(**params)

def show_my_orders(vk, from_id, user_id):
    orders = get_user_orders_today(user_id)
    if not orders:
        send(vk, from_id, "У тебя нет заказов на сегодня.", get_main_keyboard(from_id))
        return
    reply = "📋 ТВОИ ЗАКАЗЫ НА СЕГОДНЯ:\n\n"
    for o in orders:
        order_id, class_name, meal_type, cp, cb, cs, co, cpz = o
        total = cp + cb + cs + co + cpz
        reply += f"#{order_id} 🏫 {class_name} ({meal_type}): {total} чел.\n"
        reply += f"  Платники: {cp} | Бесплатники: {cb} | СВО: {cs} | ОВЗ: {co} | Подвоз: {cpz}\n\n"
    send(vk, from_id, reply, get_main_keyboard(from_id))

def show_all_orders(vk, from_id):
    rows = get_all_orders_today()
    if not rows:
        send(vk, from_id, "Заказов на сегодня нет.", get_main_keyboard(from_id))
        return
    reply = "📋 ВСЕ ЗАКАЗЫ НА СЕГОДНЯ:\n\n"
    for r in rows:
        order_id, cn, mt, cp, cb, cs, co, cpz = r
        total = cp + cb + cs + co + cpz
        reply += f"#{order_id} 🏫 {cn} ({mt}): {total} чел.\n"
        reply += f"  Платники: {cp} | Бесплатники: {cb} | СВО: {cs} | ОВЗ: {co} | Подвоз: {cpz}\n\n"
    reply += "Напиши номер заказа (#ID), чтобы редактировать."
    send(vk, from_id, reply, get_main_keyboard(from_id))

def handle_message(event, vk):
    try:
        msg = event.obj.message['text'].strip()
        msg_lower = msg.lower()
        from_id = event.obj.message['from_id']
        print(f"✅ Получено сообщение от {from_id}: {msg}")

        user_info = vk.users.get(user_ids=from_id)
        name = f"{user_info[0]['first_name']} {user_info[0]['last_name']}"
        
        user_data = get_user(from_id)
        if not user_data:
            add_user(from_id, name)
            send(vk, from_id, "👋 Привет! Заказывай питание на класс.\n\nВыбери действие 👇", get_main_keyboard(from_id))
            return

        user_id = user_data[0]

        if msg_lower.startswith("отчёт") or msg_lower.startswith("!стафф") or msg == "📋 Отчёт":
            if from_id not in STAFF_IDS:
                send(vk, from_id, "Доступ запрещён.", get_main_keyboard(from_id))
                return
            conn, db_type = get_db_connection()
            cur = conn.cursor()
            if db_type == "sqlite":
                cur.execute('''SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = DATE('now')''')
            else:
                cur.execute('''SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = CURRENT_DATE''')
            rows = cur.fetchall()
            conn.close()
            if not rows:
                send(vk, from_id, "Заказов на сегодня нет.", get_main_keyboard(from_id))
                return
            breakfast, lunch = [], []
            for row in rows:
                if row[1] == "завтрак":
                    breakfast.append(row)
                else:
                    lunch.append(row)
            reply = ""
            btotal = 0
            if breakfast:
                reply += "🌅 ЗАВТРАКИ:\n"
                for row in breakfast:
                    (cn, mt, cp, cb, cs, co, cpz) = row
                    total = cp + cb + cs + co + cpz
                    btotal += total
                    parts = []
                    if cp: parts.append(f"Платники:{cp}")
                    if cb: parts.append(f"Бесплатники:{cb}")
                    if cs: parts.append(f"СВО:{cs}")
                    if co: parts.append(f"ОВЗ:{co}")
                    if cpz: parts.append(f"Подвоз:{cpz}")
                    reply += f"🏫 {cn}: {' + '.join(parts)} = {total}\n"
                reply += f"ИТОГО: {btotal} чел.\n\n"
            else:
                reply += "🌅 ЗАВТРАКИ: нет\n\n"
            ltotal = 0
            if lunch:
                reply += "🌞 ОБЕДЫ:\n"
                for row in lunch:
                    (cn, mt, cp, cb, cs, co, cpz) = row
                    total = cp + cb + cs + co + cpz
                    ltotal += total
                    parts = []
                    if cp: parts.append(f"Платники:{cp}")
                    if cb: parts.append(f"Бесплатники:{cb}")
                    if cs: parts.append(f"СВО:{cs}")
                    if co: parts.append(f"ОВЗ:{co}")
                    if cpz: parts.append(f"Подвоз:{cpz}")
                    reply += f"🏫 {cn}: {' + '.join(parts)} = {total}\n"
                reply += f"ИТОГО: {ltotal} чел.\n\n"
            else:
                reply += "🌞 ОБЕДЫ: нет\n\n"
            reply += f"👥 ВСЕГО: {btotal + ltotal} чел."
            send(vk, from_id, reply, get_main_keyboard(from_id))
            return

        if msg == "✏️ Мои заказы" or msg_lower.startswith("мои заказы"):
            show_my_orders(vk, from_id, user_id)
            return

        if msg == "🛠 Редактировать":
            if from_id not in STAFF_IDS:
                send(vk, from_id, "Доступ запрещён.", get_main_keyboard(from_id))
                return
            show_all_orders(vk, from_id)
            return

        if from_id in temp_data and temp_data[from_id].get("step", "").startswith("staff_edit"):
            if from_id not in STAFF_IDS:
                send(vk, from_id, "Доступ запрещён.", get_main_keyboard(from_id))
                del temp_data[from_id]
                return
            
            step = temp_data[from_id]["step"]
            order_id = temp_data[from_id]["order_id"]

            if step == "staff_edit_category":
                if msg == "🔙 Назад":
                    del temp_data[from_id]
                    send(vk, from_id, "Главное меню:", get_main_keyboard(from_id))
                    return
                cat_map = {"Платники": "plat", "Бесплатники": "bes", "СВО": "svo", "ОВЗ": "ovz", "Подвоз": "podvoz"}
                if msg in cat_map:
                    temp_data[from_id]["category"] = cat_map[msg]
                    temp_data[from_id]["step"] = "staff_edit_action"
                    names_row = get_order_names(order_id)
                    idx = {"plat": 0, "bes": 1, "svo": 2, "ovz": 3, "podvoz": 4}[cat_map[msg]]
                    current_names = names_row[idx] or "—"
                    send(vk, from_id,
                         f"Категория: {msg}\n\nТекущие фамилии:\n{current_names}\n\nЧто сделать?",
                         get_names_action_keyboard())
                    return
                send(vk, from_id, "Выбери категорию кнопкой:", get_edit_category_keyboard())
                return

            if step == "staff_edit_action":
                if msg == "🔙 Другая категория":
                    temp_data[from_id]["step"] = "staff_edit_category"
                    send(vk, from_id, "Выбери категорию:", get_edit_category_keyboard())
                    return
                if msg == "➕ Добавить":
                    temp_data[from_id]["step"] = "staff_edit_add_names"
                    send(vk, from_id, "Напиши ФАМИЛИИ через запятую, которые надо ДОБАВИТЬ:", None)
                    return
                if msg == "➖ Удалить":
                    temp_data[from_id]["step"] = "staff_edit_remove_names"
                    send(vk, from_id, "Напиши ФАМИЛИИ через запятую, которые надо УДАЛИТЬ:", None)
                    return
                send(vk, from_id, "Выбери действие кнопкой:", get_names_action_keyboard())
                return

            if step == "staff_edit_add_names":
                cat = temp_data[from_id]["category"]
                names_row = get_order_names(order_id)
                idx = {"plat": 0, "bes": 1, "svo": 2, "ovz": 3, "podvoz": 4}[cat]
                current = names_row[idx] or ""
                current_list = [n.strip() for n in current.split(',') if n.strip()]
                new_names = [n.strip() for n in msg.split(',') if n.strip()]
                for n in new_names:
                    if n not in current_list:
                        current_list.append(n)
                names_str = ", ".join(current_list)
                count = len(current_list)
                if update_order_names(order_id, cat, names_str, count):
                    send(vk, from_id,
                         f"✅ Добавлено {len(new_names)} чел.\n\nТеперь в категории ({count} чел.):\n{names_str}",
                         get_main_keyboard(from_id))
                else:
                    send(vk, from_id, "❌ Ошибка сохранения.", get_main_keyboard(from_id))
                del temp_data[from_id]
                return

            if step == "staff_edit_remove_names":
                cat = temp_data[from_id]["category"]
                names_row = get_order_names(order_id)
                idx = {"plat": 0, "bes": 1, "svo": 2, "ovz": 3, "podvoz": 4}[cat]
                current = names_row[idx] or ""
                current_list = [n.strip() for n in current.split(',') if n.strip()]
                to_remove = [n.strip() for n in msg.split(',') if n.strip()]
                removed = []
                for n in to_remove:
                    if n in current_list:
                        current_list.remove(n)
                        removed.append(n)
                names_str = ", ".join(current_list)
                count = len(current_list)
                if update_order_names(order_id, cat, names_str, count):
                    send(vk, from_id,
                         f"✅ Удалено {len(removed)} чел.\n\nОсталось ({count} чел.):\n{names_str if names_str else '—'}",
                         get_main_keyboard(from_id))
                else:
                    send(vk, from_id, "❌ Ошибка сохранения.", get_main_keyboard(from_id))
                del temp_data[from_id]
                return

        if msg.startswith("#") or (msg.isdigit() and len(msg) <= 5):
            order_id = int(msg.replace("#", ""))
            if from_id in STAFF_IDS:
                temp_data[from_id] = {"step": "staff_edit_category", "order_id": order_id}
                send(vk, from_id, f"📝 Редактируешь заказ #{order_id}\n\nВыбери категорию:", get_edit_category_keyboard())
            else:
                send(vk, from_id, "Только сотрудники могут редактировать заказы.", get_main_keyboard(from_id))
            return

        if msg == "🌅 Завтрак":
            temp_data[from_id] = {"step": "class_name", "meal_type": "завтрак"}
            send(vk, from_id, "🏫 Заказ на ЗАВТРАК.\n\nНапиши название класса (например: 9А)", None)
            return
        if msg == "🌞 Обед":
            temp_data[from_id] = {"step": "class_name", "meal_type": "обед"}
            send(vk, from_id, "🏫 Заказ на ОБЕД.\n\nНапиши название класса (например: 9А)", None)
            return

        if from_id in temp_data:
            step = temp_data[from_id].get("step")
            
            if step == "class_name":
                temp_data[from_id]["class_name"] = msg.upper()
                temp_data[from_id]["step"] = "date"
                send(vk, from_id, "📅 Шаг 2. Выбери дату:", get_date_keyboard())
                return
            
            if step == "date":
                date_str = parse_date(msg)
                if not date_str:
                    send(vk, from_id, "Не понял дату. Выбери кнопку или напиши ГГГГ-ММ-ДД:", get_date_keyboard())
                    return
                temp_data[from_id]["date"] = date_str
                temp_data[from_id]["step"] = "category"
                temp_data[from_id]["names_plat"] = []
                temp_data[from_id]["names_bes"] = []
                temp_data[from_id]["names_svo"] = []
                temp_data[from_id]["names_ovz"] = []
                temp_data[from_id]["names_podvoz"] = []
                send(vk, from_id,
                     "👥 Шаг 3. Выбери категорию, а потом напиши ФАМИЛИИ через запятую.\n\n"
                     "Пример: Иванов, Петров, Сидоров\n\n"
                     "Когда закончишь — нажми ✅ Готово",
                     get_category_keyboard())
                return
            
            if step == "category":
                if msg == "✅ Готово":
                    total_names = (len(temp_data[from_id]["names_plat"]) + len(temp_data[from_id]["names_bes"]) +
                                   len(temp_data[from_id]["names_svo"]) + len(temp_data[from_id]["names_ovz"]) +
                                   len(temp_data[from_id]["names_podvoz"]))
                    if total_names == 0:
                        send(vk, from_id, "Ты не ввёл ни одной фамилии.", get_category_keyboard())
                        return
                    class_name = temp_data[from_id]["class_name"]
                    date_str = temp_data[from_id]["date"]
                    meal_type = temp_data[from_id]["meal_type"]
                    np = ", ".join(temp_data[from_id]["names_plat"])
                    nb = ", ".join(temp_data[from_id]["names_bes"])
                    ns = ", ".join(temp_data[from_id]["names_svo"])
                    no = ", ".join(temp_data[from_id]["names_ovz"])
                    npz = ", ".join(temp_data[from_id]["names_podvoz"])
                    cp = len(temp_data[from_id]["names_plat"])
                    cb = len(temp_data[from_id]["names_bes"])
                    cs = len(temp_data[from_id]["names_svo"])
                    co = len(temp_data[from_id]["names_ovz"])
                    cpz = len(temp_data[from_id]["names_podvoz"])
                    create_order(user_id, class_name, date_str, meal_type, cp, cb, cs, co, cpz, np, nb, ns, no, npz)
                    total = cp + cb + cs + co + cpz
                    reply = (
                        f"✅ ЗАКАЗ ОФОРМЛЕН!\n\n"
                        f"Класс: {class_name}\nДата: {date_str}\nПриём: {meal_type}\n\n"
                        f"Платники ({cp}): {np if np else '—'}\n"
                        f"Бесплатники ({cb}): {nb if nb else '—'}\n"
                        f"СВО ({cs}): {ns if ns else '—'}\n"
                        f"ОВЗ ({co}): {no if no else '—'}\n"
                        f"Подвоз ({cpz}): {npz if npz else '—'}\n\n"
                        f"👥 Всего: {total} чел."
                    )
                    send(vk, from_id, reply, get_main_keyboard(from_id))
                    del temp_data[from_id]
                    return
                
                if msg == "💳 Платники":
                    temp_data[from_id]["current_category"] = "plat"
                    send(vk, from_id, "Напиши ФАМИЛИИ платников через запятую:", None)
                    return
                if msg == "🆓 Бесплатники":
                    temp_data[from_id]["current_category"] = "bes"
                    send(vk, from_id, "Напиши ФАМИЛИИ бесплатников через запятую:", None)
                    return
                if msg == "⭐ СВО":
                    temp_data[from_id]["current_category"] = "svo"
                    send(vk, from_id, "Напиши ФАМИЛИИ СВО через запятую:", None)
                    return
                if msg == "♿ ОВЗ":
                    temp_data[from_id]["current_category"] = "ovz"
                    send(vk, from_id, "Напиши ФАМИЛИИ ОВЗ через запятую:", None)
                    return
                if msg == "🚌 Подвоз":
                    temp_data[from_id]["current_category"] = "podvoz"
                    send(vk, from_id, "Напиши ФАМИЛИИ подвоза через запятую:", None)
                    return
                
                if "current_category" in temp_data[from_id]:
                    cat = temp_data[from_id]["current_category"]
                    names = [n.strip() for n in msg.split(',') if n.strip()]
                    temp_data[from_id][f"names_{cat}"].extend(names)
                    total_in_cat = len(temp_data[from_id][f"names_{cat}"])
                    cat_names = {"plat": "Платники", "bes": "Бесплатники", "svo": "СВО", "ovz": "ОВЗ", "podvoz": "Подвоз"}
                    send(vk, from_id, f"✅ Добавлено {len(names)} чел. в {cat_names[cat]}.\nВсего: {total_in_cat}\n\nВыбери следующую категорию или нажми ✅ Готово:", get_category_keyboard())
                    return
                
                send(vk, from_id, "Выбери категорию кнопкой ниже:", get_category_keyboard())
                return

        send(vk, from_id, "📌 Выбери действие на клавиатуре 👇", get_main_keyboard(from_id))

    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        try:
            send(vk, from_id, "Произошла ошибка. Попробуй ещё раз.", get_main_keyboard(from_id))
        except:
            pass

if __name__ == "__main__":
    init_db()
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("🤖 SWILL BOT ACTIVE")
    print("Жду сообщений...")
    
    # === ВЕЧНЫЙ ЦИКЛ С ПЕРЕПОДКЛЮЧЕНИЕМ ===
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    handle_message(event, vk)
        except Exception as e:
            print(f"⚠️ Ошибка longpoll: {e}")
            print("Переподключение через 10 секунд...")
            time.sleep(10)
            try:
                longpoll = VkBotLongPoll(vk_session, GROUP_ID)
                print("✅ Переподключено")
            except Exception as e2:
                print(f"❌ Не удалось переподключиться: {e2}")
                time.sleep(30)