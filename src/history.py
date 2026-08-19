"""Chiqqan mavzular tarixi — takrorlanishning oldini oladi."""
import json
import logging
import os
import random
from datetime import datetime

import config

log = logging.getLogger("history")

MAX_ENTRIES = 400          # tarixda saqlanadigan maksimal yozuv
RECENT_FOR_PROMPT = 45     # promptga uzatiladigan oxirgi mavzular soni
CATEGORY_COOLDOWN = 8      # oxirgi N ta postda ishlatilgan kategoriya qayta tanlanmaydi


def _ensure_dirs() -> None:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.PENDING_DIR, exist_ok=True)


def load() -> list[dict]:
    _ensure_dirs()
    if not os.path.exists(config.HISTORY_FILE):
        return []
    try:
        with open(config.HISTORY_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Tarixni o'qib bo'lmadi (%s), bo'sh tarixdan boshlanadi.", e)
        return []


def save(entries: list[dict]) -> None:
    _ensure_dirs()
    with open(config.HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(entries[-MAX_ENTRIES:], f, ensure_ascii=False, indent=2)


def add(category: str, topic: str, title: str, slot: str, message_id: int | None) -> None:
    entries = load()
    entries.append({
        "datetime": datetime.now(config.TZ).isoformat(timespec="seconds"),
        "slot": slot,
        "category": category,
        "topic": topic,
        "title": title,
        "message_id": message_id,
    })
    save(entries)
    log.info("Tarixga yozildi: %s", topic)


def recent_topics(limit: int = RECENT_FOR_PROMPT) -> list[str]:
    return [e.get("topic", "") for e in load()[-limit:] if e.get("topic")]


def pick_category() -> str:
    """Yaqinda ishlatilmagan kategoriyalardan tasodifiy bittasini tanlaydi."""
    used = {e.get("category") for e in load()[-CATEGORY_COOLDOWN:]}
    pool = [c for c in config.CATEGORIES if c not in used] or list(config.CATEGORIES)
    choice = random.choice(pool)
    log.info("Tanlangan kategoriya: %s", choice)
    return choice


# ---------- Poll uchun kutayotgan ma'lumot ----------
def pending_path(slot: str) -> str:
    return os.path.join(config.PENDING_DIR, f"{slot}.json")


def save_pending(slot: str, data: dict) -> None:
    _ensure_dirs()
    with open(pending_path(slot), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("Poll ma'lumoti saqlandi: %s", pending_path(slot))


def load_pending(slot: str) -> dict | None:
    path = pending_path(slot)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        log.error("Pending faylni o'qib bo'lmadi: %s", e)
        return None


def clear_pending(slot: str) -> None:
    path = pending_path(slot)
    if os.path.exists(path):
        os.remove(path)
