import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import datetime
import os
import re
import urllib.parse
import time

# === КОНФИГ ===
VK_TOKEN = os.environ.get("VK_TOKEN", "vk1.a.z1AGhRJTlOfwdx4ldltGvv10FPkpmfgUHproUb6uREpo0Ao2TH8PCldeXPDFY7O7qVVkd2NdhCtOd1EJ321WsxAXw_BfL8U13lkhK3JC77rUvMuHAhqiaGB4VPMFnMvb9qhEjWXyXwzf4RtQIshOIxxFbKUJUjaEQgX9aouqhvaHYM0zvVLzTDE_9qEmIlFVIE7x7oGrqNuTYDWXGj2T4A")
GROUP_ID = 241386335
STAFF_IDS = [523723395, 768610229, 165518301, 424711270, 157860178]
CREATOR_IDS = [523723395, 768610229]

def get_db_connection():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        import sqlite3
        db_path = os.environ.get("DB_PATH", "/data/canteen.db")
        return sqlite3.connect(db_path), "sqlite"
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
        cur.execute('''CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, vk_id BIGINT UNIQUE, full_name TEXT, department TEXT)''')
        cur.execute('''CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, user_id INTEGER, class_name TEXT, order_date DATE, meal_type TEXT, count_plat INTEGER DEFAULT 0, count_bes INTEGER DEFAULT 0, count_svo INTEGER DEFAULT 0, count_ovz INTEGER DEFAULT 0, count_podvoz INTEGER DEFAULT 0, names_plat TEXT DEFAULT '', names_bes TEXT DEFAULT '', names_svo TEXT DEFAULT '', names_ovz TEXT DEFAULT '', names_podvoz TEXT DEFAULT '', status TEXT DEFAULT 'новый')''')
        for col, col_type in [("count_podvoz", "INTEGER DEFAULT 0"), ("names_plat", "TEXT DEFAULT ''"), ("names_bes", "TEXT DEFAULT ''"), ("names_svo", "TEXT DEFAULT ''"), ("names_ovz", "TEXT DEFAULT ''"), ("names_podvoz", "TEXT DEFAULT ''")]:
            try: cur.execute(f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col} {col_type}")
            except: pass
    conn.commit(); conn.close()
    print("✅ База данных инициализирована")

def add_user(vk_id, name, dept="не указан"):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    if db_type == "sqlite": cur.execute("INSERT OR IGNORE INTO users (vk_id, full_name, department) VALUES (?, ?, ?)", (vk_id, name, dept))
    else: cur.execute("INSERT INTO users (vk_id, full_name, department) VALUES (%s, %s, %s) ON CONFLICT (vk_id) DO NOTHING", (vk_id, name, dept))
    conn.commit(); conn.close()

def get_user(vk_id):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    if db_type == "sqlite": cur.execute("SELECT id, full_name FROM users WHERE vk_id = ?", (vk_id,))
    else: cur.execute("SELECT id, full_name FROM users WHERE vk_id = %s", (vk_id,))
    row = cur.fetchone(); conn.close(); return row

def create_order(user_id, cn, dt, mt, cp, cb, cs, co, cpz, np, nb, ns, no, npz):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute("INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz, names_plat, names_bes, names_svo, names_ovz, names_podvoz, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?, 'новый')", (user_id, cn, dt, mt, cp, cb, cs, co, cpz, np, nb, ns, no, npz))
    else:
        cur.execute("INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz, names_plat, names_bes, names_svo, names_ovz, names_podvoz, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, 'новый')", (user_id, cn, dt, mt, cp, cb, cs, co, cpz, np, nb, ns, no, npz))
    conn.commit(); conn.close()

def delete_order(oid):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    try:
        if db_type == "sqlite": cur.execute("DELETE FROM orders WHERE id = ?", (oid,))
        else: cur.execute("DELETE FROM orders WHERE id = %s", (oid,))
        conn.commit(); return True
    except Exception as e:
        print(f"❌ {e}"); return False
    finally: conn.close()

def get_user_orders_today(uid):
    today = datetime.date.today().isoformat()
    conn, db_type = get_db_connection(); cur = conn.cursor()
    if db_type == "sqlite": cur.execute("SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE user_id = ? AND order_date = ?", (uid, today))
    else: cur.execute("SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE user_id = %s AND order_date = %s", (uid, today))
    rows = cur.fetchall(); conn.close(); return rows

