# Хэндлер команды /venom
async def venom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    username = update.effective_user.username

    # Используем first_name, если оно есть, иначе используем username
    user_mention = f"<a href='tg://user?id={user_id}'>{first_name}</a>" if first_name else f"<a href='tg://user?id={user_id}'>{username}</a>"

    try:
        # Извлекаем данные пользователя из базы данных
        cursor.execute("SELECT total, last_used FROM users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        # Если пользователя нет в базе данных, добавляем его
        if result is None:
            cursor.execute("INSERT INTO users (user_id, username, total, last_used) VALUES (%s, %s, 0, %s)", 
                           (user_id, username, datetime.now()))
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
        conn.rollback()  # Откат транзакции при ошибке
        logging.error(f"Ошибка при обработке команды /venom: {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашей команды. Попробуйте позже.")


