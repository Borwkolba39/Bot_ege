import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
from aiogram.types.input_file import FSInputFile  # <--- ВАЖНО: Добавлен импорт
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
import asyncio
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
FORM_URL = os.getenv("FORM_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 8000))
CHANNEL_URL = "https://t.me/repetitor_inf100"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Клавиатура "Начать"
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Начать")]  # Текст должен совпадать точно
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Выберите действие "
)

@dp.startup()
async def set_webhook_on_start(bot: Bot):
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
        logger.info(f"✅ Webhook установлен на {WEBHOOK_URL}")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Получить чек-лист и форму", callback_data="get_checklist")],
        [InlineKeyboardButton(text=" Канал с материалами", url=CHANNEL_URL)]
    ])
    
    user_name = message.from_user.full_name or "пользователь"
    text = (
        f"Привет, {user_name}! 👋\n"
        "Я бот-помощник репетитора по информатике.\n"
        "Нажми кнопку ниже, чтобы получить чек-лист 'Топ-5 ошибок в Задаче 8' и пройти диагностику."
    )
    
    await message.answer(text, reply_markup=start_keyboard)
    await message.answer("Выберите действие:", reply_markup=inline_kb)
    
    if ADMIN_ID:
        username = f"@{message.from_user.username}" if message.from_user.username else "без username"
        try:
            await bot.send_message(
                ADMIN_ID,
                f"🆕 Новый пользователь: {user_name} ({username})\nID: <code>{message.from_user.id}</code>",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления админу: {e}")

@dp.callback_query(lambda c: c.data == "get_checklist")
async def send_checklist_and_form(callback: CallbackQuery):
    image_path = "8.png"
    
    try:
        # Используем FSInputFile для корректной работы в aiogram 3.x
        photo = FSInputFile(image_path)
        
        await callback.message.answer_photo(
            photo=photo,
            caption=(
                "📸 Вот превью чек-листа «Топ-5 ошибок в Задаче 8»!\n\n"
                "Чтобы получить полный PDF-разбор и записаться на бесплатную диагностику, "
                "перейди по кнопке ниже 👇"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📝 Открыть форму диагностики", url=FORM_URL)]
            ])
        )
        await callback.answer() 
        
    except FileNotFoundError:
        logger.error(f"Файл {image_path} не найден!")
        await callback.message.answer(" Картинка временно недоступна. Но вы можете заполнить форму:")
        await callback.message.answer("📝 Форма диагностики", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Заполнить форму", url=FORM_URL)]
        ]))
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)

@dp.message(lambda msg: msg.text == "🚀 Начать")
async def handle_start_button(message: Message):
    await cmd_start(message)

@dp.message(~Command("start"))
async def fallback(message: Message):
    await message.answer("Используйте команду /start или кнопку 🚀 Начать.", reply_markup=start_keyboard)

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
        logger.info("🛑 Остановка...")
    finally:
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
