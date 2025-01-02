import os
import logging
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

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

# Словарь для хранения данных пользователей
user_data = {}

# Хэндлер команды /venom
async def venom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.effective_user.username
    user_id = update.effective_user.id

    # Получение текущего значения и проверка на существование
    if user_id not in user_data:
        user_data[user_id] = {"total": 0, "last_used": None}

    # Проверка cooldown (24 часа)
    from datetime import datetime, timedelta
    now = datetime.now()
    if user_data[user_id]["last_used"] and now - user_data[user_id]["last_used"] < timedelta(hours=24):
        remaining_time = timedelta(hours=24) - (now - user_data[user_id]["last_used"])
        hours, remainder = divmod(remaining_time.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        await update.message.reply_text(
            f"@{username}, НЕ АХУЕВАЙ\nНапишешь через {hours}ч {minutes}м, петух!\nНе думай что я слабак"
        )
        return

    # Генерация случайного числа от 1 до 5
    import random
    added_value = random.randint(1, 5)

    # Обновление значений пользователя
    user_data[user_id]["total"] += added_value
    user_data[user_id]["last_used"] = now

    # Проверка на достижение 100%
    if user_data[user_id]["total"] >= 100:
        await update.message.reply_text(f"@{username}, ТЫ VENOM!")
    else:
        await update.message.reply_text(
            f"@{username}, Ты стал VENOMOM на {user_data[user_id]['total']}% (+{added_value})"
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
