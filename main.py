import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import asyncio
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
FORM_URL = os.getenv("FORM_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.startup()
async def set_webhook_on_start(bot: Bot):
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
        logger.info(f"✅ Webhook установлен на {WEBHOOK_URL}")
    else:
        logger.warning("⚠️ WEBHOOK_URL не указан. Webhook не будет установлен.")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Пройти диагностику", url=FORM_URL)],
        [InlineKeyboardButton(text="📢 Канал с материалами", url="https://t.me/EgeKABot")]
    ])
    
    user_name = message.from_user.full_name or "пользователь"
    text = (
        f"Привет, {user_name}! 👋\n"
        "Я бот-помощник репетитора по информатике.\n"
        "🎯 Бесплатная диагностика + подбор программы → жми кнопку ниже 👇"
    )
    await message.answer(text, reply_markup=kb)
    
    if ADMIN_ID:
        username = f"@{message.from_user.username}" if message.from_user.username else "без username"
        user_id = message.from_user.id
        admin_text = (
            f"🆕 Новый пользователь: {user_name} ({username})\n"
            f"ID: <code>{user_id}</code>"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления админу: {e}")

@dp.message(~Command("start"))
async def fallback(message: Message):
    await message.answer("Используйте команду /start для вызова главного меню.")

async def main():
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path="/webhook")
    setup_application(app, dp, bot=bot)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"🚀 Сервер запущен на порту {PORT}")
    
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки. Завершаем работу...")
    finally:
        await runner.cleanup()
        logger.info("✅ Сервер корректно остановлен.")

if __name__ == "__main__":
    asyncio.run(main())
