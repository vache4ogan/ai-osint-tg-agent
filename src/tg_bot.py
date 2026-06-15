import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
import feedparser

from src.config import BOT_TOKEN, ADMIN_ID, CHANNEL_ID
# Импортируем наш собранный граф и функцию парсера
from agents.graph import app

from src.chanking import update_knowledge_base
from typing import Any
# ==========================================
# НАСТРОЙКИ БОТА
# ==========================================
BOT_TOKEN = BOT_TOKEN
ADMIN_ID = ADMIN_ID
CHANNEL_ID = CHANNEL_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ==========================================
# КЭШ (Хранилище состояний)
# ==========================================
recent_topics_cache = {} # Хранит названия тем: { "topic_0": "Название статьи" }
drafts_cache = {}        # Хранит готовые тексты перед публикацией: { "topic_0": "Текст поста..." }

# ==========================================
# ХЭНДЛЕРЫ БАЗОВЫХ КОМАНД
# ==========================================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id != ADMIN_ID: return
    await message.answer(
        "Привет, босс! 🦾\n\n"
        "1️⃣ `/update` — скачать новые статьи в базу (ChromaDB)\n"
        "2️⃣ `/topics` — выбрать тему для публикации в канал"
    )

@dp.message(Command("update"))
async def cmd_update(message: Message):
    if message.from_user.id != ADMIN_ID: return
    
    await message.answer("🔄 Запускаю парсер. Обновляю базу знаний...")
    await asyncio.to_thread(update_knowledge_base)
    await message.answer("✅ База обновлена! Жми /topics, чтобы выбрать тему.")

@dp.message(Command("topics"))
async def cmd_topics(message: Message):
    if message.from_user.id != ADMIN_ID: return
    
    rss_url = "https://habr.com/ru/rss/hub/machine_learning/all/"
    feed = await asyncio.to_thread(feedparser.parse, rss_url)
    
    builder = InlineKeyboardBuilder()
    recent_topics_cache.clear() 
    
    for i, raw_entry in enumerate(feed.entries[:5]):
        # Явно говорим анализатору: "Считай это любым объектом, у него точно есть .title"
        entry: Any = raw_entry 
        
        topic_id = f"topic_{i}"
        recent_topics_cache[topic_id] = entry.title
        builder.button(text=entry.title, callback_data=topic_id)
        
    builder.adjust(1) 
    await message.answer("📰 Выбери тему для генерации черновика:", reply_markup=builder.as_markup())

# ==========================================
# ЛОГИКА ГЕНЕРАЦИИ И HUMAN-IN-THE-LOOP
# ==========================================

# 1. Запуск генерации после выбора темы
@dp.callback_query(F.data.startswith("topic_"))
async def process_topic_selection(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID: return
    
    topic_id = callback_query.data
    topic_title = recent_topics_cache.get(topic_id)
    
    if not topic_title:
        await callback_query.answer("Тема устарела, вызови /topics еще раз.", show_alert=True)
        return

    await callback_query.answer()
    status_msg = await callback_query.message.answer(
        f"⏳ Агенты пошли писать пост на тему:\n*{topic_title}*\n\nЭто займет пару минут...", 
        parse_mode="Markdown"
    )
    
    await generate_and_review(topic_id, topic_title, status_msg)

# Вспомогательная функция для генерации (чтобы можно было вызывать повторно)
async def generate_and_review(topic_id: str, topic_title: str, message: Message):
    try:
        # Запускаем LangGraph
        initial_state = {"topic": topic_title}
        final_state = await asyncio.to_thread(app.invoke, initial_state)
        draft = final_state["draft"]
        
        # Сохраняем черновик в кэш
        final_text = draft + "\n\n Всем бр бр патапим !"
        drafts_cache[topic_id] = final_text
        
        # Создаем клавиатуру модерации (Human-in-the-loop)
        builder = InlineKeyboardBuilder()
        builder.button(text="🟢 Опубликовать", callback_data=f"pub_{topic_id}")
        builder.button(text="🔄 Перегенерировать", callback_data=f"reg_{topic_id}")
        builder.button(text="❌ Отменить", callback_data=f"can_{topic_id}")
        builder.adjust(1)
        
        # Отправляем черновик на проверку
        await message.edit_text(
            f"📝 **ЧЕРНОВИК ГОТОВ**\n*Тема:* {topic_title}\n\n{final_text}",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        await message.edit_text(f"❌ Ошибка генерации агентами: {e}")

# ==========================================
# ХЭНДЛЕРЫ МОДЕРАЦИИ (Кнопки под черновиком)
# ==========================================

# 🟢 ОПУБЛИКОВАТЬ
@dp.callback_query(F.data.startswith("pub_"))
async def action_publish(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID: return
    
    topic_id = callback_query.data.replace("pub_", "")
    draft = drafts_cache.get(topic_id)
    
    if not draft:
        await callback_query.answer("Черновик не найден. Начни заново /topics.", show_alert=True)
        return

    # Отправляем в публичный канал
    await bot.send_message(chat_id=CHANNEL_ID, text=draft)
    
    # Меняем сообщение в личке админа
    await callback_query.message.edit_text(f"✅ Успешно опубликовано в канал!\n\n{draft}")
    await callback_query.answer()

# 🔄 ПЕРЕГЕНЕРИРОВАТЬ
@dp.callback_query(F.data.startswith("reg_"))
async def action_regenerate(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID: return
    
    topic_id = callback_query.data.replace("reg_", "")
    topic_title = recent_topics_cache.get(topic_id)
    
    if not topic_title:
        await callback_query.answer("Тема устарела.", show_alert=True)
        return

    await callback_query.message.edit_text(f"🔄 Агенты переписывают пост:\n*{topic_title}*...", parse_mode="Markdown")
    await callback_query.answer()
    
    # Запускаем генерацию заново
    await generate_and_review(topic_id, topic_title, callback_query.message)

# ❌ ОТМЕНИТЬ
@dp.callback_query(F.data.startswith("can_"))
async def action_cancel(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID: return
    
    topic_id = callback_query.data.replace("can_", "")
    topic_title = recent_topics_cache.get(topic_id, "Неизвестная тема")
    
    # Очищаем кэш черновика
    drafts_cache.pop(topic_id, None)
    
    await callback_query.message.edit_text(f"❌ Публикация отменена.\nТема: {topic_title}")
    await callback_query.answer()

# ==========================================
# ЗАПУСК
# ==========================================
async def main():
    print("🤖 Бот запущен! Жду команд...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())