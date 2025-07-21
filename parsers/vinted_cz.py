from playwright.async_api import async_playwright
from utils import get_random_user_agent, get_random_proxy
import urllib.parse
import time

import logging
import os

# Конфигурация логера 
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

    base_url = (
        f"https://www.vinted.cz/catalog?"
        f"search_text={encoded_keyword}&catalog[]=2312&page=1&time={current_timestamp}"
    )
    logger.info(f"Открываем Vinted: {base_url}")

    async with async_playwright() as p:
        user_agent = get_random_user_agent()
        proxy = get_random_proxy()
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
            await page.goto(base_url, timeout=60000)

            # Скроллим вниз для загрузки карточек
            for _ in range(5):
                await page.mouse.wheel(0, 2500)
                await page.wait_for_timeout(1200)

            # Получаем карточки товаров
            items = await page.query_selector_all(
                "div.new-item-box__image-container a[href*='/items/']"
            )

            for item in items:
                href = await item.get_attribute("href")
                if href and "/items/" in href:
                    full_url = "https://www.vinted.cz" + href
                    if full_url not in found_links:
                        found_links.append(full_url)

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке Vinted: {e}")
        finally:
            await browser.close()

    logger.info(f"🔍 [Vinted] По ключу '{keyword}' найдено {len(found_links)} ссылок")
    return found_links
