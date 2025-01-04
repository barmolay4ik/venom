import os
import logging
import psycopg2
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime, timedelta
import random

# Инициализация Flask
app = Flask(__name__)

# Логгер для Telegram API
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Ваш токен Telegram-бота
TOKEN = "7898615918:AAFZwC8uNnlZD8rQ5n-npbP-PAD9U4KdK8Y"

# Инициализация Telegram бота
application = ApplicationBuilder().token(TOKEN).build()

# Получаем строку подключения к базе данных
DATABASE_URL = os.getenv('DATABASE_URL')

# Подключаемся к базе данных PostgreSQL
conn = psycopg2.connect(DATABASE_URL, sslmode='require')
cursor = conn.cursor()

# Создаем таблицу для хранения данных пользователей, если она не существует
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    total INTEGER,
    last_used TIMESTAMP
)
""")
conn.commit()

# Хэндлер команды /venom
async def venom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    # Используем first_name, если оно есть, иначе используем username
    user_mention = f"<a href='tg://user?id={user_id}'>{first_name}</a>" if first_name else f"<a href='tg://user?id={user_id}'>{username}</a>"

    # Извлекаем данные пользователя из базы данных
    cursor.execute("SELECT total, last_used FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    # Если пользователя нет в базе данных, добавляем его
    if result is None:
        cursor.execute("INSERT INTO users (user_id, total, last_used) VALUES (%s, 0, %s)", (user_id, datetime.now()))
        conn.commit()
        total, last_used = 0, None
    else:
        total, last_used = result

    # Проверка на доступность попытки (в 19:00 по Киеву)
    now = datetime.now()
    target_time = now.replace(hour=14, minute=0, second=0, microsecond=0)

    if last_used and now < target_time:
        remaining_time = target_time - now
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        await update.message.reply_text(
            f"{user_mention}, ты уже играл.\nСейчас ты venom на {total}%\nСледующая попытка завтра!",
            parse_mode="HTML"
        )
        return

    # Генерация случайного числа от 1 до 5
    added_value = random.randint(1, 5)

    # Обновление значений пользователя в базе данных
    new_total = total + added_value
    cursor.execute("""
        UPDATE users 
        SET total = %s, last_used = %s 
        WHERE user_id = %s
    """, (new_total, now, user_id))
    conn.commit()

    # Проверка на достижение 100%
    if new_total >= 100:
        await update.message.reply_text(f"{user_mention}, ТЫ VENOM!", parse_mode="HTML")
    else:
        await update.message.reply_text(
            f"{user_mention}, ты стал VENOMОМ на {new_total}% (+{added_value})\nСледующая попытка завтра!",
            parse_mode="HTML"
        )

# Добавление хэндлера для команды /venom
application.add_handler(CommandHandler("venom", venom))

@app.route("/")
def home():
    return "Бот работает!"

def run_telegram_bot():
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    from threading import Thread

    # Запуск Flask в отдельном потоке
    thread = Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000))))
    thread.start()

    # Запуск Telegram бота
    run_telegram_bot()
