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
    habit_time TEXT
)
''')
conn.commit()

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Я помогу тебе следить за привычками. Используй команду /add_habit, чтобы добавить новую привычку, и /remove_habit, чтобы удалить привычку.")

@bot.message_handler(commands=['add_habit'])
def add_habit(message):
    bot.reply_to(message, "Пожалуйста, отправьте данные для новой привычки в формате: 'Название привычки, день недели (где 0 это понедельник и 6 это воскресенье), время (HH:MM)'.")

@bot.message_handler(commands=['remove_habit'])
def remove_habit(message):
    user_id = message.chat.id
    cursor.execute('SELECT id, habit_name FROM habits WHERE user_id = ?', (user_id,))
    habits = cursor.fetchall()

    if not habits:
        bot.reply_to(message, "У вас нет добавленных привычек.")
        return

    markup = InlineKeyboardMarkup()
    for habit in habits:
        markup.add(InlineKeyboardButton(habit[1], callback_data=f"remove_{habit[0]}"))
    markup.add(InlineKeyboardButton("Отмена", callback_data="cancel"))

    bot.send_message(message.chat.id, "Выберите привычку для удаления:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data.startswith("remove_"):
        habit_id = int(call.data.split("_")[1])
        cursor.execute('DELETE FROM habits WHERE id = ?', (habit_id,))
        conn.commit()
        bot.answer_callback_query(call.id, "Привычка удалена!")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Привычка удалена!")
    elif call.data == "cancel":
        bot.answer_callback_query(call.id, "Отмена!")
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Отмена!")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    try:
        habit_data = message.text.split(',')
        if len(habit_data) != 3:
            raise ValueError("Неверный формат данных.")

        habit_name = habit_data[0].strip()
        day_of_week = int(habit_data[1].strip())
        habit_time = habit_data[2].strip()

        if day_of_week < 0 or day_of_week > 6:
            raise ValueError("Неверный день недели. Используйте числа от 0 (понедельник) до 6 (воскресенье).")

        if not habit_time or len(habit_time) != 5 or habit_time[2] != ':':
            raise ValueError("Неверный формат времени. Используйте формат HH:MM.")

        user_id = message.chat.id
        cursor.execute('INSERT INTO habits (user_id, habit_name, day_of_week, habit_time) VALUES (?, ?, ?, ?)',
                       (user_id, habit_name, day_of_week, habit_time))
        conn.commit()

        bot.reply_to(message, f"Привычка '{habit_name}' добавлена!")

        # Планируем напоминание
        schedule_habit_reminder(user_id, habit_name, day_of_week, habit_time)

    except ValueError as e:
        bot.reply_to(message, str(e))
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        bot.reply_to(message, "Произошла ошибка при обработке запроса.")

def schedule_habit_reminder(user_id, habit_name, day_of_week, habit_time):
    def send_reminder():
        bot.send_message(user_id, f"Напоминание: сделайте '{habit_name}'!")

    # Планируем задачу
    schedule.every().day.at(habit_time).do(send_reminder).tag(f"{user_id}_{habit_name}")

    # Запускаем планировщик в отдельном потоке
    threading.Thread(target=run_scheduler).start()

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

# Загрузка существующих привычек из базы данных и планирование напоминаний
def load_habits():
    cursor.execute('SELECT user_id, habit_name, day_of_week, habit_time FROM habits')
    habits = cursor.fetchall()
    for habit in habits:
        user_id, habit_name, day_of_week, habit_time = habit
        schedule_habit_reminder(user_id, habit_name, day_of_week, habit_time)

# Загружаем привычки при запуске бота
load_habits()

bot.infinity_polling()