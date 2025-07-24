import asyncio
import os 
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command, CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile


import logging

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

from inline_kbd import admin_choices

from user_control import set_user_status


bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Конфигурация логера 
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("tg_bot")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    fh = logging.FileHandler(os.path.join(LOG_DIR, "tg_bot.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())

# Временное хранилище статусов
user_message_status = {}

def set_user_status(user_id: int, status: bool):
    user_message_status[user_id] = status

def is_user_active(user_id: int) -> bool:
    return user_message_status.get(user_id, True)  # По умолчанию True

# ========= Отправка сообщений в чат =========
async def send_to_telegram(message: str, chat_id: int = TELEGRAM_CHAT_ID):
    if not is_user_active(chat_id):
        logger.info(f"ℹ️ Пользователь {chat_id} отключил сообщения, сообщение не отправлено")
        return
    try:
        await bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        logger.error(f"❌ Ошибка отправки: {e}")


# ========= Команды бота =========
@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer("👋 Привет! Я бот для уведомлений по ключевым словам.")

@dp.message(Command("id"))
async def id_cmd(message: Message):
    await message.answer(f"Ваш chat_id: <code>{message.chat.id}</code>", parse_mode="HTML")

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer("📌 Команды:\n/start — начать\n/id — узнать chat_id\n/help — помощь")

# Функция для открытия админ панели админу - по TELEGRAM_CHAT_ID
@dp.message(Command('admin'))
async def admin_cmd(message: types.Message):
    user_username = message.from_user.username
    if message.from_user.id == TELEGRAM_CHAT_ID:
        await message.answer(f'⭐ Адимн панель {user_username} ⭐ \n Поддержываемые сайты: \n 🌐 bazos.cz \n 🌐 sbazar.cz \n 🌐 aukro.cz \n 🌐 vinted.cz \n  ', reply_markup=admin_choices)
    else:
        await message.answer('У вас нет доступа к этой команде 🛑')

@dp.callback_query(lambda c: c.data == 'start_messages')
async def start_messages(callback: types.CallbackQuery):
    set_user_status(callback.from_user.id, True)
    await callback.answer("✅ Сообщения включены")
    logger.info("✅ Отправка сообщений включена в телеграмм бота")
    # Можно уведомить, что сейчас сообщения включены


@dp.callback_query(lambda c: c.data == 'stop_messages')
async def stop_messages(callback: types.CallbackQuery):
    set_user_status(callback.from_user.id, False)
    await callback.answer("⛔️ Сообщения выключены")
    logger.info("⛔️ Отправка сообщений в телеграмм бота выключена")
    # Можно уведомить, что сообщения отключены


# Функция для полуучения файла с ключевыми словами 
@dp.callback_query(lambda c: c.data.startswith('keywords_data'))
async def get_keywords_data(callback: types.CallbackQuery):
    file_path = "parsers/keywords.txt"  # путь к файлу

    try:
        document = FSInputFile(file_path, filename="keywords.txt")
        await bot.send_document(chat_id=callback.from_user.id, document=document)
        await callback.answer("📤 Файл отправлен", show_alert=True)
        logger.info("Файл с ключевыми словами был отправлен пользователю")
    except Exception as e:
        logger.error(f"❌ Ошибка при отправке файла: {e}")
        await callback.answer("❌ Не удалось отправить файл", show_alert=True)


# FSM-состояния
class AddKeywordState(StatesGroup):
    waiting_for_keyword = State()

# Обработка кнопки "Добавить слово"
@dp.callback_query(lambda c: c.data == 'add_one_keyword')
async def prompt_for_keyword(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Введите новое ключевое слово:")
    logger.info("Пользователь вводит ключевое слово для добавления в файл")
    await state.set_state(AddKeywordState.waiting_for_keyword)
    await callback.answer()

@dp.message(AddKeywordState.waiting_for_keyword)
async def save_new_keyword(message: types.Message, state: FSMContext):
    keyword = message.text.strip()

    if not keyword:
        await message.answer("❌ Ключевое слово не может быть пустым.")
        return

    file_path = "parsers/keywords.txt"
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            existing_keywords = [line.strip() for line in lines]
            logger.info("Попытка добавления ключевого слова")
    except FileNotFoundError as e:
        existing_keywords = []
        lines = []
        logger.error(f"Ошибка при добавление ключевого слова: {e}")

    if keyword in existing_keywords:
        await message.answer("⚠️ Это ключевое слово уже существует.")
    else:
        with open(file_path, "a", encoding="utf-8") as f:
            if lines and not lines[-1].endswith('\n'):
                f.write('\n')  # добавляем перенос строки, если последняя строка не заканчивается на \n
            f.write(f"{keyword}\n")
        await message.answer(f"✅ Ключевое слово <b>{keyword}</b> добавлено.")

    await state.clear()


# Путь к файлу ключевых слов
KEYWORDS_FILE_PATH = "parsers/keywords.txt"

# Флаг остановки парсинга
stop_parsing = False

class ImportKeywordState(StatesGroup):
    waiting_for_file = State()

@dp.callback_query(lambda c: c.data == 'import_keywords_data')
async def prompt_import_keywords(callback: types.CallbackQuery, state: FSMContext):
    global stop_parsing
    stop_parsing = True  # Остановить все рассылки
    await callback.message.answer("📎 Пожалуйста, отправьте .txt файл с ключевыми словами.")
    await state.set_state(ImportKeywordState.waiting_for_file)

@dp.message(ImportKeywordState.waiting_for_file)
async def handle_imported_file(message: types.Message, state: FSMContext):
    global stop_parsing
    document = message.document

    if not document or not document.file_name.endswith(".txt"):
        await message.answer("❌ Пожалуйста, отправьте .txt файл.")
        return

    os.makedirs("parsers", exist_ok=True)

    file = await message.bot.get_file(document.file_id)
    await message.bot.download_file(file.file_path, destination=KEYWORDS_FILE_PATH)

    await message.answer("✅ Файл успешно загружен и заменён.")
    stop_parsing = False  # Снова можно начинать парсинг
    await state.clear()



# ========= Запуск =========
async def run_bot():
    logger.info("✅ Telegram-бот запущен")
    await dp.start_polling(bot)


# ========= Возможность запуска как скрипт =========
if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Бот остановлен вручную")

