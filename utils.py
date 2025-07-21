import random
import json
import os

from config import HEADERS, PROXIES
from urllib.parse import urlparse

def get_random_user_agent():
    return random.choice(HEADERS)

def get_random_proxy():
    return random.choice(PROXIES)

def load_seen_links(filename: str):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            seen = set(data.get("seen", []))
            last_id = data.get("last_id", None)
            return seen, last_id
    except FileNotFoundError:
        return set(), None
    except Exception as e:
        print(f"Ошибка загрузки файла {filename}: {e}")
        return set(), None

def save_seen_links(filename: str, seen_links: set, last_id):
    try:
        data = {
            "seen": list(seen_links),
            "last_id": last_id
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения файла {filename}: {e}")


def load_keywords(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
