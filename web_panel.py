from flask import Flask, render_template_string, request
import os
import datetime
import urllib.parse

app = Flask(__name__)

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

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🍽 Панель столовой</title>
    <style>
        body { font-family: Arial, sans