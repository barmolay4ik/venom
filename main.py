import os
import json
import logging
from flask import Flask
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from datetime import datetime, time
import pytz

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

# Часовой пояс для Киева
KYIV_TZ = pytz.timezone("Europe/Kyiv")

# Путь к файлу для хранения данных
DATA_FILE = "user_data.json"

# Функция для загрузки данных из файла
def load_user_data():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as file:
                return json.load(file)
    except json.JSONDecodeError:
        logging.warning("Файл данных повреждён. Загружены пустые данные.")
    return {}

# Функция для сохранения данных в файл
def save_user_data():
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(user_data, file, ensure_ascii=False, indent=4)

# Загрузка данных пользователей
user_data = load_user_data()

# Хэндлер команды /venom
async def venom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    username = update.effective_user.first_name  # Имя пользователя
    user_id = str(update.effective_user.id)     # ID пользователя (строка для JSON)

    # Генерация HTML ссылки
    user_link = f'<a href="tg://user?id={user_id}">{username}</a>'

    # Получение текущей даты и времени в часовом поясе Киева
    now = datetime.now(KYIV_TZ)
    today_reset_time = datetime.combine(now.date(), time(14, 0), tzinfo=KYIV_TZ)

    # Проверка, если текущее время до 19:00
    if now < today_reset_time:
        await update.message.reply_text(
            f"{user_link}, ты уже играл.\nСейчас ты venom на {user_data.get(user_id, {'total': 0})['total']}%\nСледующая попытка сегодня в 14:00!",
            parse_mode=ParseMode.HTML
        )
        return

    # Если пользователь уже играл сегодня после 19:00
    if user_id in user_data and user_data[user_id]["last_used"] >= today_reset_time.isoformat():
        await update.message.reply_text(
            f"{user_link}, ты уже играл.\nСейчас ты venom на {user_data[user_id]['total']}%\nСледующая попытка завтра!",
            parse_mode=ParseMode.HTML
        )
        return

    # Генерация случайного числа от 1 до 5
    import random
    added_value = random.randint(1, 5)

    # Обновление данных пользователя
    if user_id not in user_data:
        user_data[user_id] = {"total": 0, "last_used": None}

    user_data[user_id]["total"] += added_value
    user_data[user_id]["last_used"] = now.isoformat()

    # Сохранение данных после обновления
    save_user_data()

    # Проверка на достижение 100%
    if user_data[user_id]["total"] >= 100:
        await update.message.reply_text(
            f"{user_link}, ТЫ VENOM!",
            parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text(
            f"{user_link}, ты стал VENOMOM на {user_data[user_id]['total']}% (+{added_value})\nСледующая попытка завтра!",
            parse_mode=ParseMode.HTML
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
