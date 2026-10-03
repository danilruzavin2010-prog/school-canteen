import threading
import subprocess
import time
import os
import datetime
import urllib.parse
from flask import Flask, render_template_string, request

# === ЗАПУСК БОТА В ФОНЕ ===
def run_bot():
    while True:
        try:
            print("🚀 Запуск бота...")
            subprocess.run(["python", "bot.py"])
        except Exception as e:
            print(f"❌ Бот упал: {e}")
        print("⚠️ Бот завершился. Перезапуск через 5 секунд...")
        time.sleep(5)

bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
print("🤖 Поток бота запущен")

app = Flask(__name__)

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

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🍽 Панель столовой</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; background: #f5f5f5; padding: 12px; color: #222; }
        .container { max-width: 1100px; margin: 0 auto; background: white; border-radius: 16px; padding: 16px 14px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
        h1 { font-size: 22px; margin-bottom: 4px; color: #2d3e50; }
        .subtitle { color: #888; font-size: 14px; margin-bottom: 16px; border-bottom: 1px solid #eee; padding-bottom: 10px; }
        .filters { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
        .filter-btn { display: inline-block; padding: 8px 14px; border-radius: 20px; background: #f0f0f0; color: #333; text-decoration: none; font-size: 14px; border: 1px solid #ddd; transition: all 0.2s; }
        .filter-btn.active { background: #4CAF50; color: white; border-color: #4CAF50; }
        .table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; border-radius: 12px; border: 1px solid #e8e8e8; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; min-width: 600px; }
        th { background: #4CAF50; color: white; padding: 10px 8px; font-weight: 600; white-space: nowrap; text-align: center; font-size: 13px; }
        td { padding: 10px 8px; text-align: center; border-bottom: 1px solid #f0f0f0; white-space: nowrap; }
        tr:last-child td { border-bottom: none; }
        tr:nth-child(even) { background: #fafafa; }
        .class-name { font-weight: 700; color: #1a3b5d; }
        .meal-type { background: #eef6ff; border-radius: 12px; padding: 2px 10px; display: inline-block; font-size: 12px; font-weight: 600; color: #1a5d8f; }
        .num { font-weight: 600; }
        .plat { color: #2e7d32; }
        .bes { color: #1565c0; }
        .svo { color: #e65100; }
        .ovz { color: #6a1b9a; }
        .podvoz { color: #d35400; }
        .total-cell { font-weight: 700; background: #fff8e1; border-radius: 4px; padding: 2px 8px; }
        .names-btn { cursor: pointer; color: #1976D2; text-decoration: underline; font-size: 12px; }
        .names-block { display: none; text-align: left; font-size: 12px; padding: 8px; background: #fafafa; border-radius: 6px; margin-top: 4px; }
        .names-block.show { display: block; }
        .names-block b { display: inline-block; min-width: 120px; }
        .totals { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 18px; padding: 14px 12px; background: #f8faff; border-radius: 12px; border: 1px solid #e8ecf4; }
        .totals .label { font-size: 13px; color: #555; }
        .totals .value { font-size: 18px; font-weight: 700; text-align: right; }
        .totals .value.plat { color: #2e7d32; }
        .totals .value.bes { color: #1565c0; }
        .totals .value.svo { color: #e65100; }
        .totals .value.ovz { color: #6a1b9a; }
        .totals .value.podvoz { color: #d35400; }
        .totals .value.people { color: #1a237e; font-size: 22px; }
        .total-people-block { grid-column: 1 / -1; display: flex; justify-content: space-between; align-items: center; border-top: 2px solid #e0e7f0; padding-top: 12px; margin-top: 4px; }
        .total-people-block .label { font-size: 16px; font-weight: 600; }
        .total-people-block .value { font-size: 26px; }
        .date-form { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 16px; padding-top: 14px; border-top: 1px solid #eee; }
        .date-form input[type="date"] { padding: 10px 12px; border: 1px solid #ccc; border-radius: 10px; font-size: 16px; flex: 1 1 180px; }
        .date-form button { padding: 10px 20px; background: #4CAF50; color: white; border: none; border-radius: 10px; font-size: 16px; font-weight: 600; cursor: pointer; }
        @media (max-width: 600px) {
            body { padding: 6px; }
            .container { padding: 10px 8px; border-radius: 12px; }
            h1 { font-size: 18px; }
            .filter-btn { font-size: 12px; padding: 6px 12px; }
            table { font-size: 12px; min-width: 500px; }
            th { font-size: 11px; padding: 6px 4px; }
            td { padding: 8px 4px; }
            .totals { grid-template-columns: 1fr 1fr; padding: 10px 8px; }
            .totals .value { font-size: 16px; }
            .total-people-block .value { font-size: 22px; }
        }
    </style>
    <script>
        function toggleNames(id) {
            var el = document.getElementById('names-' + id);
            if (el) el.classList.toggle('show');
        }
    </script>
</head>
<body>
<div class="container">
    <h1>🍽 Панель столовой</h1>
    <div class="subtitle">Заказы на {{ date }}</div>

    <div class="filters">
        <a href="?date={{ date }}&meal=" class="filter-btn {{ 'active' if meal_filter == '' else '' }}">Все</a>
        <a href="?date={{ date }}&meal=завтрак" class="filter-btn {{ 'active' if meal_filter == 'завтрак' else '' }}">🌅 Завтрак</a>
        <a href="?date={{ date }}&meal=обед" class="filter-btn {{ 'active' if meal_filter == 'обед' else '' }}">🌞 Обед</a>
    </div>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Класс</th>
                    <th>Приём</th>
                    <th>Платники</th>
                    <th>Бесплатники</th>
                    <th>СВО</th>
                    <th>ОВЗ</th>
                    <th>Подвоз</th>
                    <th>Всего</th>
                    <th>Фамилии</th>
                </tr>
            </thead>
            <tbody>
            {% for row in orders %}
                <tr>
                    <td class="class-name">{{ row[0] }}</td>
                    <td><span class="meal-type">{{ row[1] }}</span></td>
                    <td class="num plat">{{ row[2] }}</td>
                    <td class="num bes">{{ row[3] }}</td>
                    <td class="num svo">{{ row[4] }}</td>
                    <td class="num ovz">{{ row[5] }}</td>
                    <td class="num podvoz">{{ row[6] }}</td>
                    <td><span class="total-cell">{{ row[2] + row[3] + row[4] + row[5] + row[6] }}</span></td>
                    <td>
                        <span class="names-btn" onclick="toggleNames({{ row[8] }})">показать</span>
                        <div class="names-block" id="names-{{ row[8] }}">
                            {% if row[7] %}<div><b>Платники:</b> {{ row[7] }}</div>{% endif %}
                            {% if row[9] %}<div><b>Бесплатники:</b> {{ row[9] }}</div>{% endif %}
                            {% if row[10] %}<div><b>СВО:</b> {{ row[10] }}</div>{% endif %}
                            {% if row[11] %}<div><b>ОВЗ:</b> {{ row[11] }}</div>{% endif %}
                            {% if row[12] %}<div><b>Подвоз:</b> {{ row[12] }}</div>{% endif %}
                        </div>
                    </td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="totals">
        <div><span class="label">Платники</span></div>
        <div class="value plat">{{ total_plat }}</div>

        <div><span class="label">Бесплатники</span></div>
        <div class="value bes">{{ total_bes }}</div>

        <div><span class="label">СВО</span></div>
        <div class="value svo">{{ total_svo }}</div>

        <div><span class="label">ОВЗ</span></div>
        <div class="value ovz">{{ total_ovz }}</div>

        <div><span class="label">Подвоз</span></div>
        <div class="value podvoz">{{ total_podvoz }}</div>

        <div class="total-people-block">
            <span class="label">👥 Всего человек</span>
            <span class="value people">{{ total_people }}</span>
        </div>
    </div>

    <form method="GET" class="date-form">
        <input type="date" name="date" value="{{ date }}">
        <button>Показать</button>
    </form>
</div>
</body>
</html>
"""

@app.route('/')
def panel():
    date_str = request.args.get('date', datetime.date.today().isoformat())
    meal_filter = request.args.get('meal', '')
    
    conn, db_type = get_db_connection()
    cur = conn.cursor()
    
    base_select = '''
        SELECT id, class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, count_podvoz,
               names_plat, names_bes, names_svo, names_ovz, names_podvoz, status
        FROM orders
        WHERE order_date = {}
    '''
    
    if db_type == "postgresql":
        query = base_select.format("%s")
        params = [date_str]
        if meal_filter:
            query += " AND meal_type = %s"
            params.append(meal_filter)
    else:
        query = base_select.format("?")
        params = [date_str]
        if meal_filter:
            query += " AND meal_type = ?"
            params.append(meal_filter)
    
    cur.execute(query, params)
    raw = cur.fetchall()
    conn.close()
    
    orders = []
    for r in raw:
        orders.append((
            r[1], r[2], r[3], r[4], r[5], r[6], r[7],
            r[8], r[0], r[9], r[10], r[11], r[12],
        ))
    
    total_plat = sum(o[2] for o in orders)
    total_bes = sum(o[3] for o in orders)
    total_svo = sum(o[4] for o in orders)
    total_ovz = sum(o[5] for o in orders)
    total_podvoz = sum(o[6] for o in orders)
    total_people = total_plat + total_bes + total_svo + total_ovz + total_podvoz
    
    return render_template_string(
        HTML,
        orders=orders,
        total_plat=total_plat,
        total_bes=total_bes,
        total_svo=total_svo,
        total_ovz=total_ovz,
        total_podvoz=total_podvoz,
        total_people=total_people,
        date=date_str,
        meal_filter=meal_filter
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    app.run(host='0.0.0.0', port=port, debug=False)