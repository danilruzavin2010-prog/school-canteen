import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
import datetime, os, re, urllib.parse, time

VK_TOKEN = os.environ.get("VK_TOKEN", "vk1.a.z1AGhRJTlOfwdx4ldltGvv10FPkpmfgUHproUb6uREpo0Ao2TH8PCldeXPDFY7O7qVVkd2NdhCtOd1EJ321WsxAXw_BfL8U13lkhK3JC77rUvMuHAhqiaGB4VPMFnMvb9qhEjWXyXwzf4RtQIshOIxxFbKUJUjaEQgX9aouqhvaHYM0zvVLzTDE_9qEmIlFVIE7x7oGrqNuTYDWXGj2T4A")
GROUP_ID = 241386335
STAFF_IDS = [523723395, 768610229, 165518301, 424711270, 157860178]
CREATOR_IDS = [523723395, 768610229]

def db():
    url = os.environ.get("DATABASE_URL")
    if not url:
        import sqlite3
        return sqlite3.connect(os.environ.get("DB_PATH", "/data/canteen.db")), "sqlite"
    import psycopg2
    r = urllib.parse.urlparse(url)
    return psycopg2.connect(database=r.path[1:], user=r.username, password=r.password, host=r.hostname, port=r.port), "pg"

def init_db():
    c, t = db(); cur = c.cursor()
    if t == "sqlite":
        cur.executescript('''
            CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, vk_id INTEGER UNIQUE, full_name TEXT, department TEXT);
            CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, class_name TEXT, order_date TEXT, meal_type TEXT, count_plat INTEGER DEFAULT 0, count_bes INTEGER DEFAULT 0, count_svo INTEGER DEFAULT 0, count_ovz INTEGER DEFAULT 0, count_podvoz INTEGER DEFAULT 0, names_plat TEXT DEFAULT '', names_bes TEXT DEFAULT '', names_svo TEXT DEFAULT '', names_ovz TEXT DEFAULT '', names_podvoz TEXT DEFAULT '', status TEXT DEFAULT 'новый');
        ''')
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, vk_id BIGINT UNIQUE, full_name TEXT, department TEXT)")
        cur.execute("CREATE TABLE IF NOT EXISTS orders (id SERIAL PRIMARY KEY, user_id INTEGER, class_name TEXT, order_date DATE, meal_type TEXT, count_plat INTEGER DEFAULT 0, count_bes INTEGER DEFAULT 0, count_svo INTEGER DEFAULT 0, count_ovz INTEGER DEFAULT 0, count_podvoz INTEGER DEFAULT 0, names_plat TEXT DEFAULT '', names_bes TEXT DEFAULT '', names_svo TEXT DEFAULT '', names_ovz TEXT DEFAULT '', names_podvoz TEXT DEFAULT '', status TEXT DEFAULT 'новый')")
        for col, col_type in [("count_podvoz", "INTEGER DEFAULT 0"), ("names_plat", "TEXT DEFAULT ''"), ("names_bes", "TEXT DEFAULT ''"), ("names_svo", "TEXT DEFAULT ''"), ("names_ovz", "TEXT DEFAULT ''"), ("names_podvoz", "TEXT DEFAULT ''")]:
            try: cur.execute(f"ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col} {col_type}")
            except: pass
    c.commit(); c.close()
    print("✅ База данных инициализирована")

def add_user(vk_id, name, dept="не указан"):
    c, t = db(); cur = c.cursor()
    if t == "sqlite": cur.execute("INSERT OR IGNORE INTO users (vk_id, full_name, department) VALUES (?, ?, ?)", (vk_id, name, dept))
    else: cur.execute("INSERT INTO users (vk_id, full_name, department) VALUES (%s, %s, %s) ON CONFLICT (vk_id) DO NOTHING", (vk_id, name, dept))
    c.commit(); c.close()

def get_user(vk_id):
    c, t = db(); cur = c.cursor()
    q = "?" if t == "sqlite" else "%s"
    cur.execute(f"SELECT id, full_name FROM users WHERE vk_id = {q}", (vk_id,))
    r = cur.fetchone(); c.close(); return r

