from playwright.async_api import async_playwright
from utils import get_random_user_agent, get_rotated_proxy
import urllib.parse
import logging
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("bazos")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    fh = logging.FileHandler(os.path.join(LOG_DIR, "bazos.log"), encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())


async def search_bazos(keyword: str):
    found_links = set()  # ⚠️ используем set для устранения дублей

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
            encoded_keyword = urllib.parse.quote(keyword)
            search_url = f"https://knihy.bazos.cz/inzeraty/{encoded_keyword}/"
            logger.info(f"🔍 Открываем Bazos: {search_url}")
            await page.goto(search_url, timeout=50000)

            items = await page.query_selector_all("div.inzeratynadpis")
            if not items:
                logger.warning(f"⚠️ Не найдено элементов div.inzeratynadpis по ключу '{keyword}'")

            for item in items[:15]:
                link_handle = await item.query_selector("a")
                if link_handle:
                    href = await link_handle.get_attribute("href")
                    if href:
                        url = "https://knihy.bazos.cz" + href.strip()
                        found_links.add(url.lower())

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке Bazos: {e}")

        finally:
            await browser.close()

    links = list(found_links)
    logger.info(f"✅ [Bazos] По ключу '{keyword}' найдено {len(links)} уникальных ссылок")
    return links
