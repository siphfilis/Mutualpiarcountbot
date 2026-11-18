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

TOKEN = os.environ.get("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ----------------- КЛАВИАТУРЫ -----------------

main_menu_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика каналов")],
        [KeyboardButton(text="❤️ Поддержка и реклама")],
        [KeyboardButton(text="💡 Помощь"), KeyboardButton(text="💡 Предложение")]
    ],
    resize_keyboard=True
)

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
        
    keyboard_builder.append([KeyboardButton(text="🔄 Обновить список")])
    keyboard_builder.append([KeyboardButton(text="🔙 Меню")])
    
    return ReplyKeyboardMarkup(keyboard=keyboard_builder, resize_keyboard=True)


# ----------------- БАЗА ДАННЫХ -----------------

def init_db():
    conn = sqlite3.connect("bot_stats.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            chat_id INTEGER PRIMARY KEY,
            title TEXT
        )
    """)
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

def get_channel_stats(chat_id: int):
    conn = sqlite3.connect("bot_stats.db")
    cursor = conn.cursor()
    cursor.execute("SELECT author_name, COUNT(*) FROM posts_stats WHERE chat_id = ? GROUP BY author_name", (chat_id,))
    stats = cursor.fetchall()
    conn.close()
    return stats


# ----------------- ОБРАБОТЧИК СОБЫТИЙ В КАНАЛЕ -----------------

@dp.channel_post()
async def track_channel_posts(post: Message):
    chat_id = post.chat.id
    chat_title = post.chat.title or "Без названия"
    
    save_channel_to_db(chat_id, chat_title)
    
    if post.author_signature:
        author_name = post.author_signature
    else:
        author_name = "От лица канала"
        
    save_post_to_db(chat_id, author_name)


# ----------------- ОБРАБОТЧИК СООБЩЕНИЙ В ЛИЧКЕ БОТА -----------------

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    if message.chat.type != "private":
        return

    welcome_text = (
        "Я считаю, сколько постов опубликовал каждый админ твоих каналов.\n"
        "Как подключить канал:\n"
        "1. Добавь меня в канал администратором\n"
        "2. Включи в канале «Подписывать сообщения» - иначе я не вижу автора\n"
        "• Все - новые посты считаются сами\n\n"
        "Считаются только посты, опубликованные после добавления бота. Посты без подписи идут как \"От лица канала\"\n\n"
        "Бот делается одним человеком с помощью ии, я вообще нихуя не разбираюсь в кодах, но у меня нет возможности платить людям за разработку и помощь😭. Так что некоторое время бот будет сырым, если я вообще не забью хуй на его разработку.\n\n"
        "OWNER - штурвал"
    )
    await message.answer(welcome_text, reply_markup=main_menu_keyboard)

@dp.message(F.text == "📊 Статистика каналов")
async def show_channels_menu(message: Message):
    if message.chat.type != "private":
        return

    channels = get_user_channels()

    if not channels:
        await message.answer(
            "...у меня пока нет данных ни по одному каналу.\n"
            "Убедитесь, что вы добавили бота в канал, выдали ему права администратора и в нем появились новые посты.",
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
        "В качестве поддержки, вы можете отправить любое количество звезд данному человеку: @Yugo_Kanno\n"
        "Все отправленные звезды идут на поддержку бота!"
    )
    await message.answer(support_text, reply_markup=main_menu_keyboard)

@dp.message(F.text == "💡 Помощь")
async def show_help(message: Message):
    help_text = (
        "Появились вопросы? Вы можете задать их @Yugo_Kanno, или написать в анонимные сообщения: "
        "http://t.me/anonaskbot?start=DEeCvyqIwnnLdNB"
    )
    await message.answer(help_text, reply_markup=main_menu_keyboard)

@dp.message(F.text == "💡 Предложение")
async def show_suggestion(message: Message):
    suggestion_text = (
        "Появились вопросы? Вы можете задать их @Yugo_Kanno, или написать в анонимные сообщения: "
        "http://t.me/anonaskbot?start=DEeCvyqIwnnLdNB"
    )
    await message.answer(suggestion_text, reply_markup=main_menu_keyboard)

@dp.message(F.text == "🔙 Меню")
async def back_to_menu(message: Message):
    await message.answer("Главное меню:", reply_markup=main_menu_keyboard)

@dp.message(F.text == "🔄 Обновить список")
async def refresh_channels(message: Message):
    await show_channels_menu(message)

@dp.message(F.text.startswith("📢 "))
async def show_channel_stats(message: Message):
    if message.chat.type != "private":
        return

    channel_title = message.text.replace("📢 ", "").strip()

    conn = sqlite3.connect("bot_stats.db")
    cursor = conn.cursor()
    cursor.execute("SELECT chat_id FROM channels WHERE title = ?", (channel_title,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        await message.answer("Не удалось найти данные по этому каналу в базе.", reply_markup=main_menu_keyboard)
        return

    chat_id = row[0]
    stats = get_channel_stats(chat_id)

    stats_text = ""
    if not stats:
        stats_text = "📭 В этом канале пока не зафиксировано постов после подключения бота."
    else:
        for author, count in stats:
            stats_text += f"• <b>{author}</b>: {count} пост(ов)\n"

    await message.answer(
        f"📊 <b>Статистика для канала:</b> <b>{channel_title}</b>\n\n"
        f"{stats_text}",
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
