"""Telegram Bot API bilan ishlash."""
import json
import logging
import time

import requests

import config

log = logging.getLogger("telegram")
API = "https://api.telegram.org/bot{token}/{method}"


class TelegramError(RuntimeError):
    pass


def call(method: str, params: dict | None = None, files: dict | None = None,
         timeout: int = 60, raise_on_error: bool = True) -> dict | None:
    url = API.format(token=config.TELEGRAM_TOKEN, method=method)
    params = params or {}
    last_err = None
    for attempt in range(1, 4):
        try:
            r = requests.post(url, data=params, files=files, timeout=timeout)
            data = r.json()
            if data.get("ok"):
                return data.get("result")
            desc = data.get("description", "")
            # Rate limit
            if data.get("error_code") == 429:
                retry = data.get("parameters", {}).get("retry_after", 5)
                log.warning("Telegram 429, %ss kutilmoqda", retry)
                time.sleep(retry + 1)
                last_err = desc
                continue
            last_err = f"{data.get('error_code')}: {desc}"
            break  # boshqa xatoda qayta urinishdan foyda yo'q
        except (requests.RequestException, json.JSONDecodeError) as e:
            last_err = str(e)
            log.warning("Telegram tarmoq xatosi: %s (urinish %s/3)", e, attempt)
            time.sleep(3 * attempt)
            if files:
                break  # fayl oqimi qayta o'qilmaydi
    msg = f"Telegram {method} xatosi: {last_err}"
    if raise_on_error:
        raise TelegramError(msg)
    log.error(msg)
    return None


# ------------------------------------------------------------------
def send_photo(chat_id: str, photo_bytes: bytes, caption: str,
               reply_markup: dict | None = None, filename: str = "post.png") -> dict:
    params = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup)
    return call("sendPhoto", params, files={"photo": (filename, photo_bytes, "image/png")})


def send_message(chat_id: str, text: str, reply_markup: dict | None = None,
                 parse_mode: str = "HTML", raise_on_error: bool = True) -> dict | None:
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "link_preview_options": json.dumps({"is_disabled": True}),
    }
    if reply_markup:
        params["reply_markup"] = json.dumps(reply_markup)
    return call("sendMessage", params, raise_on_error=raise_on_error)


def send_quiz(chat_id: str, question: str, options: list[str], correct_index: int,
              explanation: str = "", reply_to: int | None = None,
              open_period: int | None = None) -> dict:
    params = {
        "chat_id": chat_id,
        "question": question[:300],
        "options": json.dumps([o[:100] for o in options], ensure_ascii=False),
        "type": "quiz",
        "correct_option_id": correct_index,
        "is_anonymous": "true",
    }
    if explanation:
        params["explanation"] = explanation[:200]
        params["explanation_parse_mode"] = "HTML"
    if open_period:
        params["open_period"] = open_period
    if reply_to:
        params["reply_parameters"] = json.dumps(
            {"message_id": reply_to, "allow_sending_without_reply": True}
        )
    return call("sendPoll", params)


def edit_caption(chat_id: str, message_id: int, caption: str,
                 reply_markup: dict | None = None) -> None:
    params = {
        "chat_id": chat_id,
        "message_id": message_id,
        "caption": caption[:1024],
        "parse_mode": "HTML",
    }
    params["reply_markup"] = json.dumps(reply_markup) if reply_markup else json.dumps({"inline_keyboard": []})
    call("editMessageCaption", params, raise_on_error=False)


def answer_callback(callback_id: str, text: str = "") -> None:
    call("answerCallbackQuery", {"callback_query_id": callback_id, "text": text[:200]},
         raise_on_error=False)


def get_updates(offset: int | None = None, timeout: int = 25) -> list[dict]:
    params = {"timeout": timeout, "allowed_updates": json.dumps(["callback_query"])}
    if offset is not None:
        params["offset"] = offset
    result = call("getUpdates", params, timeout=timeout + 20, raise_on_error=False)
    return result or []


def drop_pending_updates() -> int | None:
    """Eski (o'qilmagan) update'larni tashlab yuboradi va yangi offset qaytaradi."""
    updates = get_updates(offset=-1, timeout=0)
    if updates:
        return updates[-1]["update_id"] + 1
    return None


def wait_for_regen_click(deadline_ts: float, offset: int | None, token: str) -> tuple[bool, int | None]:
    """Belgilangan vaqtgacha admin 'Qayta qilish' tugmasini bosishini kutadi.

    Qaytaradi: (bosildimi, yangi_offset)
    """
    log.info("Admin javobini kutmoqda (%.0f sekund)...", max(0, deadline_ts - time.time()))
    while time.time() < deadline_ts:
        remaining = deadline_ts - time.time()
        poll_timeout = int(max(1, min(25, remaining)))
        updates = get_updates(offset=offset, timeout=poll_timeout)
        for u in updates:
            offset = u["update_id"] + 1
            cq = u.get("callback_query")
            if not cq:
                continue
            data = cq.get("data", "")
            from_id = str(cq.get("from", {}).get("id", ""))
            if from_id != str(config.ADMIN_CHAT_ID):
                answer_callback(cq["id"], "Bu tugma faqat admin uchun.")
                continue
            if data == f"regen:{token}":
                answer_callback(cq["id"], "♻️ Qabul qilindi. Post qaytadan tayyorlanmoqda...")
                log.info("Admin qayta generatsiyani so'radi.")
                return True, offset
            # eski postning tugmasi
            answer_callback(cq["id"], "Bu post allaqachon yakunlangan.")
        if not updates:
            time.sleep(1)
    return False, offset


def regen_keyboard(token: str) -> dict:
    return {"inline_keyboard": [[{"text": "🔄 Qayta qilish", "callback_data": f"regen:{token}"}]]}
