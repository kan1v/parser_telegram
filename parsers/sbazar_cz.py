from playwright.async_api import async_playwright
import urllib.parse
import asyncio
import os
import logging

from utils import get_random_user_agent, load_seen_links, save_seen_links, get_rotated_proxy

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
SEEN_FILE = "parsers/sbazar_cz_seen.json"

logger = logging.getLogger("sbazar")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.hasHandlers():
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    fh = logging.FileHandler(os.path.join(LOG_DIR, "sbazar.log"), encoding="utf-8")
    fh.setFormatter(formatter)
    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.addHandler(sh)


async def search_sbazar(keyword: str):
    encoded_keyword = urllib.parse.quote(keyword)
    base_url = f"https://www.sbazar.cz/hledej/{encoded_keyword}/31-knihy-literatura"
    logger.info(f"🔍 Открываем Sbazar: {base_url}")

    found_links = []
    seen_links_raw = load_seen_links(SEEN_FILE)
    seen_links = set(link.strip().lower() for link in seen_links_raw)

    async with async_playwright() as p:
        user_agent = get_random_user_agent()
        proxy = get_rotated_proxy(keyword)
        logger.info(f"🌐 Прокси: {proxy['server']}")

        launch_args = {"headless": True}
        if proxy:
            launch_args["proxy"] = {
                "server": proxy["server"],
                "username": proxy["username"],
                "password": proxy["password"]
            }

        browser = await p.chromium.launch(**launch_args)
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()

        try:
            await page.goto(base_url, timeout=50000)
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(2.0)

            try:
                await page.click("button:has-text('Souhlasím')", timeout=5000)
                logger.info("✅ Cookie popup закрыт")
                await asyncio.sleep(1.0)
            except:
                logger.info("ℹ️ Cookie popup не найден")

            await page.wait_for_selector('a[href*="/inzerat/"], a[href*="/rozbalena-nabidka/"]', timeout=15000)

            # Получаем первые 15 карточек
            elements = await page.query_selector_all('a[href*="/inzerat/"], a[href*="/rozbalena-nabidka/"]')
            collected = []

            for el in elements:
                if len(collected) >= 15:
                    break

                href = await el.get_attribute("href")
                if href:
                    full_url = f"https://www.sbazar.cz{href.strip()}" if href.startswith("/") else href.strip()
                    normalized = full_url.lower()
                    collected.append(normalized)

            # Проверяем, есть ли среди них новые
            new_links = [link for link in collected if link not in seen_links]

            if new_links:
                found_links = new_links
                seen_links.update(new_links)
                save_seen_links(SEEN_FILE, seen_links)
                logger.info(f"✅ Найдено новых ссылок: {len(new_links)}")
            else:
                logger.info("📭 Все 15 ссылок уже просмотрены. Новых нет.")

        except Exception as e:
            logger.error(f"❌ Ошибка при поиске Sbazar по ключу '{keyword}': {e}")
        finally:
            await browser.close()

    if found_links:
        logger.info(f"🧠 Последние сохранённые: {found_links[-3:]}")
    return found_links