def get_all_orders_today():
    today = datetime.date.today().isoformat()
    conn, db_type = get_db_connection(); cur = conn.cursor()
    if db_type == "sqlite": cur.execute("SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = ? ORDER BY class_name", (today,))
    else: cur.execute("SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = %s ORDER BY class_name", (today,))
    rows = cur.fetchall(); conn.close(); return rows

def get_order_names(oid):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    if db_type == "sqlite": cur.execute("SELECT names_plat, names_bes, names_svo, names_ovz, names_podvoz FROM orders WHERE id = ?", (oid,))
    else: cur.execute("SELECT names_plat, names_bes, names_svo, names_ovz, names_podvoz FROM orders WHERE id = %s", (oid,))
    row = cur.fetchone(); conn.close(); return row

def update_order_names(oid, cat, ns, cnt):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    try:
        if db_type == "sqlite": cur.execute(f"UPDATE orders SET names_{cat} = ?, count_{cat} = ? WHERE id = ?", (ns, cnt, oid))
        else: cur.execute(f"UPDATE orders SET names_{cat} = %s, count_{cat} = %s WHERE id = %s", (ns, cnt, oid))
        conn.commit(); return True
    except Exception as e:
        print(f"❌ {e}"); return False
    finally: conn.close()

def parse_date(text):
    text = text.lower().strip()
    if text == "сегодня": return datetime.date.today().isoformat()
    elif text == "завтра": return (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    elif text == "послезавтра": return (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
    else:
        match = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', text)
        if match:
            try: return datetime.date(int(match.group(1)), int(match.group(2)), int(match.group(3))).isoformat()
            except: return None
    return None

def clean_names(text):
    if not text: return []
    parts = [n.strip() for n in text.split(',')]
    return [p for p in parts if p and p not in ['-', '—', '–', '0', 'нет', 'Нет']]

def get_main_keyboard(from_id):
    k = VkKeyboard(one_time=False)
    k.add_button("🌅 Завтрак", color=VkKeyboardColor.SECONDARY)
    k.add_button("🌞 Обед", color=VkKeyboardColor.SECONDARY)
    k.add_line()
    k.add_button("✏️ Мои заказы", color=VkKeyboardColor.SECONDARY)
    if from_id in STAFF_IDS or from_id in CREATOR_IDS:
        k.add_button("📋 Отчёт", color=VkKeyboardColor.POSITIVE)
        k.add_line()
        k.add_button("🛠 Редактировать", color=VkKeyboardColor.PRIMARY)
    return k.get_keyboard()

def get_date_keyboard():
    k = VkKeyboard(one_time=True)
    k.add_button("Сегодня", color=VkKeyboardColor.PRIMARY)
    k.add_button("Завтра", color=VkKeyboardColor.PRIMARY)
    k.add_line()
    k.add_button("Послезавтра", color=VkKeyboardColor.SECONDARY)
    k.add_button("🔙 Назад", color=VkKeyboardColor.NEGATIVE)
    return k.get_keyboard()

def get_category_keyboard():
    k = VkKeyboard(one_time=True)
    k.add_button("💳 Платники", color=VkKeyboardColor.PRIMARY)
    k.add_button("🆓 Бесплатники", color=VkKeyboardColor.PRIMARY)
    k.add_line()
    k.add_button("⭐ СВО", color=VkKeyboardColor.SECONDARY)
    k.add_button("♿ ОВЗ", color=VkKeyboardColor.SECONDARY)
    k.add_line()
    k.add_button("🚌 Подвоз", color=VkKeyboardColor.SECONDARY)
    k.add_button("✅ Готово", color=VkKeyboardColor.POSITIVE)
    k.add_line()
    k.add_button("🔙 Назад", color=VkKeyboardColor.NEGATIVE)
    return k.get_keyboard()

def get_edit_category_keyboard():
    k = VkKeyboard(one_time=True)
    k.add_button("Платники", color=VkKeyboardColor.PRIMARY)
    k.add_button("Бесплатники", color=VkKeyboardColor.PRIMARY)
    k.add_line()
    k.add_button("СВО", color=VkKeyboardColor.SECONDARY)
    k.add_button("ОВЗ", color=VkKeyboardColor.SECONDARY)
    k.add_line()
    k.add_button("Подвоз", color=VkKeyboardColor.SECONDARY)
    k.add_button("🔙 Назад", color=VkKeyboardColor.NEGATIVE)
    return k.get_keyboard()
    def get_edit_date_keyboard():
        k = VkKeyboard(one_time=True)
        k.add_button("📅 Сегодня", color=VkKeyboardColor.PRIMARY)
        k.add_button("📅 Завтра", color=VkKeyboardColor.PRIMARY)
        k.add_line()
        k.add_button("🔙 Назад", color=VkKeyboardColor.NEGATIVE)
        return k.get_keyboard()

def get_names_action_keyboard(from_id=None):
    k = VkKeyboard(one_time=True)
    k.add_button("➕ Добавить", color=VkKeyboardColor.POSITIVE)
    k.add_button("➖ Удалить", color=VkKeyboardColor.NEGATIVE)
    k.add_line()
    if from_id is not None and from_id in CREATOR_IDS:
        k.add_button("🗑 Удалить заказ", color=VkKeyboardColor.NEGATIVE)
    k.add_button("🔙 Другая категория", color=VkKeyboardColor.SECONDARY)
    return k.get_keyboard()

temp_data = {}

def send(vk, uid, text, kb=None):
    p = {'user_id': uid, 'message': text, 'random_id': 0}
    if kb: p['keyboard'] = kb
    vk.messages.send(**p)

def show_my_orders(vk, uid, user_id):
    rows = get_user_orders_today(user_id)
    if not rows:
        send(vk, uid, "У тебя нет заказов на сегодня.", get_main_keyboard(uid)); return
    rep = "📋 ТВОИ ЗАКАЗЫ НА СЕГОДНЯ:\n\n"
    for o in rows:
        oid, cn, mt, cp, cb, cs, co, cpz = o
        rep += f"#{oid} 🏫 {cn} ({mt}): {cp+cb+cs+co+cpz} чел.\n"
        rep += f"  Платники: {cp} | Бесплатники: {cb} | СВО: {cs} | ОВЗ: {co} | Подвоз: {cpz}\n\n"
    send(vk, uid, rep, get_main_keyboard(uid))
def get_all_orders_by_date(date_str):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute("SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = ? ORDER BY class_name", (date_str,))
    else:
        cur.execute("SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = %s ORDER BY class_name", (date_str,))
    rows = cur.fetchall(); conn.close(); return rows

def show_all_orders(vk, uid):
    rows = get_all_orders_today()
    if not rows:
        send(vk, uid, "Заказов нет.", get_main_keyboard(uid)); return
    rep = "📋 ВСЕ ЗАКАЗЫ НА СЕГОДНЯ:\n\n"
    for r in rows:
        oid, cn, mt, cp, cb, cs, co, cpz = r
        rep += f"#{oid} 🏫 {cn} ({mt}): {cp+cb+cs+co+cpz} чел.\n"
        rep += f"  Платники: {cp} | Бесплатники: {cb} | СВО: {cs} | ОВЗ: {co} | Подвоз: {cpz}\n\n"
    rep += "Напиши номер заказа (#ID), чтобы редактировать."
    send(vk, uid, rep, get_main_keyboard(uid))

def handle_message(event, vk):
    try:
        msg = event.obj.message['text'].strip()
        low = msg.lower()
        uid = event.obj.message['from_id']
        print(f"✅ {uid}: {msg}")
        info = vk.users.get(user_ids=uid)
        name = f"{info[0]['first_name']} {info[0]['last_name']}"
        ud = get_user(uid)
        if not ud:
            add_user(uid, name)
            send(vk, uid, "👋 Привет! Заказывай питание.", get_main_keyboard(uid)); return
        user_id = ud[0]

        if low.startswith("отчёт") or low.startswith("!стафф") or msg == "📋 Отчёт":
            if uid not in STAFF_IDS and uid not in CREATOR_IDS:
                send(vk, uid, "Доступ запрещён.", get_main_keyboard(uid)); return
            conn, db_type = get_db_connection(); cur = conn.cursor()
            if db_type == "sqlite": cur.execute("SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = DATE('now')")
            else: cur.execute("SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = CURRENT_DATE")
            rows = cur.fetchall(); conn.close()
            if not rows:
                send(vk, uid, "Заказов нет.", get_main_keyboard(uid)); return
            bf, ln = [], []
            for row in rows:
                (bf if row[1] == "завтрак" else ln).append(row)
            rep = ""
            btotal = 0
            if bf:
                rep += "🌅 ЗАВТРАКИ:\n"
                for row in bf:
                    cn, mt, cp, cb, cs, co, cpz = row
                    total = cp + cb + cs + co + cpz; btotal += total
                    parts = []
                    if cp: parts.append(f"Платники:{cp}")
                    if cb: parts.append(f"Бесплатники:{cb}")
                    if cs: parts.append(f"СВО:{cs}")
                    if co: parts.append(f"ОВЗ:{co}")
                    if cpz: parts.append(f"Подвоз:{cpz}")
                    rep += f"🏫 {cn}: {' + '.join(parts)} = {total}\n"
                rep += f"ИТОГО: {btotal} чел.\n\n"
            else: rep += "🌅 ЗАВТРАКИ: нет\n\n"
            ltotal = 0
            if ln:
                rep += "🌞 ОБЕДЫ:\n"
                for row in ln:
                    cn, mt, cp, cb, cs, co, cpz = row
                    total = cp + cb + cs + co + cpz; ltotal += total
                    parts = []
                    if cp: parts.append(f"Платники:{cp}")
                    if cb: parts.append(f"Бесплатники:{cb}")
                    if cs: parts.append(f"СВО:{cs}")
                    if co: parts.append(f"ОВЗ:{co}")
                    if cpz: parts.append(f"Подвоз:{cpz}")
                    rep += f"🏫 {cn}: {' + '.join(parts)} = {total}\n"
                rep += f"ИТОГО: {ltotal} чел.\n\n"
            else: rep += "🌞 ОБЕДЫ: нет\n\n"
            rep += f"👥 ВСЕГО: {btotal + ltotal} чел."
            send(vk, uid, rep, get_main_keyboard(uid)); return

        if msg == "✏️ Мои заказы" or low.startswith("мои заказы"):
            show_my_orders(vk, uid, user_id); return

        if msg == "🛠 Редактировать":
            if uid not in STAFF_IDS and uid not in CREATOR_IDS:
                send(vk, uid, "Доступ запрещён.", get_main_keyboard(uid)); return
            temp_data[uid] = {"step": "edit_date"}
            send(vk, uid, "📅 На какую дату смотреть заказы?", get_edit_date_keyboard()); return
        if uid in temp_data and temp_data[uid].get("step") == "edit_date":
            if msg == "📅 Сегодня":
                date_str = datetime.date.today().isoformat()
                label = "СЕГОДНЯ"
            elif msg == "📅 Завтра":
                date_str = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
                label = "ЗАВТРА"
            elif msg == "🔙 Назад":
                del temp_data[uid]
                send(vk, uid, "Меню:", get_main_keyboard(uid)); return
            else:
                send(vk, uid, "Выбери дату кнопкой:", get_edit_date_keyboard()); return
            del temp_data[uid]
            rows = get_all_orders_by_date(date_str)
            if not rows:
                send(vk, uid, f"Заказов на {label} нет.", get_main_keyboard(uid)); return
            rep = f"📋 ВСЕ ЗАКАЗЫ НА {label}:\n\n"
            for r in rows:
                oid, cn, mt, cp, cb, cs, co, cpz = r
                rep += f"#{oid} 🏫 {cn} ({mt}): {cp+cb+cs+co+cpz} чел.\n"
                rep += f"  Платники: {cp} | Бесплатники: {cb} | СВО: {cs} | ОВЗ: {co} | Подвоз: {cpz}\n\n"
            rep += "Напиши #ID заказа для редактирования."
            send(vk, uid, rep, get_main_keyboard(uid)); return
        if uid in temp_data and temp_data[uid].get("step", "").startswith("se"):
            if uid not in STAFF_IDS and uid not in CREATOR_IDS:
                send(vk, uid, "Доступ запрещён.", get_main_keyboard(uid)); del temp_data[uid]; return
            step = temp_data[uid]["step"]; oid = temp_data[uid]["oid"]
            if step == "se_cat":
                if msg == "🔙 Назад":
                    del temp_data[uid]; send(vk, uid, "Меню:", get_main_keyboard(uid)); return
                cmap = {"Платники":"plat","Бесплатники":"bes","СВО":"svo","ОВЗ":"ovz","Подвоз":"podvoz"}
                if msg in cmap:
                    temp_data[uid]["cat"] = cmap[msg]; temp_data[uid]["step"] = "se_act"
                    nr = get_order_names(oid)
                    idx = {"plat":0,"bes":1,"svo":2,"ovz":3,"podvoz":4}[cmap[msg]]
                    cur = nr[idx] or "—"
                    send(vk, uid, f"Категория: {msg}\n\nТекущие фамилии:\n{cur}\n\nЧто сделать?", get_names_action_keyboard(uid)); return
                send(vk, uid, "Выбери категорию:", get_edit_category_keyboard()); return
            if step == "se_act":
                if msg == "🔙 Другая категория":
                    temp_data[uid]["step"] = "se_cat"; send(vk, uid, "Выбери категорию:", get_edit_category_keyboard()); return
                if msg == "➕ Добавить":
                    temp_data[uid]["step"] = "se_add"; send(vk, uid, "Напиши ФАМИЛИИ через запятую для ДОБАВЛЕНИЯ:", None); return
                if msg == "➖ Удалить":
                    temp_data[uid]["step"] = "se_rem"; send(vk, uid, "Напиши ФАМИЛИИ через запятую для УДАЛЕНИЯ:", None); return
                if msg == "🗑 Удалить заказ":
                    if uid not in CREATOR_IDS:
                        send(vk, uid, "❌ Только создатель может удалять.", get_main_keyboard(uid)); return
                    if delete_order(oid):
                        del temp_data[uid]; send(vk, uid, "✅ Заказ удалён.", get_main_keyboard(uid))
                    else: send(vk, uid, "❌ Ошибка.", get_main_keyboard(uid))
                    return
                send(vk, uid, "Выбери действие:", get_names_action_keyboard(uid)); return
            if step == "se_add":
                cat = temp_data[uid]["cat"]; nr = get_order_names(oid)
                idx = {"plat":0,"bes":1,"svo":2,"ovz":3,"podvoz":4}[cat]
                lst = clean_names(nr[idx] or "")
                new = clean_names(msg)
                for n in new:
                    if n not in lst: lst.append(n)
                ns = ", ".join(lst); cnt = len(lst)
                if update_order_names(oid, cat, ns, cnt):
                    send(vk, uid, f"✅ Добавлено {len(new)}. Теперь {cnt} чел.:\n{ns}", get_main_keyboard(uid))
                else: send(vk, uid, "❌ Ошибка.", get_main_keyboard(uid))
                del temp_data[uid]; return
            if step == "se_rem":
                cat = temp_data[uid]["cat"]; nr = get_order_names(oid)
                idx = {"plat":0,"bes":1,"svo":2,"ovz":3,"podvoz":4}[cat]
                lst = clean_names(nr[idx] or "")
                to_rm = clean_names(msg); rm = []
                for n in to_rm:
                    if n in lst: lst.remove(n); rm.append(n)
                ns = ", ".join(lst); cnt = len(lst)
                if update_order_names(oid, cat, ns, cnt):
                    send(vk, uid, f"✅ Удалено {len(rm)}. Осталось {cnt}:\n{ns if ns else '—'}", get_main_keyboard(uid))
                else: send(vk, uid, "❌ Ошибка.", get_main_keyboard(uid))
                del temp_data[uid]; return

        if msg.startswith("#"):
            if uid not in STAFF_IDS and uid not in CREATOR_IDS:
                send(vk, uid, "Только сотрудники.", get_main_keyboard(uid)); return
            oid = int(msg.replace("#", ""))
            temp_data[uid] = {"step": "se_cat", "oid": oid}
            send(vk, uid, f"📝 Редактируешь заказ #{oid}\n\nВыбери категорию:", get_edit_category_keyboard()); return

        if msg == "🌅 Завтрак":
            temp_data[uid] = {"step": "cn", "mt": "завтрак", "hist": []}
            send(vk, uid, "🏫 Заказ на ЗАВТРАК.\n\nНапиши класс (например: 9А)", None); return
        if msg == "🌞 Обед":
            temp_data[uid] = {"step": "cn", "mt": "обед", "hist": []}
            send(vk, uid, "🏫 Заказ на ОБЕД.\n\nНапиши класс (например: 9А)", None); return

        if uid in temp_data:
            step = temp_data[uid].get("step")
            if msg == "🔙 Назад":
                h = temp_data[uid].get("hist", [])
                if not h:
                    del temp_data[uid]; send(vk, uid, "Меню:", get_main_keyboard(uid)); return
                prev = h.pop(); temp_data[uid]["step"] = prev; temp_data[uid]["hist"] = h
                if prev == "cn": send(vk, uid, "🏫 Напиши класс:", None)
                elif prev == "dt": send(vk, uid, "📅 Выбери дату:", get_date_keyboard())
                elif prev == "cat": send(vk, uid, "👥 Выбери категорию:", get_category_keyboard())
                return
            if step == "cn":
                temp_data[uid]["hist"].append("cn")
                temp_data[uid]["cn"] = msg.upper()
                temp_data[uid]["step"] = "dt"
                send(vk, uid, "📅 Шаг 2. Выбери дату:", get_date_keyboard()); return
            if step == "dt":
                dt = parse_date(msg)
                if not dt: send(vk, uid, "Не понял дату:", get_date_keyboard()); return
                temp_data[uid]["hist"].append("dt"); temp_data[uid]["dt"] = dt; temp_data[uid]["step"] = "cat"
                for c in ["plat","bes","svo","ovz","podvoz"]: temp_data[uid][f"n_{c}"] = []
                send(vk, uid, "👥 Шаг 3. Выбери категорию и напиши ФАМИЛИИ.\nЕсли человек не нужен — `-` или `0`.", get_category_keyboard()); return
            if step == "cat":
                if msg == "✅ Готово":
                    tot = sum(len(temp_data[uid][f"n_{c}"]) for c in ["plat","bes","svo","ovz","podvoz"])
                    if tot == 0: send(vk, uid, "Ты не ввёл ни одной фамилии.", get_category_keyboard()); return
                    cn = temp_data[uid]["cn"]; dt = temp_data[uid]["dt"]; mt = temp_data[uid]["mt"]
                    vals = {}
                    for c in ["plat","bes","svo","ovz","podvoz"]:
                        vals[c] = ", ".join(temp_data[uid][f"n_{c}"])
                        vals[f"c_{c}"] = len(temp_data[uid][f"n_{c}"])
                    create_order(user_id, cn, dt, mt, vals["c_plat"], vals["c_bes"], vals["c_svo"], vals["c_ovz"], vals["c_podvoz"], vals["plat"], vals["bes"], vals["svo"], vals["ovz"], vals["podvoz"])
                    rep = f"✅ ЗАКАЗ ОФОРМЛЕН!\n\nКласс: {cn}\nДата: {dt}\nПриём: {mt}\n\n"
                    rep += f"Платники ({vals['c_plat']}): {vals['plat'] or '—'}\n"
                    rep += f"Бесплатники ({vals['c_bes']}): {vals['bes'] or '—'}\n"
                    rep += f"СВО ({vals['c_svo']}): {vals['svo'] or '—'}\n"
                    rep += f"ОВЗ ({vals['c_ovz']}): {vals['ovz'] or '—'}\n"
                    rep += f"Подвоз ({vals['c_podvoz']}): {vals['podvoz'] or '—'}\n"
                    send(vk, uid, rep, get_main_keyboard(uid)); del temp_data[uid]; return
                cmap = {"💳 Платники":"plat","🆓 Бесплатники":"bes","⭐ СВО":"svo","♿ ОВЗ":"ovz","🚌 Подвоз":"podvoz"}
                if msg in cmap:
                    temp_data[uid]["cur"] = cmap[msg]
                    send(vk, uid, f"Напиши ФАМИЛИИ для {msg}:\nЕсли не нужен — `-` или `0`", None); return
                if "cur" in temp_data[uid]:
                    c = temp_data[uid]["cur"]; new = clean_names(msg)
                    if new: temp_data[uid][f"n_{c}"].extend(new)
                    cnt = len(temp_data[uid][f"n_{c}"])
                    names = {"plat":"Платники","bes":"Бесплатники","svo":"СВО","ovz":"ОВЗ","podvoz":"Подвоз"}
                    if new: send(vk, uid, f"✅ {len(new)} в {names[c]}. Всего: {cnt}", get_category_keyboard())
                    else: send(vk, uid, f"`-` не считается. В {names[c]}: {cnt}", get_category_keyboard())
                    return
                send(vk, uid, "Выбери категорию:", get_category_keyboard()); return

        send(vk, uid, "📌 Выбери действие:", get_main_keyboard(uid))
    except Exception as e:
        print(f"❌ {e}")
        try: send(vk, uid, "Ошибка. Попробуй ещё.", get_main_keyboard(uid))
        except: pass

if __name__ == "__main__":
    init_db()
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)
    print("🤖 SWILL BOT ACTIVE")
    print("Жду сообщений...")
    while True:
        try:
            for event in longpoll.listen():
                if event.type == VkBotEventType.MESSAGE_NEW:
                    handle_message(event, vk)
        except Exception as e:
            print(f"⚠️ {e}")
            time.sleep(10)
            try: longpoll = VkBotLongPoll(vk_session, GROUP_ID); print("✅ Переподключено")
            except: time.sleep(30)
