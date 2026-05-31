import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, CallbackQuery
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
CHANNEL_URL = "https://t.me/repetitor_inf100" # Ваш канал

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Клавиатура с кнопкой "Начать" (Reply Keyboard)
# Важно: текст должен совпадать ТОЧНО с тем, что видит пользователь
start_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚀 Начать")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Выберите действие 👇"
)

@dp.startup()
async def set_webhook_on_start(bot: Bot):
    if WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL, allowed_updates=dp.resolve_used_update_types())
        logger.info(f"✅ Webhook установлен на {WEBHOOK_URL}")
    else:
        logger.warning("⚠️ WEBHOOK_URL не указан.")

@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Inline-кнопки
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Получить чек-лист и форму", callback_data="get_checklist")],
        [InlineKeyboardButton(text="📢 Канал с материалами", url=CHANNEL_URL)]
    ])
    
    user_name = message.from_user.full_name or "пользователь"
    text = (
        f"Привет, {user_name}! 👋\n"
        "Я бот-помощник репетитора по информатике.\n"
        " Нажми кнопку ниже, чтобы получить чек-лист 'Топ-5 ошибок в Задаче 8' и пройти диагностику."
    )
    
    await message.answer(text, reply_markup=start_keyboard)
    await message.answer("Выберите действие:", reply_markup=inline_kb)
    
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
            logger.error(f"Ошибка уведомления админу: {e}")

# Обработчик нажатия на кнопку "Получить чек-лист"
@dp.callback_query(lambda c: c.data == "get_checklist")
async def send_checklist_and_form(callback: CallbackQuery):
    image_path = "8.png" 
    
    try:
        # Проверяем существование файла перед отправкой
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Файл {image_path} не найден в директории {os.getcwd()}")

        with open(image_path, "rb") as photo:
            await callback.message.answer_photo(
                photo=photo,
                caption=(
                    "📸 Вот превью чек-листа «Топ-5 ошибок в Задаче 8»!\n\n"
                    "Чтобы получить полный PDF-разбор и записаться на бесплатную диагностику, "
                    "перейди по кнопке ниже 👇"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=" Открыть форму диагностики", url=FORM_URL)]
                ])
            )
        
        # Убираем "часики" загрузки на кнопке
        await callback.answer() 
        
    except FileNotFoundError as e:
        logger.error(str(e))
        await callback.message.answer("❌ Извините, картинка временно недоступна (ошибка сервера). Но вы можете заполнить форму:")
        await callback.message.answer("📝 Форма диагностики", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Заполнить форму", url=FORM_URL)]
        ]))
        await callback.answer()
    except Exception as e:
        logger.error(f"Неизвестная ошибка при отправке фото: {e}")
        await callback.answer("Произошла ошибка. Попробуйте позже.", show_alert=True)

# Обработчик нажатия на кнопку "🚀 Начать"
@dp.message(lambda msg: msg.text == " Начать")
async def handle_start_button(message: Message):
    await cmd_start(message)

# Обработчик всех остальных сообщений (fallback)
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
