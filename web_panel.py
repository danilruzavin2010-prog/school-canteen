from flask import Flask, render_template_string, request
import os
import datetime
import urllib.parse
import sys

app = Flask(__name__)

# === ОПРЕДЕЛЯЕМ ТИП БАЗЫ ДАННЫХ ===
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

# === ВРЕМЕННЫЙ МАРШРУТ ДЛЯ СОЗДАНИЯ ТАБЛИЦ ===
@app.route('/create_tables')
def create_tables_route():
    try:
        import psycopg2
        import urllib.parse
        import os
        
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            return "❌ DATABASE_URL не найден! Добавь переменную в RelaxDev."
        
        result = urllib.parse.urlparse(db_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        cur = conn.cursor()
        
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
        return "✅ Таблицы users и orders успешно созданы! <a href='/'>Вернуться на главную</a>"
    except Exception as e:
        return f"❌ Ошибка: {e}"

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
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 16px; border-radius: 12px; }
        h1 { font-size: 20px; }
        table { width: 100%; border-collapse: collapse; font-size: 14px; }
        th { background: #4CAF50; color: white; padding: 8px; }
        td { padding: 8px; text-align: center; border-bottom: 1px solid #ddd; }
        .plat { color: green; }
        .bes { color: blue; }
        .svo { color: orange; }
        .ovz { color: purple; }
        .totals { margin-top: 16px; padding: 12px; background: #f0f0f0; border-radius: 8px; }
        .totals span { font-weight: bold; }
        .filters { margin: 12px 0; }
        .filter-btn { padding: 6px 12px; background: #e0e0e0; border-radius: 16px; text-decoration: none; color: black; margin-right: 8px; }
        .filter-btn.active { background: #4CAF50; color: white; }
        .date-form { margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap; }
        .date-form input[type="date"] { padding: 8px; flex: 1; }
        .date-form button { padding: 8px 16px; background: #4CAF50; color: white; border: none; border-radius: 6px; }
        .status-new { color: orange; }
        .status-confirmed { color: green; }
        @media (max-width: 600px) {
            table { font-size: 12px; }
            th, td { padding: 4px; }
        }
    </style>
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
        <tr><th>Класс</th><th>Приём</th><th>Платники</th><th>Бесплатники</th><th>СВО</th><th>ОВЗ</th><th>Всего</th><th>Статус</th></tr>
        {% for row in orders %}
        <tr>
            <td><strong>{{ row[0] }}</strong></td>
            <td>{{ row[1] }}</td>
            <td class="plat">{{ row[2] }}</td>
            <td class="bes">{{ row[3] }}</td>
            <td class="svo">{{ row[4] }}</td>
            <td class="ovz">{{ row[5] }}</td>
            <td><strong>{{ row[2] + row[3] + row[4] + row[5] }}</strong></td>
            <td class="status-{{ row[6] }}">{{ row[6] }}</td>
        </tr>
        {% endfor %}
    </table>

    <div class="totals">
        <p>👥 Всего: <span>{{ total_people }}</span> чел.</p>
        <p>💳 Платники: <span class="plat">{{ total_plat }}</span> | 
           🆓 Бесплатники: <span class="bes">{{ total_bes }}</span> | 
           ⭐ СВО: <span class="svo">{{ total_svo }}</span> | 
           ♿ ОВЗ: <span class="ovz">{{ total_ovz }}</span></p>
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
    
    # Универсальный запрос (работает и в SQLite, и в PostgreSQL)
    if db_type == "postgresql":
        query = '''
            SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, status
            FROM orders
            WHERE order_date = %s
        '''
        params = [date_str]
        if meal_filter and meal_filter != '':
            query += " AND meal_type = %s"
            params.append(meal_filter)
        cur.execute(query, params)
    else:
        # SQLite
        query = '''
            SELECT class_name, meal_type, count_plat, count_bes, count_svo, count_ovz, status
            FROM orders
            WHERE order_date = ?
        '''
        params = [date_str]
        if meal_filter and meal_filter != '':
            query += " AND meal_type = ?"
            params.append(meal_filter)
        cur.execute(query, params)
    
    rows = cur.fetchall()
    conn.close()
    
    total_plat = sum(r[2] for r in rows)
    total_bes = sum(r[3] for r in rows)
    total_svo = sum(r[4] for r in rows)
    total_ovz = sum(r[5] for r in rows)
    total_people = total_plat + total_bes + total_svo + total_ovz
    
    return render_template_string(
        HTML,
        orders=rows,
        total_plat=total_plat,
        total_bes=total_bes,
        total_svo=total_svo,
        total_ovz=total_ovz,
        total_people=total_people,
        date=date_str,
        meal_filter=meal_filter
    )

@app.route('/create_tables')
def create_tables_route():
    try:
        import psycopg2
        import urllib.parse
        import os
        
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            return "❌ DATABASE_URL не найден! Добавь переменную в RelaxDev."
        
        result = urllib.parse.urlparse(db_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        cur = conn.cursor()
        
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
        return "✅ Таблицы users и orders успешно созданы! <a href='/'>Вернуться на главную</a>"
    except Exception as e:
        return f"❌ Ошибка: {e}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)