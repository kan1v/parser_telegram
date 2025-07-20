import random
import json
import os

from config import HEADERS

def get_random_user_agent():
    return random.choice(HEADERS)

def get_random_proxy():
    from config import PROXIES
    return random.choice(PROXIES) if PROXIES else None

import json
import os

def load_seen_links(filepath):
    if not os.path.exists(filepath):
        # Файл ещё не создан — возвращаем пустой словарь и id=0
        return {}, 0
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                # Пустой файл — возвращаем пустой словарь и id=0
                return {}, 0
            
            data = json.loads(content)
            seen_links = {int(item["id"]): item["link"] for item in data}
            last_id = max(seen_links.keys()) if seen_links else 0
            return seen_links, last_id
    except Exception as e:
        print(f"⚠️ Ошибка при загрузке {filepath}: {e}")
        return {}, 0

def save_seen_links(filepath, seen_links: dict):
    # Записываем текущие ссылки в файл в формате JSON
    data = [{"id": k, "link": v} for k, v in seen_links.items()]
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_keywords(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
