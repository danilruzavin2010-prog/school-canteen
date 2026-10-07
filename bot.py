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
        cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, vk_id BIGINT UNIQUE, full_name TEXT, department TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, user_id INTEGER, class_name TEXT, order_date DATE, meal_type TEXT, count_plat INTEGER DEFAULT 0, count_bes INTEGER DEFAULT 0, count_svo INTEGER DEFAULT 0, count_ovz INTEGER DEFAULT 0, count_podvoz INTEGER DEFAULT 0, names_plat TEXT DEFAULT '', names_bes TEXT DEFAULT '', names_svo TEXT DEFAULT '', names_ovz TEXT DEFAULT '', names_podvoz TEXT DEFAULT '', status TEXT DEFAULT 'новый')")
        for col, col_type in [
            ("count_podvoz", "INTEGER DEFAULT 0"),
            ("names_plat", "TEXT DEFAULT ''"),
            ("names_bes", "TEXT DEFAULT ''"),
            ("names_svo", "TEXT DEFAULT ''"),
            ("names_ovz", "TEXT DEFAULT ''"),
            ("names_podvoz", "TEXT DEFAULT ''")
        ]:
            try: cur.execute(f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col} {col_type}")
            except: pass
    conn.commit(); conn.close()
    print("✅ База данных инициализирована")

def add_user(vk_id, name, dept="не указан"):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute("INSERT OR IGNORE INTO users (vk_id, full_name, department) VALUES (?, ?, ?)", (vk_id, name, dept))
    else:
        cur.execute("INSERT INTO users (vk_id, full_name, department) VALUES (%s, %s, %s) ON CONFLICT (vk_id) DO NOTHING", (vk_id, name, dept))
    conn.commit(); conn.close()

def get_user(vk_id):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute("SELECT id, full_name FROM users WHERE vk_id = ?", (vk_id,))
    else:
        cur.execute("SELECT id, full_name FROM users WHERE vk_id = %s", (vk_id,))
    row = cur.fetchone(); conn.close(); return row

def create_order(user_id, class_name, order_date, meal_type, cp, cb, cs, co, cpz, np, nb, ns, no, npz):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute("INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz, names_plat, names_bes, names_svo, names_ovz, names_podvoz, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'новый')", (user_id, class_name, order_date, meal_type, cp, cb, cs, co, cpz, np, nb, ns, no, npz))
    else:
        cur.execute("INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz, names_plat, names_bes, names_svo, names_ovz, names_podvoz, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'новый')", (user_id, class_name, order_date, meal_type, cp, cb, cs, co, cpz, np, nb, ns, no, npz))
    conn.commit(); conn.close()

def get_user_orders_today(user_id):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    today = datetime.date.today().isoformat()
    if db_type == "sqlite":
        cur.execute("SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE user_id = ? AND order_date = ?", (user_id, today))
    else:
        cur.execute("SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE user_id = %s AND order_date = %s", (user_id, today))
    rows = cur.fetchall(); conn.close(); return rows

def get_all_orders_today():
    conn, db_type = get_db_connection(); cur = conn.cursor()
    today = datetime.date.today().isoformat()
    if db_type == "sqlite":
        cur.execute("SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = ? ORDER BY class_name", (today,))
    else:
        cur.execute("SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = %s ORDER BY class_name", (today,))
    rows = cur.fetchall(); conn.close(); return rows

def get_order_names(order_id):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    if db_type == "sqlite":
        cur.execute("SELECT names_plat, names_bes, names_svo, names_ovz, names_podvoz FROM orders WHERE id = ?", (order_id,))
    else:
        cur.execute("SELECT names_plat, names_bes, names_svo, names_ovz, names_podvoz FROM orders WHERE id = %s", (order_id,))
    row = cur.fetchone(); conn.close(); return row

def update_order_names(order_id, category, names_str, count):
    conn, db_type = get_db_connection(); cur = conn.cursor()
    try:
        if db_type == "sqlite":
            cur.execute(f"UPDATE orders SET names_{category} = ?, count_{category} = ? WHERE id = ?", (names_str, count, order_id))
        else:
            cur.execute(f"UPDATE orders SET names_{category} = %s, count_{category} = %s WHERE id = %s", (names_str, count, order_id))
        conn.commit(); return True
    except: return False
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
    if from_id in STAFF_IDS:
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

