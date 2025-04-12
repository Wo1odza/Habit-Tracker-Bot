import telebot
import schedule
import time
import threading
import sqlite3
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import API_bot

bot = telebot.TeleBot(API_bot)

# Инициализация базы данных
conn = sqlite3.connect('habits.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
CREATE TABLE IF NOT EXISTS habits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    habit_name TEXT,
    day_of_week INTEGER,
    habit_time TEXT,
    remove_after_first INTEGER DEFAULT 0
)
''')
conn.commit()


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    keyboard = InlineKeyboardMarkup(row_width=1)  # Чтобы кнопки были одна под другой
    keyboard.add(
        InlineKeyboardButton("Список привычек", callback_data="list_habits"),
        InlineKeyboardButton("Добавить привычку", callback_data="add_habit_info"),
        InlineKeyboardButton("Удалить привычку", callback_data="remove_habit_menu"),
        InlineKeyboardButton("Редактировать привычку", callback_data="edit_habit_menu")
    )
    bot.reply_to(message,
                 "Привет! Я помогу тебе следить за привычками.\n\n"
                 "**Доступные команды:**\n"
                 "/add_habit - Добавить новую привычку\n"
                 "/remove_habit - Удалить существующую привычку\n"
                 "/start или /help - Показать это сообщение\n"
                 "Кнопки ниже - Быстрый доступ к функциям\n",
                 reply_markup=keyboard, parse_mode="Markdown")  # Добавляем форматирование Markdown


@bot.message_handler(commands=['add_habit'])
def add_habit(message):
    bot.reply_to(message, "Пожалуйста, отправьте данные для новой привычки в формате: 'Название привычки, день недели (где 0 это понедельник и 6 это воскресенье), время (HH:MM), тип (1 - удалить после первого напоминания, 0 - навсегда)'.")


# --- Редактирование привычек ---
@bot.callback_query_handler(func=lambda call: call.data == "edit_habit_menu")
def edit_habit_menu(call):
    user_id = call.message.chat.id
    cursor.execute('SELECT id, habit_name FROM habits WHERE user_id = ?', (user_id,))
    habits = cursor.fetchall()

    if not habits:
        bot.answer_callback_query(call.id, "У вас нет привычек для редактирования.")
        bot.send_message(call.message.chat.id, "У вас нет привычек для редактирования.")
        return

    markup = InlineKeyboardMarkup(row_width=1)
    for habit in habits:
        markup.add(InlineKeyboardButton(habit[1], callback_data=f"edit_{habit[0]}"))  # Используем ID привычки
    markup.add(InlineKeyboardButton("Отмена", callback_data="cancel"))

    bot.send_message(call.message.chat.id, "Выберите привычку для редактирования:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
def edit_habit_selected(call):
    habit_id = int(call.data.split("_")[1])
    user_id = call.message.chat.id
    # Сохраняем ID привычки, которую редактируем
    bot.register_next_step_handler(call.message, edit_habit_data, habit_id)  # Передаем habit_id

    bot.send_message(call.message.chat.id,
                     "Отправьте новые данные для привычки в формате: 'Название привычки, день недели (0-6), время (HH:MM), тип (0 или 1)'.")


def edit_habit_data(message, habit_id): # Получаем habit_id
    try:
        habit_data = message.text.split(',')
        if len(habit_data) != 4:
            raise ValueError("Неверный формат данных.")

        habit_name = habit_data[0].strip()
        day_of_week = int(habit_data[1].strip())
        habit_time = habit_data[2].strip()
        remove_after_first = int(habit_data[3].strip())

        if day_of_week < 0 or day_of_week > 6:
            raise ValueError("Неверный день недели. Используйте числа от 0 (понедельник) до 6 (воскресенье).")

        if not habit_time or len(habit_time) != 5 or habit_time[2] != ':':
            raise ValueError("Неверный формат времени. Используйте формат HH:MM.")

        if remove_after_first not in [0, 1]:
            raise ValueError("Неверный тип. Используйте 0 или 1.")

        user_id = message.chat.id
        cursor.execute('''
            UPDATE habits
            SET habit_name = ?, day_of_week = ?, habit_time = ?, remove_after_first = ?
            WHERE id = ? AND user_id = ?
        ''', (habit_name, day_of_week, habit_time, remove_after_first, habit_id, user_id))  # Обновляем по ID
        conn.commit()

        # Обновляем расписание
        schedule.clear(tag=f"{user_id}_{habit_id}") # Сначала удаляем старую задачу
        schedule_habit_reminder(user_id, habit_name, day_of_week, habit_time, remove_after_first, habit_id) # Создаем новую

        bot.reply_to(message, f"Привычка '{habit_name}' успешно отредактирована!")

    except ValueError as e:
        bot.reply_to(message, str(e))
    except Exception as e:
        print(f"Произошла ошибка при редактировании привычки: {e}")
        bot.reply_to(message, "Произошла ошибка при обработке запроса.")
# ---  Конец редактирования привычек ---



# --- Удаление с подтверждением ---
@bot.callback_query_handler(func=lambda call: call.data == "remove_habit_menu")
def remove_habit_menu(call):
    user_id = call.message.chat.id
    cursor.execute('SELECT id, habit_name FROM habits WHERE user_id = ?', (user_id,))
    habits = cursor.fetchall()

    if not habits:
        bot.answer_callback_query(call.id, "У вас нет добавленных привычек.")
        bot.send_message(call.message.chat.id, "У вас нет добавленных привычек.") # Отправляем сообщение, если нет привычек
        return

    markup = InlineKeyboardMarkup()
    for habit in habits:
        markup.add(InlineKeyboardButton(habit[1], callback_data=f"confirm_remove_{habit[0]}"))  # добавляем префикс
    markup.add(InlineKeyboardButton("Отмена", callback_data="cancel"))

    bot.send_message(call.message.chat.id, "Выберите привычку для удаления:", reply_markup=markup)



@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_remove_"))
def confirm_remove_habit(call):
    habit_id = int(call.data.split("_")[2])  # извлекаем habit_id
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Да, удалить", callback_data=f"remove_{habit_id}"),
               InlineKeyboardButton("Нет, отмена", callback_data="cancel"))
    bot.send_message(call.message.chat.id, "Вы уверены, что хотите удалить эту привычку?", reply_markup=markup)
# --- Конец удаления с подтверждением ---

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith("remove_"):
        habit_id = int(call.data.split("_")[1])
        user_id = call.message.chat.id # Получаем user_id
        cursor.execute('DELETE FROM habits WHERE id = ? AND user_id = ?', (habit_id, user_id))  # Добавляем условие user_id
        conn.commit()
        bot.answer_callback_query(call.id, "Привычка удалена!")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Привычка удалена!")
        # Удаляем задачу из планировщика (если она есть)
        schedule.clear(tag=f"{call.message.chat.id}_{habit_id}")
    elif call.data == "cancel":
        bot.answer_callback_query(call.id, "Отмена!")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Отмена!")
    elif call.data == "list_habits":
        user_id = call.message.chat.id
        cursor.execute('SELECT habit_name, day_of_week, habit_time, remove_after_first FROM habits WHERE user_id = ?', (user_id,))
        habits = cursor.fetchall()

        if not habits:
            bot.answer_callback_query(call.id, "У вас пока нет привычек.")
            bot.send_message(call.message.chat.id, "У вас пока нет привычек.")
            return

        habit_list_text = "Ваши привычки:\n"
        for habit in habits:
            habit_name, day_of_week, habit_time, remove_after_first = habit
            day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            remove_text = "Удалить после первого напоминания" if remove_after_first == 1 else "Постоянная привычка"
            habit_list_text += f"- {habit_name}, {day_names[day_of_week]}, {habit_time}, {remove_text}\n"

        bot.answer_callback_query(call.id, "Список привычек:")
        bot.send_message(call.message.chat.id, habit_list_text)

    elif call.data == "add_habit_info":
        bot.answer_callback_query(call.id, "Как добавить привычку")
        bot.send_message(call.message.chat.id, "Чтобы добавить привычку, используйте команду /add_habit или нажмите соответствующую кнопку.  Затем отправьте данные в формате: 'Название привычки, день недели (0-6), время (HH:MM), тип (0 или 1)'.")


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        habit_data = message.text.split(',')
        if len(habit_data) != 4:
            raise ValueError("Неверный формат данных.")

        habit_name = habit_data[0].strip()
        day_of_week = int(habit_data[1].strip())
        habit_time = habit_data[2].strip()
        remove_after_first = int(habit_data[3].strip())

        if day_of_week < 0 or day_of_week > 6:
            raise ValueError("Неверный день недели. Используйте числа от 0 (понедельник) до 6 (воскресенье).")

        if not habit_time or len(habit_time) != 5 or habit_time[2] != ':':
            raise ValueError("Неверный формат времени. Используйте формат HH:MM.")

        if remove_after_first not in [0, 1]:
            raise ValueError("Неверный тип. Используйте 0 или 1.")

        user_id = message.chat.id
        cursor.execute('INSERT INTO habits (user_id, habit_name, day_of_week, habit_time, remove_after_first) VALUES (?, ?, ?, ?, ?)',
                       (user_id, habit_name, day_of_week, habit_time, remove_after_first))
        conn.commit()
        habit_id = cursor.lastrowid # Получаем ID только что добавленной привычки

        bot.reply_to(message, f"Привычка '{habit_name}' добавлена!")

        # Планируем напоминание
        schedule_habit_reminder(user_id, habit_name, day_of_week, habit_time, remove_after_first, habit_id)

    except ValueError as e:
        bot.reply_to(message, str(e))
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        bot.reply_to(message, "Произошла ошибка при обработке запроса.")


def schedule_habit_reminder(user_id, habit_name, day_of_week, habit_time, remove_after_first, habit_id):
    def send_reminder():
        bot.send_message(user_id, f"Напоминание: сделайте '{habit_name}'!")
        if remove_after_first == 1:
            # Удаляем привычку из базы данных
            cursor.execute('DELETE FROM habits WHERE id = ?', (habit_id,))
            conn.commit()

            # Удаляем задачу из планировщика
            schedule.clear(tag=f"{user_id}_{habit_id}")
            print(f"Удалена привычка '{habit_name}' (ID: {habit_id}) пользователя {user_id} после первого напоминания.")

    # Планируем задачу
    schedule.every().day.at(habit_time).do(send_reminder).tag(f"{user_id}_{habit_id}")

    # Запускаем планировщик в отдельном потоке
    threading.Thread(target=run_scheduler).start()


def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)


# Загрузка существующих привычек из базы данных и планирование напоминаний
def load_habits():
    cursor.execute('SELECT id, user_id, habit_name, day_of_week, habit_time, remove_after_first FROM habits')
    habits = cursor.fetchall()
    for habit in habits:
        habit_id, user_id, habit_name, day_of_week, habit_time, remove_after_first = habit
        schedule_habit_reminder(user_id, habit_name, day_of_week, habit_time, remove_after_first, habit_id)


# Загружаем привычки при запуске бота
load_habits()

bot.infinity_polling()