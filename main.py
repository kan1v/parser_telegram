import asyncio
import random
import logging
import os

from utils import load_keywords, load_seen_links, save_seen_links
from config import KEYWORDS_FILE, SEEN_LINKS_FILE
from parsers.bazos_cz import search_bazos
from parsers.vinted_cz import search_vinted
from parsers.sbazar_cz import search_sbazar
from parsers.aukro_cz import search_aukro
from telegram_bot import send_to_telegram, run_bot  # run_bot должен быть функцией, которая запускает start_polling

MAX_CONCURRENT_TASKS = 20
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("main")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    fh = logging.FileHandler(os.path.join(LOG_DIR, "main.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())

seen_links_store = {}
last_id_store = {}

PARSERS = {
    "bazos": search_bazos,
    "vinted": search_vinted,
    "sbazar": search_sbazar,
    "aukro": search_aukro,
}

MAX_LINKS_PER_MESSAGE = 30


async def send_links_separately(links: list[str], site: str, keyword: str):
    for link in links:
        message = f"🔍 <b>{site.upper()}</b> | <b>{keyword}</b>\n{link}"
        try:
            await send_to_telegram(message)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram: {e}")


def normalize_link(link: str) -> str:
    return link.strip().lower()


async def process_keyword(site: str, keyword: str, func):
    try:
        async with semaphore:
            seen_links = seen_links_store.get(site, set())
            last_id = last_id_store.get(site)

            links = await func(keyword)
            normalized_links = [normalize_link(link) for link in links]
            normalized_seen = set(normalize_link(link) for link in seen_links)

            new_links = [link for link in normalized_links if link not in normalized_seen]

            logger.info(f"[{site}] По ключу '{keyword}': всего ссылок с сайта: {len(links)}")
            logger.info(f"[{site}] Уже просмотрено: {len(seen_links)}")
            logger.info(f"[{site}] Новых ссылок: {len(new_links)}")

            if new_links:
                await send_links_separately(new_links, site, keyword)
                logger.info(f"✅ Отправлено {len(new_links)} новых ссылок по ключу '{keyword}' ({site})")

                seen_links.update(new_links)
                last_id = new_links[-1]

                save_seen_links(SEEN_LINKS_FILE[site], seen_links, last_id)
                seen_links_store[site] = seen_links
                last_id_store[site] = last_id
            else:
                logger.info(f"ℹ️ По ключу '{keyword}' на сайте '{site}' новых ссылок нет.")

    except Exception as e:
        logger.error(f"❌ Ошибка при обработке ключа '{keyword}' на {site}: {e}")


async def start_parsers_loop():
    while True:
        await start_parsers()
        logger.info("⏰ Ожидаем 60 секунд перед следующим запуском...")
        await asyncio.sleep(60)


async def start_parsers():
    global seen_links_store, last_id_store

    logger.info("🚀 Запуск парсеров...")

    keywords = load_keywords(KEYWORDS_FILE)
    tasks = []

    for site, search_func in PARSERS.items():
        seen_links, last_id = load_seen_links(SEEN_LINKS_FILE[site])
        seen_links_store[site] = seen_links
        last_id_store[site] = last_id

        for keyword in keywords:
            logger.info(f"🔄 Обработка: {site} | Ключ: '{keyword}'")
            tasks.append(asyncio.create_task(process_keyword(site, keyword, search_func)))

    await asyncio.gather(*tasks)


async def main():
    await asyncio.gather(
        start_parsers_loop(),  # запускаем парсеры в цикле
        run_bot(),             # запускаем бота отдельно
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Программа остановлена вручную")
