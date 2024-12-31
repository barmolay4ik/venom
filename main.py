import random
import time
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from flask import Flask
from threading import Thread

# Токен вашего бота
TOKEN = "7898615918:AAFZwC8uNnlZD8rQ5n-npbP-PAD9U4KdK8Y"

# Словарь для хранения результата каждого пользователя
user_scores = {}
# Словарь для хранения времени последнего использования команды для каждого пользователя
user_last_used = {}

# Загрузка данных из файла
def load_data():
    global user_scores, user_last_used
    try:
        with open("user_data.json", "r") as file:
            data = json.load(file)
            user_scores = data["scores"]
            user_last_used = data["last_used"]
            print("Данные загружены успешно.")
    except (FileNotFoundError, json.JSONDecodeError):
        # Если файл не найден или поврежден, создаем новый пустой словарь
        user_scores = {}
        user_last_used = {}
        print("Файл не найден или поврежден. Используются пустые данные.")

# Сохранение данных в файл
def save_data():
    try:
        with open("user_data.json", "w") as file:
            json.dump({"scores": user_scores, "last_used": user_last_used}, file)
            print("Данные сохранены успешно.")
    except Exception as e:
        print(f"Ошибка при сохранении данных: {e}")

# Функция для обработки команды /venom
async def venom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # Уникальный ID пользователя
    user_mention = update.effective_user.mention_html()  # Кликабельное упоминание

    # Получаем текущее время в секундах
    current_time = time.time()

    # Проверяем, был ли использован бот за последние 24 часа
    if user_id in user_last_used:
        time_diff = current_time - user_last_used[user_id]
        if time_diff < 86400:  # 86400 секунд = 24 часа
            # Считаем, сколько осталось времени до следующей команды
            remaining_time = 86400 - time_diff
            remaining_hours = int(remaining_time // 3600)
            remaining_minutes = int((remaining_time % 3600) // 60)
            remaining_seconds = int(remaining_time % 60)

            # Формируем сообщение с оставшимся временем
            await update.message.reply_text(
                f"{user_mention}, НЕ АХУЕВАЙ\nНапишешь через {remaining_hours}ч {remaining_minutes}м {remaining_seconds}с петух",
                parse_mode=ParseMode.HTML
            )
            return

    # Генерируем случайное число от 1 до 5
    random_number = random.randint(1, 5)

    # Если пользователь уже есть в словаре, прибавляем к его текущему результату
    if user_id in user_scores:
        user_scores[user_id] += random_number
    else:
        user_scores[user_id] = random_number

    # Получаем общий результат
    total_score = user_scores[user_id]

    # Обновляем время последнего использования команды
    user_last_used[user_id] = current_time

    # Проверяем, не достиг ли пользователь 100%
    if total_score >= 100:
        await update.message.reply_text(
            f"{user_mention}, ТЫ VENOM", parse_mode=ParseMode.HTML
        )
        # После достижения 100%, можно обнулить или оставить его на 100%
        user_scores[user_id] = 100  # Обнуляем или оставляем на 100%
    else:
        # Формируем сообщение с текущим результатом
        await update.message.reply_text(
            f"{user_mention}, Ты стал VENOMOM на {total_score}% (+{random_number})",
            parse_mode=ParseMode.HTML
        )

    # Сохраняем данные
    save_data()

def main():
    # Загружаем данные перед запуском бота
    load_data()

    # Создаем объект приложения с токеном
    app = ApplicationBuilder().token(TOKEN).build()

    # Добавляем обработчик команды /venom
    app.add_handler(CommandHandler("venom", venom))

    # Запускаем бота
    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    app.run_polling()

# Flask приложение для работы 24/7
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running!"

def run_flask():
    # Flask должен слушать на порту 3000
    flask_app.run(host="0.0.0.0", port=3000)

def run_bot():
    main()

if __name__ == "__main__":
    # Запускаем Flask сервер в отдельном потоке
    t1 = Thread(target=run_flask)
    t1.start()

    # Запускаем Telegram бота
    run_bot()
