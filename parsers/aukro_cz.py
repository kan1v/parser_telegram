from playwright.async_api import async_playwright, Page
import asyncio
import logging
import os
import json
from utils import get_random_user_agent, get_random_proxy

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
SEEN_FILE = "seen_links_aukro.json"

logger = logging.getLogger("aukro")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    fh = logging.FileHandler(os.path.join(LOG_DIR, "aukro.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())

def load_seen_links():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_seen_links(links: set):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(list(links), f, ensure_ascii=False, indent=2)

async def close_popup_if_exists(page: Page):
    try:
        await asyncio.sleep(2)
        popup = await page.query_selector("div.popup, div[data-testid='modal-root']")
        if popup:
            logger.info("🟡 Обнаружено всплывающее меню, пробуем закрыть...")
            await page.mouse.click(500, 500)
            await asyncio.sleep(1)
    except Exception as e:
        logger.warning(f"⚠️ Не удалось закрыть popup: {e}")

async def auto_scroll(page: Page, step=2000, max_scrolls=30):
    previous_height = 0
    for i in range(max_scrolls):
        await page.mouse.wheel(0, step)
        await asyncio.sleep(1.2)
        current_height = await page.evaluate("document.body.scrollHeight")
        if current_height == previous_height:
            logger.info(f"⏹️ Скроллинг завершён на {i+1}-м проходе.")
            break
        previous_height = current_height

async def wait_for_all_results(page: Page, selector: str, max_scrolls=30):
    seen_ids = set()
    for i in range(max_scrolls):
        elements = await page.query_selector_all(selector)
        new = [el for el in elements if str(id(el)) not in seen_ids]
        for el in new:
            seen_ids.add(str(id(el)))
        logger.info(f"⏬ Скролл #{i + 1}: найдено {len(new)} новых элементов (всего: {len(seen_ids)})")
        if not new:
            break
        await page.mouse.wheel(0, 2000)
        await asyncio.sleep(1.2)
    if not seen_ids:
        logger.warning("⚠️ Не удалось найти карточки товаров.")
        content = await page.content()
        with open("aukro_debug.html", "w", encoding="utf-8") as f:
            f.write(content)
        logger.warning("💾 Сохранил HTML в aukro_debug.html для анализа.")
    return await page.query_selector_all(selector)

async def search_aukro(keyword: str):
    url = (
        f"https://aukro.cz/vysledky-vyhledavani?"
        f"text={keyword}&searchAll=true&categoryId=8466"
        f"&searchRedirectDisabled=true&subbrand=BAZAAR"
    )
    logger.info(f"🔎 Открываем Aukro: {url}")
    found_links = []

    seen_links = load_seen_links()

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
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await close_popup_if_exists(page)
            await asyncio.sleep(2)  # немного подождать отрисовки

            no_results = await page.locator("text='Nebyly nalezeny žádné výsledky'").is_visible()
            if no_results:
                logger.info(f"❌ Нет результатов по ключу '{keyword}'")
                return []

            await auto_scroll(page)
            elements = await wait_for_all_results(page, "a.item-card-main-container")
            if not elements:
                return []

            for el in elements:
                href = await el.get_attribute("href")
                if href and href.startswith("/"):
                    href = "https://aukro.cz" + href
                if href and href not in seen_links:
                    found_links.append(href)
                    seen_links.add(href)

            save_seen_links(seen_links)
            logger.info(f"🔗 Найдено {len(found_links)} новых ссылок по ключу '{keyword}'")

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке Aukro: {e}")

        finally:
            await browser.close()

    return found_links
