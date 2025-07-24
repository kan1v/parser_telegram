import asyncio
import logging
import os
import random

from utils import (
    load_keywords,
    load_seen_links,
    save_seen_links,
    normalize_link,
)
from config import KEYWORDS_FILE, SEEN_LINKS_FILE
from parsers.bazos_cz import search_bazos
from parsers.vinted_cz import search_vinted
from parsers.sbazar_cz import search_sbazar
from parsers.aukro_cz import search_aukro
from telegram_bot import send_to_telegram, run_bot, stop_parsing

# 👇 Семафоры по сайтам
SEMAPHORES = {
    "aukro": asyncio.Semaphore(7),
    "bazos": asyncio.Semaphore(5),
    "sbazar": asyncio.Semaphore(7),
    "vinted": asyncio.Semaphore(7),
}

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("main")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    fh = logging.FileHandler(os.path.join(LOG_DIR, "main.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())

# Хранилище просмотренных ссылок
seen_links_store: dict[str, set[str]] = {}

# Карта парсеров
PARSERS = {
    "bazos": search_bazos,
    "vinted": search_vinted,
    "sbazar": search_sbazar,
    "aukro": search_aukro,
}


async def send_links_separately(links: list[str], site: str, keyword: str):
    for link in links:
        message = f"🔍 <b>{site.upper()}</b> | <b>{keyword}</b>\n{link}"
        try:
            await send_to_telegram(message)
        except Exception as e:
            logger.error(f"❌ Ошибка отправки в Telegram: {e}")


async def process_keyword(site: str, keyword: str, func, sema: asyncio.Semaphore):
    try:
        if stop_parsing:
            logger.warning(f"[{site}] Пропущен ключ '{keyword}' из-за замены keywords.txt")
            return

        async with sema:
            await asyncio.sleep(random.uniform(1.2, 2.8))  # ⏱️ антиспам-задержка

            seen_links = seen_links_store.get(site, set())
            links = await func(keyword)
            normalized_links = [normalize_link(link) for link in links]

            new_links = [link for link in normalized_links if link not in seen_links]

            logger.info(f"[{site}] По ключу '{keyword}': всего ссылок: {len(links)}")
            logger.info(f"[{site}] Уже просмотрено: {len(seen_links)}")
            logger.info(f"[{site}] Новых ссылок: {len(new_links)}")

            if new_links:
                await send_links_separately(new_links, site, keyword)
                logger.info(f"✅ Отправлено {len(new_links)} новых ссылок по ключу '{keyword}' ({site})")
                seen_links.update(new_links)
                save_seen_links(SEEN_LINKS_FILE[site], seen_links)

            # Обновляем хранилище в любом случае
            seen_links_store[site] = seen_links

    except Exception as e:
        logger.error(f"❌ Ошибка при обработке ключа '{keyword}' на {site}: {e}")


async def run_for_site(site, search_func):
    logger.info(f"▶️ Обработка сайта {site.upper()}")

    seen_links = load_seen_links(SEEN_LINKS_FILE[site])
    seen_links_store[site] = seen_links

    keywords = load_keywords(KEYWORDS_FILE)
    sema = SEMAPHORES[site]

    batch_size = 30
    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i + batch_size]
        logger.info(f"[{site}] 🔄 Обработка батча {i // batch_size + 1}/{(len(keywords)-1)//batch_size+1}")

        tasks = [
            asyncio.create_task(process_keyword(site, kw, search_func, sema))
            for kw in batch
        ]
        await asyncio.gather(*tasks)
        await asyncio.sleep(3)  # ⏸️ Пауза между батчами

    logger.info(f"[{site}] ✅ Завершена обработка {len(keywords)} ключей")


async def start_parsers():
    logger.info("🚀 Старт парсинга по всем сайтам")

    await asyncio.gather(*[
        run_for_site(site, func) for site, func in PARSERS.items()
    ])

    logger.info("📊 Парсинг завершён по всем сайтам.")


async def start_parsers_loop():
    while True:
        await start_parsers()
        logger.info("⏰ Ожидание 60 сек перед следующим циклом...")
        await asyncio.sleep(60)


async def main():
    await asyncio.gather(
        start_parsers_loop(),
        run_bot(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Программа остановлена вручную")
