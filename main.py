import asyncio
import random

from utils import load_keywords, load_seen_links, save_seen_links
from config import KEYWORDS_FILE, SEEN_LINKS_FILE

from parsers.bazos_cz import search_bazos
from parsers.vinted_cz import search_vinted
from parsers.aukro_cz import search_aukro
from parsers.sbazar_cz import search_sbazar

from telegram_bot import send_to_telegram, dp, bot  # Импортируем объект dp и bot из telegram_bot.py

import logging
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Общая конфигурация логирования 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "main.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger("main")

# Словарь парсеров
PARSERS = {
    "bazos": search_bazos,
    "aukro": search_aukro,
    "vinted": search_vinted,
    "sbazar": search_sbazar,
}

seen_links_store = {}
last_id_store = {}

async def process_keyword(site: str, keyword: str, search_function):
    global seen_links_store, last_id_store

    while True:
        try:
            links = await search_function(keyword)
            seen_links = seen_links_store[site]
            last_id = last_id_store[site]

            new_links = [link for link in links if link not in seen_links.values()]

            for link in new_links:
                message = f"🔍 <b>{site.upper()}</b> | <b>{keyword}</b>\n{link}"
                await send_to_telegram(message)
                last_id += 1
                seen_links[last_id] = link

            last_id_store[site] = last_id

            if new_links:
                save_seen_links(SEEN_LINKS_FILE[site], seen_links)

            logger.info(f"[{site}][{keyword}] ✅ Отправлено {len(new_links)} новых ссылок")

        except Exception as e:
            logger.error(f"[{site}][{keyword}] ❌ Ошибка: {e}")

        delay = random.randint(50, 120)
        logger.info(f"[{site}][{keyword}] ⏳ Следующий запрос через {delay} сек.")
        await asyncio.sleep(delay)

async def start_parsers():
    global seen_links_store, last_id_store
    keywords = load_keywords(KEYWORDS_FILE)
    tasks = []

    for site, search_func in PARSERS.items():
        seen_links, last_id = load_seen_links(SEEN_LINKS_FILE[site])
        seen_links_store[site] = seen_links
        last_id_store[site] = last_id

        for keyword in keywords:
            tasks.append(asyncio.create_task(process_keyword(site, keyword, search_func)))

    # Запускаем все парсеры параллельно (не ждем окончания)
    await asyncio.gather(*tasks)

async def main():
    # Создаем задачу для парсеров (работают в фоне)
    parsers_task = asyncio.create_task(start_parsers())

    logger.info("✅ Запуск Telegram-бота...")
    # Запускаем бота с polling (он блокирует поток, поэтому запускаем вместе с парсерами)
    await dp.start_polling(bot)

    # Если бот завершится, отменяем парсеры
    parsers_task.cancel()
    try:
        await parsers_task
    except asyncio.CancelledError:
        logger.info("Парсеры были остановленны")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Программа остановлена вручную")

