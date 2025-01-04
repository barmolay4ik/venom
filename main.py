import os
import logging
import psycopg2
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime, timedelta
import random
import asyncio
from threading import Thread

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
    try:
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

        # Получаем текущее время и время, когда пользователь может выполнить команду (14:00 текущего дня)
        now = datetime.now()
        target_time = now.replace(hour=14, minute=0, second=0, microsecond=0)

        # Инициализация переменной для позиции
        position = None

        # Если last_used до 14:00, то сбрасываем кулдаун и разрешаем пользователю выполнить команду
        if last_used and last_used < target_time:
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

            # Получаем текущий рейтинг пользователя в топе
            cursor.execute("SELECT user_id, total FROM users ORDER BY total DESC")
            top_users = cursor.fetchall()
            position = next((i+1 for i, (uid, _) in enumerate(top_users) if uid == user_id), None)

            # Если пользователь не в топ-10, выводим "10+" в позиции
            if position is None or position > 10:
                position = "10+"

            # Отправляем сообщение с новым значением
            await update.message.reply_text(
                f"{user_mention}, ты стал VENOMОМ на {new_total}% (+{added_value}).\n"
                f"Сейчас ты venom на {new_total}%. \n"
                f"Ты занимаешь {position} место в топе.\n"
                "Следующая попытка завтра!",
                parse_mode="HTML"
            )
        else:
            # Если последняя попытка была после 14:00, проверяем, прошло ли 14 часов
            if last_used and now - last_used < timedelta(hours=14):
                remaining_time = timedelta(hours=14) - (now - last_used)
                hours, remainder = divmod(remaining_time.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                await update.message.reply_text(
                    f"{user_mention}, ты уже играл.\nСейчас ты venom на {total}%.\n"
                    f"Ты занимаешь {position} место в топе.\n"
                    "Следующая попытка завтра!",
                    parse_mode="HTML"
                )
            else:
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

                # Получаем текущий рейтинг пользователя в топе
                cursor.execute("SELECT user_id, total FROM users ORDER BY total DESC")
                top_users = cursor.fetchall()
                position = next((i+1 for i, (uid, _) in enumerate(top_users) if uid == user_id), None)

                # Если пользователь не в топ-10, выводим "10+" в позиции
                if position is None or position > 10:
                    position = "10+"

                # Отправляем сообщение с новым значением
                await update.message.reply_text(
                    f"{user_mention}, ты стал VENOMОМ на {new_total}% (+{added_value}).\n"
                    f"Сейчас ты venom на {new_total}%. \n"
                    f"Ты занимаешь {position} место в топе.\n"
                    "Следующая попытка завтра!",
                    parse_mode="HTML"
                )
    except Exception as e:
        # Если произошла ошибка, откатываем транзакцию
        conn.rollback()
        logging.error(f"Ошибка в команде /venom: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте снова позже.")


# Хэндлер команды /top
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Получаем до 10 пользователей с наибольшими значениями
        cursor.execute("SELECT user_id, total FROM users ORDER BY total DESC LIMIT 10")
        top_users = cursor.fetchall()

        if not top_users:
            await update.message.reply_text("Топ веномов пуст.")
            return

        top_list = ""
        position = None  # Для хранения позиции пользователя
        user_id = update.effective_user.id

        # Формируем список топ-10 (или меньше, если их меньше)
        for i, (db_user_id, total) in enumerate(top_users, start=1):
            cursor.execute("SELECT username FROM users WHERE user_id = %s", (db_user_id,))
            user_info = cursor.fetchone()
            username = user_info[0]  # Используем username
            top_list += f"{i}|<b>{username}</b> — {total}%\n"  # Отображаем ник в жирном шрифте

            # Проверяем, если текущий пользователь в топе
            if db_user_id == user_id:
                position = i

        # Если пользователя нет в топе, выводим "10+" в позиции
        if position is None or position > 10:
            position = "10+"

        # Отправляем сообщение
        await update.message.reply_text(
            f"Топ веномов:\n{top_list}\nТы занимаешь {position} место в топе.",
            parse_mode="HTML"
        )

    except Exception as e:
        logging.error(f"Ошибка в команде /top: {e}")
        await update.message.reply_text("Произошла ошибка при получении топа. Попробуйте снова позже.")



# Добавление хэндлеров для команд
application.add_handler(CommandHandler("venom", venom))
application.add_handler(CommandHandler("top", top))

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
