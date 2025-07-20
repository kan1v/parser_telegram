TELEGRAM_BOT_TOKEN = "8097790916:AAHXiC-vBhazXm1-x24qXK8HbHb_BX7nEpo"
TELEGRAM_CHAT_ID = 539998404  

KEYWORDS_FILE = "parsers/keywords.txt"
SEEN_LINKS_FILE = {
    "bazos": "parsers/bazos_cz_seen.json",
    "sbazar": "parsers/sbazar_cz_seen.json",
    "vinted": "parsers/vinted_cz_seen.json",
    "aukro": "parsers/aukro_cz_seen.json"
}

# Пока без прокси
PROXIES = [
    # "http://user:pass@ip:port",
    # "http://ip:port",
]

# User-Agent'ы для ротации
HEADERS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
]
