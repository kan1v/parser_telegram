import asyncio
import logging
import os
import sys
import urllib.parse
from playwright.async_api import async_playwright, Page

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

DEBUG_BROWSER = True  # 👈 True — видимый браузер, False — headless

CARD_SELECTORS = [
    "a.item-card-main-container",
    "a.tw-group.item-card.tw-min-w-[16.5rem]",
    "a.item-card",  # запасной
]


logger = logging.getLogger("aukro-test")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    fh = logging.FileHandler(os.path.join(LOG_DIR, "aukro_test.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())


async def popup_watcher(page: Page, run_flag: asyncio.Event):
    selector = "a:has(i.material-icons.cursor-pointer.vertical-bottom)"
    logger.info("👁 Попап-страж запущен")

    while not run_flag.is_set():
        try:
            popup = await page.query_selector(selector)
            if popup:
                await popup.click()
                logger.info(f"✅ Попап закрыт: {selector}")
                await asyncio.sleep(1.0)
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при закрытии попапа: {e}")
        await asyncio.sleep(1.5)

    logger.info("👁 Попап-страж завершён")


async def auto_scroll(page: Page):
    last_count = 0
    attempts = 0
    max_scrolls = 30

    for i in range(max_scrolls):
        logger.info(f"🔄 Скролл {i + 1}/{max_scrolls}")
        await page.mouse.wheel(0, 1200)
        await asyncio.sleep(2.5)

        found = []
        for sel in CARD_SELECTORS:
            items = await page.query_selector_all(sel)
            if items:
                logger.info(f"✅ Селектор сработал: {sel} — найдено {len(items)} карточек")
                found = items
                break
            else:
                logger.debug(f"❌ Селектор {sel} не дал результатов")

        count = len(found)
        if count > last_count:
            last_count = count
            attempts = 0
        else:
            attempts += 1

        if attempts >= 3:
            logger.info("🛑 3 скролла подряд без новых карточек.")
            break

    await asyncio.sleep(2.0)
    return found



async def search_aukro(keyword: str):
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://aukro.cz/vysledky-vyhledavani?text={encoded_keyword}&categoryId=8466"

    logger.info(f"🔎 Открываем Aukro: {url}")
    found_links = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not DEBUG_BROWSER)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=50000)
            await asyncio.sleep(3.0)

            stop_flag = asyncio.Event()

            # 👁 Стартуем наблюдателя за попапом
            watcher = asyncio.create_task(popup_watcher(page, stop_flag))

            # 🔄 Скроллим
            elements = await auto_scroll(page)

            # 🛑 Завершаем наблюдателя
            stop_flag.set()
            await watcher

            if not elements:
                logger.warning("⚠️ Карточки не загружены.")
                return

            for el in elements[:15]:
                href = await el.get_attribute("href")
                if href and href.startswith("/"):
                    found_links.append("https://aukro.cz" + href)


            logger.info(f"✅ Найдено ссылок: {len(found_links)}")
            for link in found_links:
                print(link)

        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
        finally:
            if DEBUG_BROWSER:
                logger.info("🧪 Браузер оставлен открытым для отладки...")
                await asyncio.sleep(99999)
            else:
                await browser.close()


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        keyword = " ".join(sys.argv[1:])
    else:
        keyword = "kniha"
    print(f"\n🔍 Запуск с ключом: {keyword}\n")
    asyncio.run(search_aukro(keyword))
