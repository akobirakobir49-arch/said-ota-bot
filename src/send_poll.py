"""Chiqqan post bo'yicha kanalga test (quiz) savolini yuboradi.

Poll o'z vaqti kelganda yuboriladi — GitHub jadvali kechiksa ham yo'qolmaydi,
keyingi tekshiruv uni tutib oladi.
"""
import argparse
import logging
import sys
from datetime import datetime, timedelta

import config
import history
import telegram_api as tg

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("poll")


def _parse(dt_str: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt if dt.tzinfo else dt.replace(tzinfo=config.TZ)
    except (TypeError, ValueError):
        return None


def send_one(slot: str, force: bool = False) -> bool:
    """Bitta slot uchun poll yuboradi. Yuborilgan bo'lsa True."""
    pending = history.load_pending(slot)
    if not pending:
        log.info("'%s' uchun kutayotgan poll yo'q.", slot)
        return False

    now = datetime.now(config.TZ)
    due = _parse(pending.get("poll_due_at", ""))
    if due is None:
        published = _parse(pending.get("published_at", ""))
        hours = float(pending.get("poll_after_hours", 6))
        due = (published + timedelta(hours=hours)) if published else now

    if not force and now < due:
        log.info("'%s' polli hali erta (%s da chiqadi).", slot, due.strftime("%H:%M"))
        return False

    late_h = (now - due).total_seconds() / 3600
    if not force and late_h > config.POLL_MAX_LATE_HOURS:
        log.warning("'%s' polli %0.1f soat kechikkan — eskirgani uchun yuborilmaydi.",
                    slot, late_h)
        history.clear_pending(slot)
        return False

    quiz = pending.get("quiz") or {}
    question = (quiz.get("question") or "").strip()
    options = [str(o) for o in (quiz.get("options") or []) if str(o).strip()]
    ci = quiz.get("correct_index", 0)

    if not question or len(options) < 2:
        log.error("Quiz ma'lumoti yaroqsiz: %s", quiz)
        tg.send_message(config.ADMIN_CHAT_ID,
                        f"⚠️ '{slot}' uchun test savoli yaroqsiz, yuborilmadi.",
                        raise_on_error=False)
        history.clear_pending(slot)
        return False

    if not isinstance(ci, int) or not (0 <= ci < len(options)):
        ci = 0

    tg.send_message(config.CHANNEL_ID,
                    f"❓ <b>Bugungi post bo'yicha savol</b>\nMavzu: {pending.get('topic', '')}",
                    raise_on_error=False)

    res = tg.send_quiz(
        chat_id=config.CHANNEL_ID,
        question=question,
        options=options,
        correct_index=ci,
        explanation=quiz.get("explanation", ""),
        reply_to=pending.get("channel_message_id"),
    )
    log.info("Test savoli yuborildi. message_id=%s", (res or {}).get("message_id"))

    tg.send_message(config.ADMIN_CHAT_ID,
                    f"❓ '{slot}' posti bo'yicha test savoli kanalga yuborildi.",
                    raise_on_error=False)
    history.clear_pending(slot)
    return True


def send_due_polls() -> int:
    """Vaqti kelgan barcha polllarni yuboradi. Yuborilganlar sonini qaytaradi."""
    sent = 0
    for entry in config.POST_SCHEDULE:
        try:
            if send_one(entry["slot"]):
                sent += 1
        except Exception as e:  # noqa: BLE001
            log.exception("'%s' pollini yuborishda xato", entry["slot"])
            tg.send_message(config.ADMIN_CHAT_ID,
                            f"❌ Test savolini yuborishda xato ({entry['slot']}): "
                            f"<code>{str(e)[:300]}</code>", raise_on_error=False)
    return sent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", choices=[e["slot"] for e in config.POST_SCHEDULE],
                    help="faqat shu slot uchun")
    ap.add_argument("--force", action="store_true", help="vaqtini kutmasdan yuborish")
    args = ap.parse_args()

    config.validate()
    if args.slot:
        send_one(args.slot, force=args.force)
    else:
        send_due_polls()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        log.exception("Kutilmagan xato")
        try:
            tg.send_message(config.ADMIN_CHAT_ID,
                            f"❌ <b>Test savolini yuborishda xato</b>\n<code>{str(exc)[:400]}</code>",
                            raise_on_error=False)
        except Exception:  # noqa: BLE001
            pass
        sys.exit(1)
