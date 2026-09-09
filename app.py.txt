import threading
import os
import time

def run_bot():
    try:
        os.system("python bot.py")
    except Exception as e:
        print(f"❌ Бот упал: {e}")

def run_web():
    try:
        os.system("gunicorn web_panel:app --bind 0.0.0.0:5000")
    except Exception as e:
        print(f"❌ Веб-панель упала: {e}")

if __name__ == "__main__":
    print("🚀 Запуск бота и веб-панели...")
    
    # Запускаем бота в фоне
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    time.sleep(2)
    
    # Запускаем веб-панель
    run_web()