def save_order(u, cn, dt, mt, cp, cb, cs, co, cpz, np, nb, ns, no, npz):
    c, t = db(); cur = c.cursor()
    if t == "sqlite":
        cur.execute("INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz, names_plat, names_bes, names_svo, names_ovz, names_podvoz, status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,'новый')", (u, cn, dt, mt, cp, cb, cs, co, cpz, np, nb, ns, no, npz))
    else:
        cur.execute("INSERT INTO orders (user_id, class_name, order_date, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz, names_plat, names_bes, names_svo, names_ovz, names_podvoz, status) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'новый')", (u, cn, dt, mt, cp, cb, cs, co, cpz, np, nb, ns, no, npz))
    c.commit(); c.close()

def del_order(oid):
    c, t = db(); cur = c.cursor()
    try:
        q = "?" if t == "sqlite" else "%s"
        cur.execute(f"DELETE FROM orders WHERE id = {q}", (oid,))
        c.commit(); return True
    except: return False
    finally: c.close()

def my_orders(uid):
    c, t = db(); cur = c.cursor()
    today = datetime.date.today().isoformat()
    q = "?" if t == "sqlite" else "%s"
    cur.execute(f"SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE user_id = {q} AND order_date = {q}", (uid, today))
    r = cur.fetchall(); c.close(); return r

def all_orders():
    c, t = db(); cur = c.cursor()
    today = datetime.date.today().isoformat()
    q = "?" if t == "sqlite" else "%s"
    cur.execute(f"SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = {q} ORDER BY class_name", (today,))
    r = cur.fetchall(); c.close(); return r

def get_names(oid):
    c, t = db(); cur = c.cursor()
    q = "?" if t == "sqlite" else "%s"
    cur.execute(f"SELECT names_plat, names_bes, names_svo, names_ovz, names_podvoz FROM orders WHERE id = {q}", (oid,))
    r = cur.fetchone(); c.close(); return r

def set_names(oid, cat, ns, cnt):
    c, t = db(); cur = c.cursor()
    try:
        q = "?" if t == "sqlite" else "%s"
        cur.execute(f"UPDATE orders SET names_{cat} = {q}, count_{cat} = {q} WHERE id = {q}", (ns, cnt, oid))
        c.commit(); return True
    except: return False
    finally: c.close()

def parse_date(t):
    t = t.lower().strip()
    if t == "сегодня": return datetime.date.today().isoformat()
    if t == "завтра": return (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    if t == "послезавтра": return (datetime.date.today() + datetime.timedelta(days=2)).isoformat()
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})$', t)
    if m:
        try: return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except: return None
    return None

def clean(text):
    if not text: return []
    return [n.strip() for n in text.split(',') if n.strip() and n.strip() not in ['-', '—', '–', '0', 'нет', 'Нет']]

def kb_main(uid):
    k = VkKeyboard(one_time=False)
    k.add_button("🌅 Завтрак", color=VkKeyboardColor.SECONDARY)
    k.add_button("🌞 Обед", color=VkKeyboardColor.SECONDARY)
    k.add_line()
    k.add_button("✏️ Мои заказы", color=VkKeyboardColor.SECONDARY)
    if uid in STAFF_IDS or uid in CREATOR_IDS:
        k.add_button("📋 Отчёт", color=VkKeyboardColor.POSITIVE)
        k.add_line()
        k.add_button("🛠 Редактировать", color=VkKeyboardColor.PRIMARY)
    return k.get_keyboard()

def kb_date():
    k = VkKeyboard(one_time=True)
    k.add_button("Сегодня", color=VkKeyboardColor.PRIMARY)
    k.add_button("Завтра", color=VkKeyboardColor.PRIMARY)
    k.add_line()
    k.add_button("Послезавтра", color=VkKeyboardColor.SECONDARY)
    k.add_button("🔙 Назад", color=VkKeyboardColor.NEGATIVE)
    return k.get_keyboard()

def kb_cat():
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

def kb_edit_cat():
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

def kb_names(uid):
    k = VkKeyboard(one_time=True)
    k.add_button("➕ Добавить", color=VkKeyboardColor.POSITIVE)
    k.add_button("➖ Удалить", color=VkKeyboardColor.NEGATIVE)
    k.add_line()
    if uid in CREATOR_IDS:
        k.add_button("🗑 Удалить заказ", color=VkKeyboardColor.NEGATIVE)
    k.add_button("🔙 Другая категория", color=VkKeyboardColor.SECONDARY)
    return k.get_keyboard()

