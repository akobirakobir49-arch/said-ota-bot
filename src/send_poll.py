"""Chiqqan post bo'yicha kanalga test (quiz) savolini yuboradi."""
import argparse
import logging
import sys

import config
import history
import telegram_api as tg

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("poll")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", required=True, choices=["morning", "evening"])
    args = ap.parse_args()

    config.validate()

    pending = history.load_pending(args.slot)
    if not pending:
        log.warning("'%s' sloti uchun kutayotgan poll topilmadi — o'tkazib yuborildi.", args.slot)
        return 0

    quiz = pending.get("quiz") or {}
    question = (quiz.get("question") or "").strip()
    options = [str(o) for o in (quiz.get("options") or []) if str(o).strip()]
    ci = quiz.get("correct_index", 0)

    if not question or len(options) < 2:
        log.error("Quiz ma'lumoti yaroqsiz: %s", quiz)
        tg.send_message(config.ADMIN_CHAT_ID,
                        f"⚠️ '{args.slot}' uchun test savoli yaroqsiz, yuborilmadi.",
                        raise_on_error=False)
        history.clear_pending(args.slot)
        return 0

    if not isinstance(ci, int) or not (0 <= ci < len(options)):
        ci = 0

    intro = f"❓ <b>Bugungi post bo'yicha savol</b>\nMavzu: {pending.get('topic', '')}"
    tg.send_message(config.CHANNEL_ID, intro,
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
                    f"❓ '{args.slot}' posti bo'yicha test savoli kanalga yuborildi.",
                    raise_on_error=False)

    history.clear_pending(args.slot)
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
