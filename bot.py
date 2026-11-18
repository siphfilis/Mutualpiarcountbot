import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# Вставь сюда токен своего бота
TOKEN = "YOUR_BOT_TOKEN_HERE"

router = Router()
db_connection = sqlite3.connect("bot_stats.db", check_same_thread=False)
cursor = db_connection.cursor()

# Инициализация базы данных
cursor.execute(
    """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    chat_title TEXT,
    author_name TEXT,
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""
)
db_connection.commit()


# --- ХРАНИЛИЩЕ / КЛАВИАТУРЫ ---


def get_main_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="📊 Статистика каналов", callback_data="channels_list"
              )
          ],
          [
              InlineKeyboardButton(
                  text="⭐ Поддержать разработку", callback_data="support"
              )
          ],
      ]
  )


def get_periods_keyboard(chat_id: int):
  return InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text="День", callback_data=f"stat_{chat_id}_day"
              ),
              InlineKeyboardButton(
                  text="Неделя", callback_data=f"stat_{chat_id}_week"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="Месяц", callback_data=f"stat_{chat_id}_month"
              ),
              InlineKeyboardButton(
                  text="Всё время", callback_data=f"stat_{chat_id}_all"
              ),
          ],
          [
              InlineKeyboardButton(
                  text="« Назад к каналам", callback_data="channels_list"
              )
          ],
      ]
  )


# --- ХОНДЛЕРЫ (ОБРАБОТЧИКИ) ---


@router.message(CommandStart())
async def cmd_start(message: Message):
  text = (
      "Данный бот создан для подсчета вп в каналах.\n"
      "«(ЦИТИРОВАНИЕ) own - штурвал»\n\n"
      "Чтобы я мог считать посты, сделай следующее:\n"
      "1. Добавь бота в администраторы канала\n"
      '2. Включи в канале "подписывать сообщения", иначе я не вижу авторов\n'
      "3. Всё!! Новые посты будут считаться сами.\n\n"
      "«(ЦИТИРОВАНИЕ) считаются только те посты, которые отправлены после"
      " добавления бота как администратора.»"
  )
  await message.answer(text, reply_markup=get_main_keyboard())


@router.callback_query(F.data == "support")
async def process_support(callback: CallbackQuery):
  text = (
      "Я рада, что вы хотите поддержать проект!! В качестве поддержки, вы"
      " можете отправить любое количество звезд данному человеку: @Yugo_Kanno"
  )
  await callback.message.edit_text(text, reply_markup=get_main_keyboard())
  await callback.answer()


@router.callback_query(F.data == "channels_list")
async def process_channels_list(callback: CallbackQuery):
  user_id = callback.from_user.id
  bot_obj = callback.bot

  # В реальном приложении здесь лучше хранить привязку каналов к пользователю в БД,
  # но для примера пройдемся по сохраненным в базе уникальным каналам, где бот админ.
  cursor.execute(
      "SELECT DISTINCT chat_id, chat_title FROM posts"
  )  # Упрощенный вариант для демонстрации
  channels = cursor.fetchall()

  keyboard_buttons = []

  for chat_id, chat_title in channels:
    try:
      # Проверяем, является ли пользователь админом в этом канале
      member = await bot_obj.get_chat_member(chat_id, user_id)
      if member.status in [
          ChatMemberStatus.ADMINISTRATOR,
          ChatMemberStatus.CREATOR,
      ]:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=chat_title, callback_data=f"channel_{chat_id}"
            )
        ])
    except Exception:
      pass

  keyboard_buttons.append(
      [InlineKeyboardButton(text="« Главное меню", callback_data="main_menu")]
  )

  if not keyboard_buttons or len(keyboard_buttons) == 1:
    text = (
        "У тебя пока нет каналов, где мы вместе с тобой являемся"
        " администраторами, или бот еще не зафиксировал посты."
    )
  else:
    text = "Выбери канал для просмотра статистики:"

  await callback.message.edit_text(
      text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
  )
  await callback.answer()


@router.callback_query(F.data == "main_menu")
async def process_main_menu(callback: CallbackQuery):
  text = "Главное меню:"
  await callback.message.edit_text(text, reply_markup=get_main_keyboard())
  await callback.answer()


@router.callback_query(F.data.startswith("channel_"))
async def process_channel_selected(callback: CallbackQuery):
  chat_id = int(callback.data.split("_")[1])

  # По умолчанию при клике показываем статистику за неделю (как вы и хотели)
  await show_statistics(callback, chat_id, period="week")


@router.callback_query(F.data.startswith("stat_"))
async def process_period_selected(callback: CallbackQuery):
  parts = callback.data.split("_")
  chat_id = int(parts[1])
  period = parts[2]

  await show_statistics(callback, chat_id, period=period)


async def show_statistics(callback: CallbackQuery, chat_id: int, period: str):
  # Выбираем интервал времени для SQL
  time_filter = ""
  period_name = "за всё время"

  if period == "day":
    time_filter = "AND date >= datetime('now', '-1 day')"
    period_name = "за день"
  elif period == "week":
    time_filter = "AND date >= datetime('now', '-7 days')"
    period_name = "за неделю"
  elif period == "month":
    time_filter = "AND date >= datetime('now', '-30 days')"
    period_name = "за месяц"

  cursor.execute(
      f"SELECT chat_title FROM posts WHERE chat_id = ? LIMIT 1", (chat_id,)
  )
  res = cursor.fetchone()
  chat_title = res[0] if res else "Канал"

  # Считаем посты по авторам за выбранный период
  cursor.execute(
      f"""
        SELECT author_name, COUNT(*) as cnt 
        FROM posts 
        WHERE chat_id = ? {time_filter} 
        GROUP BY author_name
    """,
      (chat_id,),
  )
  stats = cursor.fetchall()

  stats_text = f"Статистика для канала: {chat_title} ({period_name})\n\n"
  if not stats:
    stats_text += "• Пока нет записей за этот период."
  else:
    for author, count in stats:
      stats_text += f"• {author}: {count} пост{get_post_word(count)}\n"

  await callback.message.edit_text(
      stats_text, reply_markup=get_periods_keyboard(chat_id)
  )
  await callback.answer()


def get_post_word(count: int) -> str:
  # Функция для правильного склонения слова "пост"
  if count % 10 == 1 and count % 100 != 11:
    return ""
  elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
    return "а"
  else:
    return "ов"


# Логика сбора постов из каналов
@router.channel_post()
async def collect_channel_posts(message: Message):
  if message.chat.type in [ChatType.CHANNEL, ChatType.SUPERGROUP]:
    # Проверяем наличие подписи автора (авторство)
    if message.author_signature:
      chat_id = message.chat.id
      chat_title = message.chat.title or "Без названия"
      author_name = message.author_signature

      # Сохраняем в базу данных
      cursor.execute(
          "INSERT INTO posts (chat_id, chat_title, author_name) VALUES (?, ?,"
          " ?)",
          (chat_id, chat_title, author_name),
      )
      db_connection.commit()


async def main():
  logging.basicConfig(level=logging.INFO)
  bot = Bot(token=TOKEN)
  dp = Dispatcher(storage=MemoryStorage())
  dp.include_router(router)

  print("Бот запущен!")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
