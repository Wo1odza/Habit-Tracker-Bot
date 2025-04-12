# Habit Tracker Telegram Bot

This Telegram bot helps you track your habits and stay motivated!  It allows you to add, remove, edit, and list your habits, and will send you reminders at the specified times.

## Features

*   **Add Habits:** Easily add new habits with details like name, day of the week, time, and whether to remove them after the first reminder.
*   **Remove Habits:** Delete unwanted habits with a confirmation step to prevent accidental deletions.
*   **Edit Habits:** Modify existing habits, including their name, day of the week, time, and removal type.
*   **List Habits:** View a list of all your currently tracked habits, including their settings.
*   **Reminders:**  Receive scheduled reminders to help you stay on track with your habits.
*   **One-Time Habits:**  Option to have a habit removed automatically after the first reminder (useful for tasks that only need to be done once).
*   **Informative /start Command:** Provides a clear overview of available commands and features.
*   **Inline Keyboard Navigation:**  Easy navigation using inline keyboard buttons in the main menu.

## Usage

1.  **Start the bot:**  Open the bot in Telegram and use the `/start` or `/help` command.

2.  **Add a habit:**

    *   Use the `/add_habit` command.
    *   Follow the format: `Habit Name, Day of the Week (0-6, where 0 is Monday and 6 is Sunday), Time (HH:MM), Type (0 for repeating habit, 1 for remove after first reminder)`
    *   Example: `Drink Water, 1, 10:00, 0`  (This adds a repeating habit to drink water every Tuesday at 10:00 AM)
    * You can also use the "Add Habit" button in the `/start` menu to see the instructions.

3.  **Remove a habit:**

    *   Use the `/remove_habit` command.
    *   Select the habit you want to remove from the list.
    *   Confirm the removal.

4.  **Edit a habit:**

    *   Use the "Edit Habit" button in the `/start` menu.
    *   Select the habit you want to edit.
    *   Follow the format: `Habit Name, Day of the Week (0-6), Time (HH:MM), Type (0 or 1)` to enter new details for the selected habit.

5.  **List your habits:**

    *   Use the "List Habits" button in the `/start` menu to view a list of your currently tracked habits.

## Setup

1.  **Prerequisites:**
    *   Python 3.6 or higher
    *   Telegram account
    *   [Create a Telegram Bot](https://core.telegram.org/bots#how-do-i-create-a-bot) and obtain your bot token.

2.  **Installation:**

    ```bash
    pip install telebot schedule python-telegram-bot
    ```

3.  **Configuration:**

    *   Create a file named `config.py` and add your Telegram bot API token:

        ```python
        API_bot = "YOUR_TELEGRAM_BOT_API_TOKEN"
        ```

    *   Replace `"YOUR_TELEGRAM_BOT_API_TOKEN"` with your actual bot token.

4.  **Run the bot:**

    ```bash
    python logic.py
    ```

## Dependencies

*   `telebot`
*   `schedule`
*   `sqlite3`
*   `python-telegram-bot` (If not included with `telebot`)

## Database

The bot uses SQLite3 to store habit data in a file named `habits.db`.  The database schema is as follows:
