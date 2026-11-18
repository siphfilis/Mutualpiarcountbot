import asyncio
import logging
import sqlite3
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

# Токен берется из защищенных переменных окружения Render
TOKEN = os.environ.get("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ----------------- КЛАВИАТУРЫ -----------------

# Главное меню
main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика каналов")],
        [KeyboardButton(text="❤️ Поддержка и реклама")],
        [KeyboardButton(text="💡 Помощь"), KeyboardButton(text="💡 Предложение")]
    ],
    resize_keyboard=True
)

# Функция для генерации списка каналов из базы данных
def get_channels_keyboard(channels_list):
    keyboard_builder = []
    row = []
    
    for chat_id, title in channels_list:
        row.append(KeyboardButton(text=f"📢 {title}"))
        if len(row) == 2:
            keyboard_builder.append(row)
            row = []
            
    if row:
        keyboard_builder.append(row)
        
    # Дополнительные служебные кнопки
    keyboard_builder.append([KeyboardButton(text="🔄 Обновить список")])
    keyboard_builder.append([KeyboardButton(text="🔙 Меню")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard_builder, resize_keyboard=True)


# ----------------- БАЗА ДАННЫХ -----------------

def init_db():
    conn = sqlite3.connect("bot_stats.db")
    cursor = conn.cursor()
    
    # Таблица для хранения каналов, куда добавлен бот
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            chat_id INTEGER PRIMARY KEY,
            title TEXT
        )
    """)
    
    # Таблица для статистики пересылки постов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts_stats (
            chat_id INTEGER,
            author_name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def save_channel_to_db(chat_id: int, title: str):
    conn = sqlite3.connect("bot_stats.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO channels (chat_id, title) VALUES (?, ?)", (chat_id, title))
    conn.commit()
    conn.close()

def save_post_to_db(chat_id: int, author_name: str):
    conn = sqlite3.connect("bot_stats.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO posts_stats (chat_id, author_name) VALUES (?, ?)", (chat_id, author_name))
    conn.commit()
    conn.close()

def get_user_channels():
    conn = sqlite3.connect("bot_stats.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id, title FROM channels")
    channels = cursor.fetchall()
    conn.close()
    return channels


# ----------------- ОБРАБОТЧИК СОБЫТИЙ В КАНАЛЕ -----------------

@dp.channel_post()
async def track_channel_posts(post: Message):
    """
    Автоматически ловит новые посты в каналах, куда добавлен бот.
    """
    chat_id = post.chat.id
    chat_title = post.chat.title or "Без названия"
    
    # Сохраняем канал в базу при любой публикации
    save_channel_to_db(chat_id, chat_title)
    
    # Определяем автора по подписи
    if post.author_signature:
        author_name = post.author_signature
    else:
        author_name = "От лица канала"
        
    # Сохраняем статистику поста
    save_post_to_db(chat_id, author_name)


# ----------------- ОБРАБОТЧИК СООБЩЕНИЙ В ЛИЧКЕ БОТА -----------------

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    if message.chat.type != "private":
        return

    welcome_text = (
        "🔥 Привет! Я считаю, сколько постов опубликовал каждый админ твоих каналов.\n\n"
        "<b>Как подключить канал:</b>\n"
        "• Добавь меня в канал администратором.\n"
        "• Включи в канале «Подписывать сообщения» — иначе я не вижу автора!\n"
        "• Всё — новые посты считаются сами.\n\n"
        "<i>Считаются только посты, опубликованные после добавления бота. Посты без подписи идут как «От лица канала».</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML", reply_markup=main_menu_keyboard)

@dp.message(F.text == "📊 Статистика каналов")
async def show_channels_menu(message: Message):
    if message.chat.type != "private":
        return

    channels = get_user_channels()

    if not channels:
        await message.answer(
            "📭 У меня пока нет данных ни по одному каналу.\n\n"
            "Убедитесь, что вы добавили меня в канал администратором и там появились новые посты.",
            reply_markup=main_menu_keyboard
        )
        return

    keyboard = get_channels_keyboard(channels)
    await message.answer(
        f"<b>Выбери канал:</b>\nДоступно каналов: {len(channels)}",
        parse_mode="HTML",
        reply_markup=keyboard
    )

@dp.message(F.text == "❤️ Поддержка и реклама")
async def show_support(message: Message):
    if message.chat.type != "private":
        return

    support_text = (
        "❤️ Я рад, что вы хотите поддержать проект!\n\n"
        "В качестве поддержки, вы можете отправить любое количество звезд данному человеку: @Yugo_Kanno"
    )
    await message.answer(support_text, reply_markup=main_menu_keyboard)

@dp.message(F.text == "💡 Помощь")
async def show_help(message: Message):
    await message.answer("По всем вопросам обращайтесь к разработчику: @Yugo_Kanno", reply_markup=main_menu_keyboard)

@dp.message(F.text == "💡 Предложение")
async def show_suggestion(message: Message):
    await message.answer("Вы можете написать свои идеи и предложения разработчику: @Yugo_Kanno", reply_markup=main_menu_keyboard)

@dp.message(F.text == "🔙 Меню")
async def back_to_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard)

@dp.message(F.text == "🔄 Обновить список")
async def refresh_channels(message: Message):
    await show_channels_menu(message)

# Обработка нажатия на конкретный канал из списка
@dp.message(F.text.startswith("📢 "))
async def show_channel_stats(message: Message):
    if message.chat.type != "private":
        return

    channel_title = message.text.replace("📢 ", "").strip()

    # Здесь бот может выводить статистику по выбранному каналу
    await message.answer(
        f"📊 <b>Статистика для канала:</b> <b>{channel_title}</b>\n\n"
        f"<i>(Здесь будет детальная статистика за неделю/месяц и кнопки выбора периодов)</i>",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard
    )


# ----------------- ЗАПУСК БОТА -----------------

async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