def get_names_action_keyboard():
    k = VkKeyboard(one_time=True)
    k.add_button("➕ Добавить", color=VkKeyboardColor.POSITIVE)
    k.add_button("➖ Удалить", color=VkKeyboardColor.NEGATIVE)
    k.add_line()
    k.add_button("🔙 Другая категория", color=VkKeyboardColor.SECONDARY)
    return k.get_keyboard()

temp_data = {}

def send(vk, user_id, message, keyboard=None):
    params = {'user_id': user_id, 'message': message, 'random_id': 0}
    if keyboard: params['keyboard'] = keyboard
    vk.messages.send(**params)

def show_my_orders(vk, from_id, user_id):
    orders = get_user_orders_today(user_id)
    if not orders:
        send(vk, from_id, "У тебя нет заказов на сегодня.", get_main_keyboard(from_id)); return
    reply = "📋 ТВОИ ЗАКАЗЫ НА СЕГОДНЯ:\n\n"
    for o in orders:
        order_id, cn, mt, cp, cb, cs, co, cpz = o
        reply += f"#{order_id} 🏫 {cn} ({mt}): {cp+cb+cs+co+cpz} чел.\n"
        reply += f"  Платники: {cp} | Бесплатники: {cb} | СВО: {cs} | ОВЗ: {co} | Подвоз: {cpz}\n\n"
    send(vk, from_id, reply, get_main_keyboard(from_id))

def show_all_orders(vk, from_id):
    rows = get_all_orders_today()
    if not rows:
        send(vk, from_id, "Заказов на сегодня нет.", get_main_keyboard(from_id)); return
    reply = "📋 ВСЕ ЗАКАЗЫ НА СЕГОДНЯ:\n\n"
    for r in rows:
        order_id, cn, mt, cp, cb, cs, co, cpz = r
        reply += f"#{order_id} 🏫 {cn} ({mt}): {cp+cb+cs+co+cpz} чел.\n"
        reply += f"  Платники: {cp} | Бесплатники: {cb} | СВО: {cs} | ОВЗ: {co} | Подвоз: {cpz}\n\n"
    reply += "Напиши #ID заказа для редактирования."
    send(vk, from_id, reply, get_main_keyboard(from_id))

