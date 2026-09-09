from flask import Flask, render_template_string, request
import sqlite3
import datetime

app = Flask(__name__)
DB = "canteen.db"

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.5, user-scalable=yes">
    <title>🍽 Панель столовой</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: #f5f5f5;
            padding: 12px;
            color: #222;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            padding: 16px 14px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        }
        h1 {
            font-size: 22px;
            margin-bottom: 4px;
            color: #2d3e50;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        h1 span {
            font-size: 26px;
        }
        .subtitle {
            color: #888;
            font-size: 14px;
            margin-bottom: 16px;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        .filters {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 16px;
        }
        .filter-btn {
            display: inline-block;
            padding: 8px 14px;
            border-radius: 20px;
            background: #f0f0f0;
            color: #333;
            text-decoration: none;
            font-size: 14px;
            border: 1px solid #ddd;
            transition: all 0.2s;
            flex: 0 1 auto;
            text-align: center;
        }
        .filter-btn.active {
            background: #4CAF50;
            color: white;
            border-color: #4CAF50;
        }
        .filter-btn:active {
            transform: scale(0.96);
        }

        /* Таблица — адаптивная */
        .table-wrap {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            margin: 0 -4px;
            border-radius: 12px;
            border: 1px solid #e8e8e8;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
            min-width: 480px;
        }
        th {
            background: #4CAF50;
            color: white;
            padding: 10px 8px;
            font-weight: 600;
            white-space: nowrap;
            text-align: center;
            font-size: 13px;
        }
        td {
            padding: 10px 8px;
            text-align: center;
            border-bottom: 1px solid #f0f0f0;
            white-space: nowrap;
        }
        tr:last-child td {
            border-bottom: none;
        }
        tr:nth-child(even) {
            background: #fafafa;
        }
        .class-name {
            font-weight: 700;
            color: #1a3b5d;
        }
        .meal-type {
            background: #eef6ff;
            border-radius: 12px;
            padding: 2px 10px;
            display: inline-block;
            font-size: 12px;
            font-weight: 600;
            color: #1a5d8f;
        }
        .num {
            font-weight: 600;
        }
        .plat { color: #2e7d32; }
        .bes { color: #1565c0; }
        .svo { color: #e65100; }
        .ovz { color: #6a1b9a; }
        .total-cell {
            font-weight: 700;
            background: #fff8e1;
            border-radius: 4px;
            padding: 2px 8px;
        }
        .status-new {
            color: #e67e22;
            font-weight: 600;
            background: #fef5e7;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            display: inline-block;
        }
        .status-confirmed {
            color: #27ae60;
            font-weight: 600;
            background: #eafaf1;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            display: inline-block;
        }

        /* Итоги */
        .totals {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 18px;
            padding: 14px 12px;
            background: #f8faff;
            border-radius: 12px;
            border: 1px solid #e8ecf4;
        }
        .totals .label {
            font-size: 13px;
            color: #555;
        }
        .totals .value {
            font-size: 18px;
            font-weight: 700;
            text-align: right;
        }
        .totals .value.plat { color: #2e7d32; }
        .totals .value.bes { color: #1565c0; }
        .totals .value.svo { color: #e65100; }
        .totals .value.ovz { color: #6a1b9a; }
        .totals .value.people {
            color: #1a237e;
            font-size: 22px;
        }
        .total-people-block {
            grid-column: 1 / -1;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 2px solid #e0e7f0;
            padding-top: 12px;
            margin-top: 4px;
        }
        .total-people-block .label {
            font-size: 16px;
            font-weight: 600;
        }
        .total-people-block .value {
            font-size: 26px;
        }

        /* Форма даты */
        .date-form {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 10px;
            margin-top: 16px;
            padding-top: 14px;
            border-top: 1px solid #eee;
        }
        .date-form label {
            font-weight: 500;
            font-size: 14px;
            color: #444;
        }
        .date-form input[type="date"] {
            padding: 10px 12px;
            border: 1px solid #ccc;
            border-radius: 10px;
            font-size: 16px;
            flex: 1 1 180px;
            background: white;
            -webkit-appearance: none;
            appearance: none;
        }
        .date-form button {
            padding: 10px 20px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            flex: 0 1 auto;
        }
        .date-form button:active {
            background: #388e3c;
            transform: scale(0.96);
        }

        /* Мелкие экраны */
        @media (max-width: 600px) {
            body { padding: 6px; }
            .container { padding: 10px 8px; border-radius: 12px; }
            h1 { font-size: 18px; }
            .filters { gap: 6px; }
            .filter-btn {
                font-size: 12px;
                padding: 6px 12px;
            }
            table { font-size: 12px; min-width: 380px; }
            th { font-size: 11px; padding: 6px 4px; }
            td { padding: 8px 4px; }
            .totals {
                grid-template-columns: 1fr 1fr;
                padding: 10px 8px;
                gap: 4px 12px;
            }
            .totals .value { font-size: 16px; }
            .total-people-block .value { font-size: 22px; }
            .date-form input[type="date"] { font-size: 14px; padding: 8px 10px; }
            .date-form button { font-size: 14px; padding: 8px 16px; }
        }

        @media (max-width: 400px) {
            table { font-size: 11px; min-width: 320px; }
            th, td { padding: 5px 3px; }
            .totals {
                grid-template-columns: 1fr;
                text-align: center;
            }
            .totals .value { text-align: center; }
            .total-people-block {
                flex-direction: column;
                gap: 4px;
            }
        }
    </style>
</head>
<body>
<div class="container">
    <h1><span>🍽</span> Столовая</h1>
    <div class="subtitle">Заказы на {{ date }}</div>

    <div class="filters">
        <a href="?date={{ date }}&meal=" class="filter-btn {{ 'active' if meal_filter == '' or meal_filter == None else '' }}">Все</a>
        <a href="?date={{ date }}&meal=завтрак" class="filter-btn {{ 'active' if meal_filter == 'завтрак' else '' }}">🌅 Завтрак</a>
        <a href="?date={{ date }}&meal=обед" class="filter-btn {{ 'active' if meal_filter == 'обед' else '' }}">🌞 Обед</a>
    </div>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Класс</th>
                    <th>Приём</th>
                    <th>💳 Плат</th>
                    <th>🆓 Бесп</th>
                    <th>⭐ СВО</th>
                    <th>♿ ОВЗ</th>
                    <th>Всего</th>
                    <th>Статус</th>
                </tr>
            </thead>
            <tbody>
            {% for row in orders %}
                <tr>
                    <td class="class-name">{{ row[1] }}</td>
                    <td><span class="meal-type">{{ row[2] }}</span></td>
                    <td class="num plat">{{ row[3] }}</td>
                    <td class="num bes">{{ row[4] }}</td>
                    <td class="num svo">{{ row[5] }}</td>
                    <td class="num ovz">{{ row[6] }}</td>
                    <td><span class="total-cell">{{ row[3] + row[4] + row[5] + row[6] }}</span></td>
                    <td><span class="status-{{ row[7] }}">{{ row[7] }}</span></td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="totals">
        <div><span class="label">💳 Платники</span></div>
        <div class="value plat">{{ total_plat }}</div>

        <div><span class="label">🆓 Бесплатники</span></div>
        <div class="value bes">{{ total_bes }}</div>

        <div><span class="label">⭐ СВО</span></div>
        <div class="value svo">{{ total_svo }}</div>

        <div><span class="label">♿ ОВЗ</span></div>
        <div class="value ovz">{{ total_ovz }}</div>

        <div class="total-people-block">
            <span class="label">👥 Всего человек</span>
            <span class="value people">{{ total_people }}</span>
        </div>
    </div>

    <form method="GET" class="date-form">
        <label for="date">📅 Дата:</label>
        <input type="date" id="date" name="date" value="{{ date }}">
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

    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    query = '''
        SELECT u.full_name, o.class_name, o.meal_type, o.count_plat, o.count_bes, o.count_svo, o.count_ovz, o.status
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE DATE(o.order_date) = ?
    '''
    params = [date_str]

    if meal_filter and meal_filter != '':
        query += " AND o.meal_type = ?"
        params.append(meal_filter)

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()

    total_plat = sum(r[3] for r in rows)
    total_bes = sum(r[4] for r in rows)
    total_svo = sum(r[5] for r in rows)
    total_ovz = sum(r[6] for r in rows)
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)