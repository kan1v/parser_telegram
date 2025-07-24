import random
import json
import hashlib
from config import HEADERS, PROXIES


def get_rotated_proxy(key: str):
    key_hash = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return PROXIES[key_hash % len(PROXIES)]


def get_random_user_agent():
    return random.choice(HEADERS)


def normalize_link(link: str) -> str:
    return link.strip().lower()


def load_seen_links(filename: str) -> set[str]:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            seen = {normalize_link(link) for link in data.get("seen", [])}
            return seen
    except FileNotFoundError:
        return set()
    except Exception as e:
        print(f"❌ Ошибка загрузки файла {filename}: {e}")
        return set()


def save_seen_links(filename: str, seen_links: set[str]):
    try:
        normalized = sorted({normalize_link(link) for link in seen_links})
        data = {
            "seen": normalized
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Ошибка сохранения файла {filename}: {e}")


def load_keywords(filepath: str) -> list[str]:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"❌ Ошибка загрузки ключей из файла {filepath}: {e}")
        return []
