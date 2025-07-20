from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto("https://www.sbazar.cz/hledej/Knihy%20s%20Toyen")

    # Пробуем закрыть окно с согласием
    try:
        # Ждём любую кнопку/тег с текстом Souhlasím
        consent_button = page.wait_for_selector("text=Souhlasím", timeout=8000)
        consent_button.click()
        print("✅ Вікно 'Souhlasím' закрито")
    except:
        print("⚠️ Не вдалося знайти кнопку 'Souhlasím'")

    # Ждём товары
    try:
        page.wait_for_selector("div[class*='screen-offer-card']", timeout=10000)
        print("✅ Знайдено блоки товарів")
    except:
        print("❌ Не вдалося знайти товари")
        page.screenshot(path="screenshot_error.png", full_page=True)
        browser.close()
        exit()

    # Сбор ссылок
    cards = page.query_selector_all("div[class*='screen-offer-card']")
    print(f"🔍 Знайдено {len(cards)} товарів")

    for i, card in enumerate(cards, 1):
        a_tag = card.query_selector("a")
        link = a_tag.get_attribute("href") if a_tag else "—"
        if link and link.startswith("/"):
            link = "https://www.sbazar.cz" + link
        print(f"{i}. {link}")

    browser.close()
