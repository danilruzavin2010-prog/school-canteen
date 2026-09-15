import threading
import os
import datetime
import urllib.parse
from flask import Flask, render_template_string, request

# === ЗАПУСК БОТА В ФОНЕ ===
def run_bot():
    try:
        os.system("python bot.py")
    except Exception as e:
        print(f"❌ Бот упал: {e}")

bot_thread = threading.Thread(target=run_bot, daemon=True)
bot_thread.start()
print("🚀 Бот запущен в фоне")

app = Flask(__name__)

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

# === HTML ШАБЛОН ===
HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🍽 Панель столовой</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 10px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 16px; border-radius: 12px; }
        h1 { font-size: 20px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th { background: #4CAF50; color: white; padding: 8px 4px; }
        td { padding: 8px 4px; text-align: center; border-bottom: 1px solid #ddd; }
        .plat { color: green; }
        .bes { color: blue; }
        .svo { color: orange; }
        .ovz { color: purple; }
        .podvoz { color: #d35400; }
        .totals { margin-top: 16px; padding: 12px; background: #f0f0f0; border-radius: 8px; }
        .totals span { font-weight: bold; }
        .filters { margin: 12px 0; }
        .filter-btn { padding: 6px 12px; background: #e0e0e0; border-radius: 16px; text-decoration: none; color: black; margin-right: 8px; display: inline-block; }
        .filter-btn.active { background: #4CAF50; color: white; }
        .date-form { margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap; }
        .date-form input[type="date"] { padding: 8px; flex: 1; }
        .date-form button { padding: 8px 16px; background: #4CAF50; color: white; border: none; border-radius: 6px; }
        .names-btn { cursor: pointer; color: #1976D2; text-decoration: underline; font-size: 11px; }
        .names-block { display: none; text-align: left; font-size: 12px; padding: 8px; background: #fafafa; border-radius: 6px; margin-top: 4px; }
        .names-block.show { display: block; }
        .names-block b { display: inline-block; min-width: 120px; }
        @media (max-width: 700px) {
            table { font-size: 11px; }
            th, td { padding: 4px 2px; }
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
    <h1>🍽 Столовая — заказы на {{ date }}</h1>
    
    <div class="filters">
        <a href="?date={{ date }}&meal=" class="filter-btn {{ 'active' if meal_filter == '' else '' }}">Все</a>
        <a href="?date={{ date }}&meal=завтрак" class="filter-btn {{ 'active' if meal_filter == 'завтрак' else '' }}">Завтрак</a>
        <a href="?date={{ date }}&meal=обед" class="filter-btn {{ 'active' if meal_filter == 'обед' else '' }}">Обед</a>
    </div>

    <table>
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
        {% for row in orders %}
        <tr>
            <td><strong>{{ row[0] }}</strong></td>
            <td>{{ row[1] }}</td>
            <td class="plat">{{ row[2] }}</td>
            <td class="bes">{{ row[3] }}</td>
            <td class="svo">{{ row[4] }}</td>
            <td class="ovz">{{ row[5] }}</td>
            <td class="podvoz">{{ row[6] }}</td>
            <td><strong>{{ row[2] + row[3] + row[4] + row[5] + row[6] }}</strong></td>
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
    </table>

    <div class="totals">
        <p>👥 Всего порций: <span>{{ total_people }}</span></p>
        <p>
            Платники: <span class="plat">{{ total_plat }}</span> | 
            Бесплатники: <span class="bes">{{ total_bes }}</span> | 
            СВО: <span class="svo">{{ total_svo }}</span> | 
            ОВЗ: <span class="ovz">{{ total_ovz }}</span> | 
            Подвоз: <span class="podvoz">{{ total_podvoz }}</span>
        </p>
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
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)