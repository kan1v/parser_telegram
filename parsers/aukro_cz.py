from playwright.async_api import async_playwright, Page
import asyncio

import logging
import os

# Конфигурация логера 
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("aukro")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    fh = logging.FileHandler(os.path.join(LOG_DIR, "aukro.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())


async def auto_scroll_until_selector(page: Page, selector: str, max_scrolls=20, pause=500):
    for _ in range(max_scrolls):
        try:
            await page.wait_for_selector(selector, timeout=1000)
            return True
        except:
            await page.evaluate("window.scrollBy(0, window.innerHeight);")
            await asyncio.sleep(pause / 1000)
    return False


async def search_aukro(keyword: str):
    url = f"https://aukro.cz/vysledky-vyhledavani?text={keyword}&searchAll=true&categoryId=8466&searchRedirectDisabled=true&subbrand=BAZAAR"
    logger.info(f"Открываем Aukro: {url}")
    found_links = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # 💬 Проверяем отсутствие результатов
            no_results = await page.query_selector("text='Nebyly nalezeny žádné výsledky'")
            if no_results:
                logger.info("Нет результатов по ключу")
                return []

            # 🔄 Скроллим, пока не появятся карточки
            success = await auto_scroll_until_selector(page, "a.item-card-main-container")
            if not success:
                logger.error("⚠️ Карточки не загрузились.")
                return found_links

            # ✅ Ждём карточки
            await page.wait_for_selector("a.item-card-main-container", timeout=8000)

            elements = await page.query_selector_all("a.item-card-main-container")
            for el in elements:
                href = await el.get_attribute("href")
                if href and href.startswith("/"):
                    href = "https://aukro.cz" + href
                if href and href not in found_links:
                    found_links.append(href)

            logger.info(f"🔍 По ключу '{keyword}' найдено {len(found_links)} ссылок")

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке Aukro: {e}")
        finally:
            await browser.close()

        return found_links
