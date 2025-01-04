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
    username TEXT,
    total INTEGER,
    last_used TIMESTAMP
)
""")
conn.commit()

# Хэндлер команды /venom
async def venom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name

    # Используем first_name для упоминания
    user_mention = f"<a href='tg://user?id={user_id}'>{first_name}</a>" if first_name else f"<a href='tg://user?id={user_id}'>{user_id}</a>"

    try:
        # Извлекаем данные пользователя из базы данных
        cursor.execute("SELECT total, last_used FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        # Если пользователя нет в базе данных, добавляем его
        if result is None:
            cursor.execute("INSERT INTO users (user_id, username, total, last_used) VALUES (%s, NULL, 0, %s)", 
                           (user_id, datetime.now()))
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

            # Получаем все данные пользователей и сортируем по total в убывающем порядке
            cursor.execute("SELECT user_id, total FROM users ORDER BY total DESC")
            top_users = cursor.fetchall()

            # Определяем позицию пользователя
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

                # Получаем все данные пользователей и сортируем по total в убывающем порядке
                cursor.execute("SELECT user_id, total FROM users ORDER BY total DESC")
                top_users = cursor.fetchall()

                # Определяем позицию пользователя
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
        conn.rollback()  # Откат транзакции при ошибке
        logging.error(f"Ошибка при обработке команды /venom: {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашей команды. Попробуйте позже.")




# Хэндлер команды /top
async def top(update, context):
    user_id = update.effective_user.id
    cursor = conn.cursor()

    # Получаем данные о пользователе и его месте в топе
    try:
        cursor.execute("""
            SELECT user_id, total, 
                RANK() OVER (ORDER BY total DESC) AS rank
            FROM users
        """)
        users_data = cursor.fetchall()

        # Находим место пользователя
        user_rank = None
        for user in users_data:
            if user[0] == user_id:
                user_rank = user[2]  # Индекс 2 - это место пользователя
                break

        if user_rank:
            await update.message.reply_text(f"Ты занимаешь {user_rank}-е место в топе!")
        else:
            await update.message.reply_text("Ты еще не в топе. Попробуй набрать больше очков!")

    except Exception as e:
        await update.message.reply_text("Произошла ошибка при получении данных топа.")
        print(f"Ошибка в команде 'топ': {e}")

    finally:
        cursor.close()


# Хэндлер команды /debug для вывода всех пользователей и их данных
async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cursor.execute("SELECT user_id, total, last_used, username FROM users")
    users = cursor.fetchall()

    if not users:
        await update.message.reply_text("Нет пользователей в базе данных.")
        return

    debug_info = "Все пользователи:\n"
    for user_id, total, last_used, username in users:
        # Если username отсутствует, выводим "none"
        username_display = username if username else "none"
        debug_info += f"ID: {user_id}, Username: {username_display}, Total: {total}, Last Used: {last_used}\n"

    await update.message.reply_text(debug_info)


# Добавление хэндлера команды /debug
application.add_handler(CommandHandler("debug", debug))

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