td = {}

def send(vk, uid, text, kb=None):
    p = {'user_id': uid, 'message': text, 'random_id': 0}
    if kb: p['keyboard'] = kb
    vk.messages.send(**p)

def handle(event, vk):
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
            send(vk, uid, "👋 Привет! Заказывай питание.", kb_main(uid)); return
        user_id = ud[0]

        if low.startswith("отчёт") or low.startswith("!стафф") or msg == "📋 Отчёт":
            if uid not in STAFF_IDS and uid not in CREATOR_IDS:
                send(vk, uid, "Доступ запрещён.", kb_main(uid)); return
            c, t = db(); cur = c.cursor()
            q = "DATE('now')" if t == "sqlite" else "CURRENT_DATE"
            cur.execute(f"SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz FROM orders WHERE order_date = {q}")
            rows = cur.fetchall(); c.close()
            if not rows:
                send(vk, uid, "Заказов нет.", kb_main(uid)); return
            bf = [r for r in rows if r[1] == "завтрак"]
            ln = [r for r in rows if r[1] != "завтрак"]
            rep = ""; bt = 0; lt = 0
            for title, group in [("🌅 ЗАВТРАКИ", bf), ("🌞 ОБЕДЫ", ln)]:
                if not group: rep += f"{title}: нет\n\n"; continue
                rep += f"{title}:\n"; tot = 0
                for row in group:
                    cn, mt, cp, cb, cs, co, cpz = row
                    s = cp + cb + cs + co + cpz; tot += s
                    parts = []
                    if cp: parts.append(f"Платники:{cp}")
                    if cb: parts.append(f"Бесплатники:{cb}")
                    if cs: parts.append(f"СВО:{cs}")
                    if co: parts.append(f"ОВЗ:{co}")
                    if cpz: parts.append(f"Подвоз:{cpz}")
                    rep += f"🏫 {cn}: {' + '.join(parts)} = {s}\n"
                rep += f"ИТОГО: {tot} чел.\n\n"
                if title.startswith("🌅"): bt = tot
                else: lt = tot
            rep += f"👥 ВСЕГО: {bt + lt} чел."
            send(vk, uid, rep, kb_main(uid)); return

        if msg == "✏️ Мои заказы" or low.startswith("мои заказы"):
            rows = my_orders(user_id)
            if not rows:
                send(vk, uid, "У тебя нет заказов.", kb_main(uid)); return
            rep = "📋 ТВОИ ЗАКАЗЫ:\n\n"
            for o in rows:
                oid, cn, mt, cp, cb, cs, co, cpz = o
                rep += f"#{oid} 🏫 {cn} ({mt}): {cp+cb+cs+co+cpz} чел.\n"
            send(vk, uid, rep, kb_main(uid)); return

        if msg == "🛠 Редактировать":
            if uid not in STAFF_IDS and uid not in CREATOR_IDS:
                send(vk, uid, "Доступ запрещён.", kb_main(uid)); return
            rows = all_orders()
            if not rows:
                send(vk, uid, "Заказов нет.", kb_main(uid)); return
            rep = "📋 ВСЕ ЗАКАЗЫ:\n\n"
            for r in rows:
                oid, cn, mt, cp, cb, cs, co, cpz = r
                rep += f"#{oid} 🏫 {cn} ({mt}): {cp+cb+cs+co+cpz} чел.\n"
            rep += "\nНапиши #ID заказа."
            send(vk, uid, rep, kb_main(uid)); return

        if uid in td and td[uid].get("step", "").startswith("se"):
            if uid not in STAFF_IDS and uid not in CREATOR_IDS:
                send(vk, uid, "Доступ запрещён.", kb_main(uid)); del td[uid]; return
            step = td[uid]["step"]; oid = td[uid]["oid"]
            if step == "se_cat":
                if msg == "🔙 Назад":
                    del td[uid]; send(vk, uid, "Меню:", kb_main(uid)); return
                cmap = {"Платники":"plat","Бесплатники":"bes","СВО":"svo","ОВЗ":"ovz","Подвоз":"podvoz"}
                if msg in cmap:
                    td[uid]["cat"] = cmap[msg]; td[uid]["step"] = "se_act"
                    nr = get_names(oid)
                    idx = {"plat":0,"bes":1,"svo":2,"ovz":3,"podvoz":4}[cmap[msg]]
                    cur = nr[idx] or "—"
                    send(vk, uid, f"Категория: {msg}\n\nФамилии:\n{cur}\n\nЧто?", kb_names(uid)); return
                send(vk, uid, "Категория:", kb_edit_cat()); return
            if step == "se_act":
                if msg == "🔙 Другая категория":
                    td[uid]["step"] = "se_cat"; send(vk, uid, "Категория:", kb_edit_cat()); return
                if msg == "➕ Добавить":
                    td[uid]["step"] = "se_add"; send(vk, uid, "ФАМИЛИИ через запятую для ДОБАВЛЕНИЯ:", None); return
                if msg == "➖ Удалить":
                    td[uid]["step"] = "se_rem"; send(vk, uid, "ФАМИЛИИ через запятую для УДАЛЕНИЯ:", None); return
                if msg == "🗑 Удалить заказ":
                    if uid not in CREATOR_IDS:
                        send(vk, uid, "❌ Только создатель.", kb_main(uid)); return
                    if del_order(oid):
                        del td[uid]; send(vk, uid, "✅ Заказ удалён.", kb_main(uid))
                    else: send(vk, uid, "❌ Ошибка.", kb_main(uid))
                    return
                send(vk, uid, "Действие:", kb_names(uid)); return
            if step == "se_add":
                cat = td[uid]["cat"]; nr = get_names(oid)
                idx = {"plat":0,"bes":1,"svo":2,"ovz":3,"podvoz":4}[cat]
                lst = clean(nr[idx] or "")
                new = clean(msg)
                for n in new:
                    if n not in lst: lst.append(n)
                ns = ", ".join(lst); cnt = len(lst)
                set_names(oid, cat, ns, cnt)
                send(vk, uid, f"✅ +{len(new)}. Всего {cnt}:\n{ns}", kb_main(uid)); del td[uid]; return
            if step == "se_rem":
                cat = td[uid]["cat"]; nr = get_names(oid)
                idx = {"plat":0,"bes":1,"svo":2,"ovz":3,"podvoz":4}[cat]
                lst = clean(nr[idx] or "")
                rm = clean(msg); rem = []
                for n in rm:
                    if n in lst: lst.remove(n); rem.append(n)
                ns = ", ".join(lst); cnt = len(lst)
                set_names(oid, cat, ns, cnt)
                send(vk, uid, f"✅ -{len(rem)}. Осталось {cnt}:\n{ns if ns else '—'}", kb_main(uid)); del td[uid]; return

        if msg.startswith("#"):
            if uid not in STAFF_IDS and uid not in CREATOR_IDS:
                send(vk, uid, "Только сотрудники.", kb_main(uid)); return
            oid = int(msg.replace("#", ""))
            td[uid] = {"step": "se_cat", "oid": oid}
            send(vk, uid, f"📝 Заказ #{oid}\n\nКатегория:", kb_edit_cat()); return

        if msg == "🌅 Завтрак":
            td[uid] = {"step": "cn", "mt": "завтрак", "hist": []}
            send(vk, uid, "🏫 ЗАВТРАК.\n\nКласс (например: 9А):", None); return
        if msg == "🌞 Обед":
            td[uid] = {"step": "cn", "mt": "обед", "hist": []}
            send(vk, uid, "🏫 ОБЕД.\n\nКласс (например: 9А):", None); return

        if uid in td:
            step = td[uid].get("step")
            if msg == "🔙 Назад":
                h = td[uid].get("hist", [])
                if not h:
                    del td[uid]; send(vk, uid, "Меню:", kb_main(uid)); return
                prev = h.pop(); td[uid]["step"] = prev; td[uid]["hist"] = h
                if prev == "cn": send(vk, uid, "🏫 Класс:", None)
                elif prev == "dt": send(vk, uid, "📅 Дата:", kb_date())
                elif prev == "cat": send(vk, uid, "👥 Категория:", kb_cat())
                return
            if step == "cn":
                td[uid]["hist"].append("cn"); td[uid]["cn"] = msg.upper(); td[uid]["step"] = "dt"
                send(vk, uid, "📅 Дата:", kb_date()); return
            if step == "dt":
                dt = parse_date(msg)
                if not dt: send(vk, uid, "Не понял:", kb_date()); return
                td[uid]["hist"].append("dt"); td[uid]["dt"] = dt; td[uid]["step"] = "cat"
                for c in ["plat","bes","svo","ovz","podvoz"]: td[uid][f"n_{c}"] = []
                send(vk, uid, "👥 Категория, потом ФАМИЛИИ через запятую.\n`-` или `0` не считаются.", kb_cat()); return
            if step == "cat":
                if msg == "✅ Готово":
                    tot = sum(len(td[uid][f"n_{c}"]) for c in ["plat","bes","svo","ovz","podvoz"])
                    if tot == 0: send(vk, uid, "Пусто.", kb_cat()); return
                    cn = td[uid]["cn"]; dt = td[uid]["dt"]; mt = td[uid]["mt"]
                    v = {}
                    for c in ["plat","bes","svo","ovz","podvoz"]:
                        v[c] = ", ".join(td[uid][f"n_{c}"])
                        v[f"c_{c}"] = len(td[uid][f"n_{c}"])
                    save_order(user_id, cn, dt, mt, v["c_plat"], v["c_bes"], v["c_svo"], v["c_ovz"], v["c_podvoz"], v["plat"], v["bes"], v["svo"], v["ovz"], v["podvoz"])
                    rep = f"✅ ЗАКАЗ!\nКласс: {cn}\nДата: {dt}\nПриём: {mt}\n\n"
                    rep += f"Платники ({v['c_plat']}): {v['plat'] or '—'}\n"
                    rep += f"Бесплатники ({v['c_bes']}): {v['bes'] or '—'}\n"
                    rep += f"СВО ({v['c_svo']}): {v['svo'] or '—'}\n"
                    rep += f"ОВЗ ({v['c_ovz']}): {v['ovz'] or '—'}\n"
                    rep += f"Подвоз ({v['c_podvoz']}): {v['podvoz'] or '—'}"
                    send(vk, uid, rep, kb_main(uid)); del td[uid]; return
                cmap = {"💳 Платники":"plat","🆓 Бесплатники":"bes","⭐ СВО":"svo","♿ ОВЗ":"ovz","🚌 Подвоз":"podvoz"}
                if msg in cmap:
                    td[uid]["cur"] = cmap[msg]
                    send(vk, uid, f"ФАМИЛИИ для {msg}:\n`-` или `0` если никого", None); return
                if "cur" in td[uid]:
                    c = td[uid]["cur"]; new = clean(msg)
                    if new: td[uid][f"n_{c}"].extend(new)
                    cnt = len(td[uid][f"n_{c}"])
                    nm = {"plat":"Платники","bes":"Бесплатники","svo":"СВО","ovz":"ОВЗ","podvoz":"Подвоз"}
                    if new: send(vk, uid, f"✅ +{len(new)} в {nm[c]}. Всего: {cnt}", kb_cat())
                    else: send(vk, uid, f"`-` не считается. В {nm[c]}: {cnt}", kb_cat())
                    return
                send(vk, uid, "Категория:", kb_cat()); return

        send(vk, uid, "📌 Выбери действие:", kb_main(uid))
    except Exception as e:
        print(f"❌ {e}")
        try: send(vk, uid, "Ошибка. Попробуй ещё.", kb_main(uid))
        except: pass

if __name__ == "__main__":
    init_db()
    vk_s = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_s.get_api()
    lp = VkBotLongPoll(vk_s, GROUP_ID)
    print("🤖 SWILL BOT ACTIVE")
    print("Жду сообщений...")
    while True:
        try:
            for ev in lp.listen():
                if ev.type == VkBotEventType.MESSAGE_NEW:
                    handle(ev, vk)
        except Exception as e:
            print(f"⚠️ {e}"); time.sleep(10)
            try: lp = VkBotLongPoll(vk_s, GROUP_ID); print("✅ Переподключено")
            except: time.sleep(30)