def handle_message(event, vk):
    try:
        msg = event.obj.message['text'].strip()
        low = msg.lower()
        uid = event.obj.message['from_id']
        print(f"✅ Получено сообщение от {uid}: {msg}")
        info = vk.users.get(user_ids=uid)
        name = f"{info[0]['first_name']} {info[0]['last_name']}"
        ud = get_user(uid)
        if not ud:
            add_user(uid, name)
            send(vk, uid, "👋 Привет! Заказывай питание.", get_main_keyboard(uid)); return
        user_id = ud[0]

        if low.startswith("отчёт") or low.startswith("!стафф") or msg == "📋 Отчёт":
            if uid not in STAFF_IDS:
                send(vk, uid, "Доступ запрещён.", get_main_keyboard(uid)); return
            conn, db_type = get_db_connection(); cur = conn.cursor()
            if db_type == "sqlite":
                cur.execute("SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = DATE('now')")
            else:
                cur.execute("SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = CURRENT_DATE")
            rows = cur.fetchall(); conn.close()
            if not rows:
                send(vk, uid, "Заказов нет.", get_main_keyboard(uid)); return
            bf, ln = [], []
            for row in rows:
                (bf if row[1] == "завтрак" else ln).append(row)
            reply = ""
            bt = lt = 0
            for title, group in [("🌅 ЗАВТРАКИ", bf), ("🌞 ОБЕДЫ", ln)]:
                if not group:
                    reply += f"{title}: нет\n\n"; continue
                reply += f"{title}:\n"; tot = 0
                for row in group:
                    cn, mt, cp, cb, cs, co, cpz = row
                    s = cp + cb + cs + co + cpz; tot += s
                    parts = []
                    if cp: parts.append(f"Платники:{cp}")
                    if cb: parts.append(f"Бесплатники:{cb}")
                    if cs: parts.append(f"СВО:{cs}")
                    if co: parts.append(f"ОВЗ:{co}")
                    if cpz: parts.append(f"Подвоз:{cpz}")
                    reply += f"🏫 {cn}: {' + '.join(parts)} = {s}\n"
                reply += f"ИТОГО: {tot} чел.\n\n"
                if title.startswith("🌅"): bt = tot
                else: lt = tot
            reply += f"👥 ВСЕГО: {bt + lt} чел."
            send(vk, uid, reply, get_main_keyboard(uid)); return

        if msg == "✏️ Мои заказы" or low.startswith("мои заказы"):
            show_my_orders(vk, uid, user_id); return

        if msg == "🛠 Редактировать":
            if uid not in STAFF_IDS:
                send(vk, uid, "Доступ запрещён.", get_main_keyboard(uid)); return
            show_all_orders(vk, uid); return

        if uid in temp_data and temp_data[uid].get("step", "").startswith("staff_edit"):
            if uid not in STAFF_IDS:
                send(vk, uid, "Доступ запрещён.", get_main_keyboard(uid)); del temp_data[uid]; return
            step = temp_data[uid]["step"]; oid = temp_data[uid]["oid"]
            if step == "staff_edit_category":
                if msg == "🔙 Назад":
                    del temp_data[uid]; send(vk, uid, "Меню:", get_main_keyboard(uid)); return
                cmap = {"Платники":"plat","Бесплатники":"bes","СВО":"svo","ОВЗ":"ovz","Подвоз":"podvoz"}
                if msg in cmap:
                    temp_data[uid]["cat"] = cmap[msg]; temp_data[uid]["step"] = "staff_edit_action"
                    nr = get_order_names(oid)
                    idx = {"plat":0,"bes":1,"svo":2,"ovz":3,"podvoz":4}[cmap[msg]]
                    cur = nr[idx] or "—"
                    send(vk, uid, f"Категория: {msg}\n\nФамилии:\n{cur}\n\nЧто сделать?", get_names_action_keyboard()); return
                send(vk, uid, "Выбери категорию:", get_edit_category_keyboard()); return
            if step == "staff_edit_action":
                if msg == "🔙 Другая категория":
                    temp_data[uid]["step"] = "staff_edit_category"; send(vk, uid, "Категория:", get_edit_category_keyboard()); return
                if msg == "➕ Добавить":
                    temp_data[uid]["step"] = "staff_edit_add"; send(vk, uid, "ФАМИЛИИ через запятую для ДОБАВЛЕНИЯ:", None); return
                if msg == "➖ Удалить":
                    temp_data[uid]["step"] = "staff_edit_rem"; send(vk, uid, "ФАМИЛИИ через запятую для УДАЛЕНИЯ:", None); return
                send(vk, uid, "Действие:", get_names_action_keyboard()); return
            if step == "staff_edit_add":
                cat = temp_data[uid]["cat"]; nr = get_order_names(oid)
                idx = {"plat":0,"bes":1,"svo":2,"ovz":3,"podvoz":4}[cat]
                lst = clean_names(nr[idx] or "")
                new = clean_names(msg)
                for n in new:
                    if n not in lst: lst.append(n)
                ns = ", ".join(lst); cnt = len(lst)
                update_order_names(oid, cat, ns, cnt)
                send(vk, uid, f"✅ +{len(new)}. Всего {cnt}:\n{ns}", get_main_keyboard(uid)); del temp_data[uid]; return
            if step == "staff_edit_rem":
                cat = temp_data[uid]["cat"]; nr = get_order_names(oid)
                idx = {"plat":0,"bes":1,"svo":2,"ovz":3,"podvoz":4}[cat]
                lst = clean_names(nr[idx] or "")
                rm = clean_names(msg); rem = []
                for n in rm:
                    if n in lst: lst.remove(n); rem.append(n)
                ns = ", ".join(lst); cnt = len(lst)
                update_order_names(oid, cat, ns, cnt)
                send(vk, uid, f"✅ -{len(rem)}. Осталось {cnt}:\n{ns if ns else '—'}", get_main_keyboard(uid)); del temp_data[uid]; return

        if msg.startswith("#"):
            if uid not in STAFF_IDS:
                send(vk, uid, "Только сотрудники.", get_main_keyboard(uid)); return
            oid = int(msg.replace("#", ""))
            temp_data[uid] = {"step": "staff_edit_category", "oid": oid}
            send(vk, uid, f"📝 Заказ #{oid}\n\nКатегория:", get_edit_category_keyboard()); return

        if msg == "🌅 Завтрак":
            temp_data[uid] = {"step": "class_name", "mt": "завтрак", "hist": []}
            send(vk, uid, "🏫 ЗАВТРАК.\n\nНапиши класс (например: 9А):", None); return
        if msg == "🌞 Обед":
            temp_data[uid] = {"step": "class_name", "mt": "обед", "hist": []}
            send(vk, uid, "🏫 ОБЕД.\n\nНапиши класс (например: 9А):", None); return

        if uid in temp_data:
            step = temp_data[uid].get("step")
            if msg == "🔙 Назад":
                h = temp_data[uid].get("hist", [])
                if not h:
                    del temp_data[uid]; send(vk, uid, "Меню:", get_main_keyboard(uid)); return
                prev = h.pop(); temp_data[uid]["step"] = prev; temp_data[uid]["hist"] = h
                if prev == "class_name": send(vk, uid, "🏫 Класс:", None)
                elif prev == "date": send(vk, uid, "📅 Дата:", get_date_keyboard())
                elif prev == "category": send(vk, uid, "👥 Категория:", get_category_keyboard())
                return
            if step == "class_name":
                temp_data[uid]["hist"].append("class_name"); temp_data[uid]["cn"] = msg.upper(); temp_data[uid]["step"] = "date"
                send(vk, uid, "📅 Дата:", get_date_keyboard()); return
            if step == "date":
                dt = parse_date(msg)
                if not dt: send(vk, uid, "Не понял дату:", get_date_keyboard()); return
                temp_data[uid]["hist"].append("date"); temp_data[uid]["dt"] = dt; temp_data[uid]["step"] = "category"
                for c in ["plat","bes","svo","ovz","podvoz"]: temp_data[uid][f"n_{c}"] = []
                send(vk, uid, "👥 Категория, потом ФАМИЛИИ через запятую.\n`-` или `0` не считаются.", get_category_keyboard()); return
            if step == "category":
                if msg == "✅ Готово":
                    tot = sum(len(temp_data[uid][f"n_{c}"]) for c in ["plat","bes","svo","ovz","podvoz"])
                    if tot == 0: send(vk, uid, "Пусто.", get_category_keyboard()); return
                    cn = temp_data[uid]["cn"]; dt = temp_data[uid]["dt"]; mt = temp_data[uid]["mt"]
                    v = {}
                    for c in ["plat","bes","svo","ovz","podvoz"]:
                        v[c] = ", ".join(temp_data[uid][f"n_{c}"])
                        v[f"c_{c}"] = len(temp_data[uid][f"n_{c}"])
                    create_order(user_id, cn, dt, mt, v["c_plat"], v["c_bes"], v["c_svo"], v["c_ovz"], v["c_podvoz"], v["plat"], v["bes"], v["svo"], v["ovz"], v["podvoz"])
                    rep = f"✅ ЗАКАЗ!\nКласс: {cn}\nДата: {dt}\nПриём: {mt}\n\n"
                    rep += f"Платники ({v['c_plat']}): {v['plat'] or '—'}\n"
                    rep += f"Бесплатники ({v['c_bes']}): {v['bes'] or '—'}\n"
                    rep += f"СВО ({v['c_svo']}): {v['svo'] or '—'}\n"
                    rep += f"ОВЗ ({v['c_ovz']}): {v['ovz'] or '—'}\n"
                    rep += f"Подвоз ({v['c_podvoz']}): {v['podvoz'] or '—'}"
                    send(vk, uid, rep, get_main_keyboard(uid)); del temp_data[uid]; return
                cmap = {"💳 Платники":"plat","🆓 Бесплатники":"bes","⭐ СВО":"svo","♿ ОВЗ":"ovz","🚌 Подвоз":"podvoz"}
                if msg in cmap:
                    temp_data[uid]["cur"] = cmap[msg]
                    send(vk, uid, f"ФАМИЛИИ для {msg}:\n`-` или `0` если никого", None); return
                if "cur" in temp_data[uid]:
                    c = temp_data[uid]["cur"]; new = clean_names(msg)
                    if new: temp_data[uid][f"n_{c}"].extend(new)
                    cnt = len(temp_data[uid][f"n_{c}"])
                    nm = {"plat":"Платники","bes":"Бесплатники","svo":"СВО","ovz":"ОВЗ","podvoz":"Подвоз"}
                    if new: send(vk, uid, f"✅ +{len(new)} в {nm[c]}. Всего: {cnt}", get_category_keyboard())
                    else: send(vk, uid, f"`-` не считается. В {nm[c]}: {cnt}", get_category_keyboard())
                    return
                send(vk, uid, "Категория:", get_category_keyboard()); return

        send(vk, uid, "📌 Выбери действие:", get_main_keyboard(uid))
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
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
            print(f"⚠️ {e}"); time.sleep(10)
            try: longpoll = VkBotLongPoll(vk_session, GROUP_ID); print("✅ Переподключено")
            except: time.sleep(30)
