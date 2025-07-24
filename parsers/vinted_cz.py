from playwright.async_api import async_playwright
from utils import get_random_user_agent, load_seen_links, save_seen_links, get_rotated_proxy
import urllib.parse
import time
import logging
import os
import asyncio

SEEN_FILE = "parsers/vinted_cz_seen.json"
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("vinted")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    fh = logging.FileHandler(os.path.join(LOG_DIR, "vinted.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())


async def search_vinted(keyword: str):
    found_links = []
    encoded_keyword = urllib.parse.quote(keyword)
    current_timestamp = int(time.time())

    url = (
        f"https://www.vinted.cz/catalog?"
        f"search_text={encoded_keyword}&catalog[]=2312&page=1&time={current_timestamp}"
    )
    logger.info(f"🔍 Открываем Vinted: {url}")

    seen_links_raw = load_seen_links(SEEN_FILE)
    seen_links = set(link.strip().lower() for link in seen_links_raw)

    for attempt in range(3):
        try:
            async with async_playwright() as p:
                user_agent = get_random_user_agent()
                proxy = get_rotated_proxy(keyword)
                logger.info(f"🌐 Попытка {attempt+1}/3 | Прокси: {proxy['server']}")

                launch_args = {
                    "headless": True,
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage"
                    ]
                }
                if proxy:
                    launch_args["proxy"] = {
                        "server": proxy["server"],
                        "username": proxy["username"],
                        "password": proxy["password"]
                    }

                browser = await p.chromium.launch(**launch_args)
                context = await browser.new_context(user_agent=user_agent)
                page = await context.new_page()

                await page.goto(url, timeout=60000)
                await page.wait_for_load_state("domcontentloaded")
                await asyncio.sleep(3.5)

                items = await page.query_selector_all("div.new-item-box__image-container a[href*='/items/']")
                if not items:
                    logger.warning("⚠️ Карточки не найдены на странице.")
                    await browser.close()
                    continue

                logger.info(f"📦 Найдено карточек: {len(items)}")

                top_15_links = []
                for item in items:
                    if len(top_15_links) >= 15:
                        break
                    href = await item.get_attribute("href")
                    if href and "/items/" in href:
                        full_url = "https://www.vinted.cz" + href.strip() if href.startswith("/") else href.strip()
                        normalized = full_url.lower()
                        top_15_links.append(normalized)

                new_links = [link for link in top_15_links if link not in seen_links]

                if new_links:
                    logger.info(f"🚨 Новых ссылок среди первых 15: {len(new_links)}")
                    found_links = new_links

                if top_15_links:
                    seen_links.update(top_15_links)
                    save_seen_links(SEEN_FILE, seen_links)

                await browser.close()
                break

        except Exception as e:
            logger.warning(f"⚠️ Попытка {attempt+1}/3 завершилась ошибкой: {e}")
            if attempt == 2:
                logger.error("❌ Все попытки неудачны. Пропускаем.")
            await asyncio.sleep(3.0)

    logger.info(f"✅ [Vinted] По ключу '{keyword}' новых ссылок: {len(found_links)}")
    if found_links:
        logger.info(f"🧠 Последние новые: {found_links[-3:]}")
    return found_links
