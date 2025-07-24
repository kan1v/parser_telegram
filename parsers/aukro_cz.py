from playwright.async_api import async_playwright, Page
import asyncio
import logging
import os
import urllib.parse

from utils import get_random_user_agent, load_seen_links, save_seen_links, get_rotated_proxy

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
SEEN_FILE = "parsers/aukro_cz_seen.json"

logger = logging.getLogger("aukro")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    fh = logging.FileHandler(os.path.join(LOG_DIR, "aukro.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())

CARD_SELECTORS = [
    "a.item-card-main-container",
    "a.tw-group.item-card.tw-min-w-\\[16\\.5rem\\]",
    "a.item-card",
]


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
        logger.info(f"🔀 Скролл {i + 1}/{max_scrolls}")
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
            logger.info("🚩 3 скролла подряд без новых карточек.")
            break

    await asyncio.sleep(2.0)
    return found


async def search_aukro(keyword: str):
    encoded_keyword = urllib.parse.quote(keyword)
    url = f"https://aukro.cz/vysledky-vyhledavani?text={encoded_keyword}&categoryId=8466"
    logger.info(f"🔎 Открываем Aukro: {url}")
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
                "username": proxy.get("username"),
                "password": proxy.get("password"),
            }

        browser = await p.chromium.launch(**launch_args)
        context = await browser.new_context(user_agent=user_agent)
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=50000)
            await asyncio.sleep(3.0)

            stop_flag = asyncio.Event()
            watcher_task = asyncio.create_task(popup_watcher(page, stop_flag))

            # ⬇️ Выполняем полноценный скроллинг с попытками
            elements = await auto_scroll(page)

            stop_flag.set()
            await watcher_task

            if not elements:
                logger.warning("📭 Карточки не найдены после скроллинга.")
                return []

            top_links = []
            for el in elements:
                if len(top_links) >= 15:
                    break

                href = await el.get_attribute("href")
                if href and href.startswith("/"):
                    full_url = f"https://aukro.cz{href.strip()}"
                    normalized = full_url.strip().lower()
                    top_links.append(normalized)

            new_links = [link for link in top_links if link not in seen_links]

            if new_links:
                found_links = new_links
                seen_links.update(top_links)
                save_seen_links(SEEN_FILE, seen_links)
                logger.info(f"✅ Найдено новых ссылок: {len(new_links)}")
            else:
                logger.info("📭 Все 15 ссылок уже просмотрены. Новых нет.")

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке Aukro: {e}")
        finally:
            await browser.close()

    if found_links:
        logger.info(f"🧠 Последние новые: {found_links[-3:]}")
    return found_links
