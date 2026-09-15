import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import datetime
import os
import re
import urllib.parse

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
                count_podvoz INTEGER DEFAULT 0,
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

def create_order(user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz):
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute('''
            INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'новый')
        ''', (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz))
    else:
        cur.execute('''
            INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'новый')
        ''', (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz))
    conn.commit()
    conn.close()

def get_user_orders_today(user_id):
    today = datetime.date.today().isoformat()
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute('''
            SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz
            FROM orders
            WHERE user_id = ? AND order_date = ?
        ''', (user_id, today))
    else:
        cur.execute('''
            SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz
            FROM orders
            WHERE user_id = %s AND order_date = %s
        ''', (user_id, today))
    rows = cur.fetchall()
    conn.close()
    return rows

def update_order_count(order_id, category, delta):
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    try:
        if db_type == "sqlite":
            cur.execute(f"SELECT {category} FROM orders WHERE id = ?", (order_id,))
            row = cur.fetchone()
            if not row:
                return False
            new_val = max(0, row[0] + delta)
            cur.execute(f"UPDATE orders SET {category} = ? WHERE id = ?", (new_val, order_id))
        else:
            cur.execute(f"SELECT {category} FROM orders WHERE id = %s", (order_id,))
            row = cur.fetchone()
            if not row:
                return False
            new_val = max(0, row[0] + delta)
            cur.execute(f"UPDATE orders SET {category} = %s WHERE id = %s", (new_val, order_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка обновления: {e}")
        return False
    finally:
        conn.close()

def delete_order(order_id):
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    try:
        if db_type == "sqlite":
            cur.execute("DELETE FROM orders WHERE id = ?", (order_id,))
        else:
            cur.execute("DELETE FROM orders WHERE id = %s", (order_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка удаления: {e}")
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
def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("🌅 Завтрак", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("🌞 Обед", color=VkKeyboardColor.SECONDARY)
    keyboard.add_line()
    keyboard.add_button("✏️ Мои заказы", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("📋 Отчёт", color=VkKeyboardColor.POSITIVE)
    return keyboard.get_keyboard()

def get_date_keyboard():
    keyboard = VkKeyboard(one_time=True)
    keyboard.add_button("Сегодня", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("Завтра", color=VkKeyboardColor.PRIMARY)
    keyboard.add_line()
    keyboard.add_button("Послезавтра", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

def get_edit_keyboard(order_id):
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("💳 +1", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("💳 -1", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("🆓 +1", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("🆓 -1", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("⭐ +1", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("⭐ -1", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("♿ +1", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("♿ -1", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("🚌 +1", color=VkKeyboardColor.POSITIVE)
    keyboard.add_button("🚌 -1", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_line()
    keyboard.add_button("🗑 Удалить заказ", color=VkKeyboardColor.NEGATIVE)
    keyboard.add_button("🔙 Назад", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

temp_data = {}

def send(vk, user_id, message, keyboard=None):
    params = {
        'user_id': user_id,
        'message': message,
        'random_id': 0
    }
    if keyboard:
        params['keyboard'] = keyboard
    vk.messages.send(**params)

def show_my_orders(vk, from_id, user_id):
    orders = get_user_orders_today(user_id)
    if not orders:
        send(vk, from_id, "У тебя нет заказов на сегодня.", get_main_keyboard())
        return
    
    reply = "📋 ТВОИ ЗАКАЗЫ НА СЕГОДНЯ:\n\n"
    for o in orders:
        order_id, class_name, meal_type, cp, cb, cs, co, cpz = o
        total = cp + cb + cs + co + cpz
        reply += f"#{order_id} 🏫 {class_name} ({meal_type}): {total} чел.\n"
        reply += f"  💳{cp} 🆓{cb} ⭐{cs} ♿{co} 🚌{cpz}\n\n"
    reply += "Напиши номер заказа (#ID) чтобы изменить его."
    send(vk, from_id, reply, get_main_keyboard())

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
            send(vk, from_id, 
                 "👋 Привет! Ты можешь заказывать питание на класс.\n\nВыбери действие на клавиатуре 👇",
                 get_main_keyboard())
            return

        user_id = user_data[0]

        # === ОТЧЁТ ===
        if msg_lower.startswith("отчёт") or msg_lower.startswith("!стафф") or msg == "📋 Отчёт":
            staff_ids = [523723395]
            if from_id not in staff_ids:
                send(vk, from_id, "Доступ запрещён.", get_main_keyboard())
                return
            
            conn, db_type = get_db_connection()
            cur = conn.cursor()
            if db_type == "sqlite":
                cur.execute('''SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz, status FROM orders WHERE order_date = DATE('now')''')
            else:
                cur.execute('''SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz, status FROM orders WHERE order_date = CURRENT_DATE''')
            rows = cur.fetchall()
            conn.close()
            
            if not rows:
                send(vk, from_id, "Заказов на сегодня нет.", get_main_keyboard())
                return
            
            breakfast, lunch = [], []
            for row in rows:
                (class_name, meal_type, cp, cb, cs, co, cpz, status) = row
                if meal_type == "завтрак":
                    breakfast.append(row)
                else:
                    lunch.append(row)
            
            reply = ""
            btotal = 0
            if breakfast:
                reply += "🌅 ЗАВТРАКИ:\n"
                for row in breakfast:
                    (class_name, meal_type, cp, cb, cs, co, cpz, status) = row
                    total = cp + cb + cs + co + cpz
                    btotal += total
                    parts = []
                    if cp: parts.append(f"💳{cp}")
                    if cb: parts.append(f"🆓{cb}")
                    if cs: parts.append(f"⭐{cs}")
                    if co: parts.append(f"♿{co}")
                    if cpz: parts.append(f"🚌{cpz}")
                    reply += f"🏫 {class_name}: {' + '.join(parts)} = {total}\n"
                reply += f"ИТОГО: {btotal} чел.\n\n"
            else:
                reply += "🌅 ЗАВТРАКИ: нет\n\n"
            
            ltotal = 0
            if lunch:
                reply += "🌞 ОБЕДЫ:\n"
                for row in lunch:
                    (class_name, meal_type, cp, cb, cs, co, cpz, status) = row
                    total = cp + cb + cs + co + cpz
                    ltotal += total
                    parts = []
                    if cp: parts.append(f"💳{cp}")
                    if cb: parts.append(f"🆓{cb}")
                    if cs: parts.append(f"⭐{cs}")
                    if co: parts.append(f"♿{co}")
                    if cpz: parts.append(f"🚌{cpz}")
                    reply += f"🏫 {class_name}: {' + '.join(parts)} = {total}\n"
                reply += f"ИТОГО: {ltotal} чел.\n\n"
            else:
                reply += "🌞 ОБЕДЫ: нет\n\n"
            
            reply += f"👥 ВСЕГО: {btotal + ltotal} чел."
            send(vk, from_id, reply, get_main_keyboard())
            return

        # === МОИ ЗАКАЗЫ ===
        if msg == "✏️ Мои заказы" or msg_lower.startswith("мои заказы"):
            show_my_orders(vk, from_id, user_id)
            return

        # === РЕДАКТИРОВАНИЕ ЗАКАЗА ===
        if from_id in temp_data and temp_data[from_id].get("step") == "editing":
            order_id = temp_data[from_id]["order_id"]
            
            if msg == "🔙 Назад":
                del temp_data[from_id]
                send(vk, from_id, "Главное меню:", get_main_keyboard())
                return
            
            if msg == "🗑 Удалить заказ":
                if delete_order(order_id):
                    del temp_data[from_id]
                    send(vk, from_id, "✅ Заказ удалён.", get_main_keyboard())
                else:
                    send(vk, from_id, "❌ Ошибка удаления.", get_main_keyboard())
                return
            
            categories = {
                "💳 +1": ("count_plat", 1),
                "💳 -1": ("count_plat", -1),
                "🆓 +1": ("count_bes", 1),
                "🆓 -1": ("count_bes", -1),
                "⭐ +1": ("count_svo", 1),
                "⭐ -1": ("count_svo", -1),
                "♿ +1": ("count_ovz", 1),
                "♿ -1": ("count_ovz", -1),
                "🚌 +1": ("count_podvoz", 1),
                "🚌 -1": ("count_podvoz", -1),
            }
            
            if msg in categories:
                cat, delta = categories[msg]
                if update_order_count(order_id, cat, delta):
                    conn, db_type = get_db_connection()
                    cur = conn.cursor()
                    if db_type == "sqlite":
                        cur.execute("SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE id = ?", (order_id,))
                    else:
                        cur.execute("SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE id = %s", (order_id,))
                    row = cur.fetchone()
                    conn.close()
                    
                    if row:
                        cn, mt, cp, cb, cs, co, cpz = row
                        total = cp + cb + cs + co + cpz
                        reply = (
                            f"📝 ЗАКАЗ #{order_id}\n\n"
                            f"🏫 Класс: {cn}\n"
                            f"🍽 Приём: {mt}\n\n"
                            f"💳 Платники: {cp}\n"
                            f"🆓 Бесплатники: {cb}\n"
                            f"⭐ СВО: {cs}\n"
                            f"♿ ОВЗ: {co}\n"
                            f"🚌 Подвоз: {cpz}\n\n"
                            f"👥 Всего: {total} чел.\n\n"
                            f"Что изменить?"
                        )
                        send(vk, from_id, reply, get_edit_keyboard(order_id))
                else:
                    send(vk, from_id, "❌ Ошибка обновления.", get_main_keyboard())
                return
            
            if msg.startswith("#") or msg.isdigit():
                new_id = int(msg.replace("#", ""))
                temp_data[from_id]["order_id"] = new_id
                send(vk, from_id, f"📝 Редактируешь заказ #{new_id}", get_edit_keyboard(new_id))
                return

        # === ВЫБОР ЗАКАЗА ДЛЯ РЕДАКТИРОВАНИЯ ===
        if msg.startswith("#") or (msg.isdigit() and len(msg) <= 5):
            order_id = int(msg.replace("#", ""))
            temp_data[from_id] = {"step": "editing", "order_id": order_id}
            send(vk, from_id, f"📝 Редактируешь заказ #{order_id}\n\nЧто изменить?", get_edit_keyboard(order_id))
            return

        # === БЫСТРЫЕ КНОПКИ ===
        if msg == "🌅 Завтрак":
            temp_data[from_id] = {"step": "class_name", "meal_type": "завтрак"}
            send(vk, from_id, "🏫 Заказ на ЗАВТРАК.\n\nНапиши название класса (например: 9А)", None)
            return
        if msg == "🌞 Обед":
            temp_data[from_id] = {"step": "class_name", "meal_type": "обед"}
            send(vk, from_id, "🏫 Заказ на ОБЕД.\n\nНапиши название класса (например: 9А)", None)
            return

        # === ДИАЛОГ ===
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
                temp_data[from_id]["step"] = "counts"
                send(vk, from_id,
                     "👥 Шаг 3. Напиши количество по категориям через запятую:\n\n"
                     "ПЛАТНИКИ, БЕСПЛАТНИКИ, СВО, ОВЗ, ПОДВОЗ\n\n"
                     "Пример: 10, 5, 2, 1, 3",
                     None)
                return
            
            if step == "counts":
                try:
                    parts = [int(p.strip()) for p in msg.split(',')]
                    if len(parts) != 5:
                        send(vk, from_id, "Нужно 5 чисел: платники, бесплатники, СВО, ОВЗ, подвоз.\nПример: 10, 5, 2, 1, 3", None)
                        return
                    cp, cb, cs, co, cpz = parts
                    if min(parts) < 0:
                        send(vk, from_id, "Количество не может быть отрицательным.", None)
                        return
                    if sum(parts) == 0:
                        send(vk, from_id, "Укажи хотя бы одного ученика.", None)
                        return
                    
                    class_name = temp_data[from_id]["class_name"]
                    date_str = temp_data[from_id]["date"]
                    meal_type = temp_data[from_id]["meal_type"]
                    
                    create_order(user_id, class_name, date_str, meal_type, cp, cb, cs, co, cpz)
                    
                    total = sum(parts)
                    reply = (
                        f"✅ ЗАКАЗ ОФОРМЛЕН!\n\n"
                        f"Класс: {class_name}\n"
                        f"Дата: {date_str}\n"
                        f"Приём: {meal_type}\n"
                        f"💳 Платников: {cp}\n"
                        f"🆓 Бесплатников: {cb}\n"
                        f"⭐ СВО: {cs}\n"
                        f"♿ ОВЗ: {co}\n"
                        f"🚌 Подвоз: {cpz}\n"
                        f"Всего: {total} чел.\n\n"
                        f"Можешь изменить заказ в разделе «✏️ Мои заказы»"
                    )
                    send(vk, from_id, reply, get_main_keyboard())
                    del temp_data[from_id]
                except ValueError:
                    send(vk, from_id, "Ошибка! Пиши 5 чисел через запятую. Пример: 10, 5, 2, 1, 3", None)
                return

        # === FALLBACK ===
        send(vk, from_id,
             "📌 Выбери действие на клавиатуре 👇",
             get_main_keyboard())

    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        try:
            send(vk, from_id, "Произошла ошибка. Попробуй ещё раз.", get_main_keyboard())
        except:
            pass

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