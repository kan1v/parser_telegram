from playwright.async_api import async_playwright
import urllib.parse
from utils import get_random_user_agent, get_random_proxy

import os
import logging

# Конфигурация логера
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

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


links_sbazar = set()

async def auto_scroll(page, pause=1500, max_empty_scrolls=3):
    empty_scrolls = 0
    try:
        last_height = await page.evaluate("document.body.scrollHeight")
    except Exception as e:
        logger.error(f"⚠️ Ошибка получения scrollHeight: {e}")
        return

    while empty_scrolls < max_empty_scrolls:
        try:
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(pause)
            new_height = await page.evaluate("document.body.scrollHeight")
        except Exception as e:
            if "Execution context was destroyed" in str(e):
                logger.error("⚠️ Контекст страницы уничтожен во время скроллинга (возможно, переход или reload).")
            else:
                logger.error(f"⚠️ Ошибка в процессе скроллинга: {e}")
            break

        if new_height == last_height:
            empty_scrolls += 1
        else:
            empty_scrolls = 0
        last_height = new_height



async def search_sbazar(keyword: str):
    found_links = []
    encoded_keyword = urllib.parse.quote(keyword)
    base_url = f"https://www.sbazar.cz/hledej/{encoded_keyword}/31-knihy-literatura"
    logger.info(f"Открываем Sbazar: {base_url}")

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
        context = await browser.new_context()
        page = await context.new_page()
        await page.set_extra_http_headers({"User-Agent": user_agent})

        try:
            await page.goto(base_url, timeout=80000)
            await page.wait_for_load_state("networkidle")


            # 👉 Закрываем cookie popup
            try:
                await page.click("button:has-text('Souhlasím')", timeout=6000)
                logger.info("✅ [Sbazar] Cookie popup закрыт")
                await page.wait_for_timeout(1500)  # 👈 даём время странице обновиться
            except:
                logger.info("ℹ️ [Sbazar] Cookie popup не найден")


            # 🔄 Автоскролл
            await auto_scroll(page)

            # ⏳ Ждём появления хотя бы одной карточки
            await page.wait_for_selector('a[href^="/inzerat/"]', timeout=20000)

            # 🔗 Получаем все потенциальные ссылки на товары
            items = await page.query_selector_all('a[href^="/"]')

            for item in items:
                href = await item.get_attribute("href")
                if (
                    href
                    and (
                        href.startswith("/inzerat/")
                        or href.startswith("/rozbalena-nabidka/")
                    )
                ):
                    full_url = "https://www.sbazar.cz" + href
                    if full_url not in found_links:
                        found_links.append(full_url)


        except Exception as e:
            logger.error(f"❌ [Sbazar] Ошибка при поиске по ключу '{keyword}': {e}")
        finally:
            await browser.close()

    logger.info(f"🔍 [Sbazar] По ключу '{keyword}' найдено {len(found_links)} ссылок")
    return found_links
