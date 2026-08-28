"""Har 15 daqiqada ishlaydigan tekshiruv: "hozir nima qilish kerak?"

GitHub Actions'ning cron mexanizmi kafolatlanmagan — ishlar soatlab kechikishi yoki
umuman tashlab yuborilishi mumkin. Shuning uchun tizim belgilangan vaqtni kutib
o'tirmaydi: har safar ishga tushganda holatni ko'radi va bajarilmagan ishni bajaradi.

Hech narsa qilish kerak bo'lmasa — 20-30 soniyada tugaydi.
"""
import argparse
import logging
import sys
from datetime import datetime, timedelta

import config
import history
import publish
import send_poll
import telegram_api as tg

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("tick")


def due_slot(now: datetime) -> tuple[dict | None, str]:
    """Hozir bajarilishi kerak bo'lgan slotni topadi.

    Qaytaradi: (slot yozuvi yoki None, sabab matni)
    """
    day = now.strftime("%Y-%m-%d")
    reasons = []

    for entry in config.POST_SCHEDULE:
        slot = entry["slot"]
        hh, mm = (int(x) for x in entry["publish_at"].split(":"))
        target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        start_from = target - timedelta(minutes=config.PREVIEW_LEAD_MINUTES)
        too_late = target + timedelta(hours=config.SKIP_IF_LATER_THAN_HOURS)

        status = history.slot_status(day, slot)
        if status:
            reasons.append(f"{slot}: allaqachon '{status}'")
            continue
        if now < start_from:
            reasons.append(f"{slot}: hali erta ({start_from.strftime('%H:%M')} dan)")
            continue
        if now > too_late:
            log.warning("%s sloti %s dan juda kech — o'tkazib yuborildi.",
                        slot, target.strftime("%H:%M"))
            history.mark_slot(day, slot, "skipped")
            tg.send_message(
                config.ADMIN_CHAT_ID,
                f"⏭ <b>{slot}</b> sloti o'tkazib yuborildi\n"
                f"Mo'ljal {target.strftime('%H:%M')} edi, hozir {now.strftime('%H:%M')} — "
                f"{config.SKIP_IF_LATER_THAN_HOURS} soatdan ko'p kechikkani uchun post "
                "chiqarilmadi.",
                raise_on_error=False)
            reasons.append(f"{slot}: juda kech, o'tkazildi")
            continue
        return entry, f"{slot} sloti bajarilishi kerak"

    return None, "; ".join(reasons) or "jadval bo'sh"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-slot", choices=[e["slot"] for e in config.POST_SCHEDULE],
                    help="jadvalga qaramasdan shu slotni bajarish")
    ap.add_argument("--dry-run", action="store_true",
                    help="kanalga chiqarmaydi, faqat adminga preview yuboradi")
    args = ap.parse_args()

    config.validate()
    now = datetime.now(config.TZ)
    log.info("Tekshiruv: %s (Toshkent)", now.strftime("%Y-%m-%d %H:%M"))

    did_something = False

    # 1) Vaqti kelgan test savollari
    try:
        sent = send_poll.send_due_polls()
        if sent:
            did_something = True
            log.info("%s ta test savoli yuborildi.", sent)
    except Exception:  # noqa: BLE001
        log.exception("Poll bosqichida xato")

    # 2) Post
    if args.force_slot:
        entry = next(e for e in config.POST_SCHEDULE if e["slot"] == args.force_slot)
        log.info("Qo'lda ishga tushirildi: %s", args.force_slot)
    else:
        entry, reason = due_slot(now)
        if entry is None:
            log.info("Post bo'yicha ish yo'q — %s", reason)

    if entry is not None:
        did_something = True
        try:
            publish.run_slot(entry, dry_run=args.dry_run)
        except Exception as exc:  # noqa: BLE001
            log.exception("Postni chiqarishda xato")
            tg.send_message(
                config.ADMIN_CHAT_ID,
                f"❌ <b>Post tayyorlashda xato</b> ({entry['slot']})\n"
                f"<code>{str(exc)[:450]}</code>\n\n"
                "<i>Keyingi tekshiruv qayta urinib ko'radi.</i>",
                raise_on_error=False)
            return 1

    if not did_something:
        log.info("Hech narsa qilish kerak emas.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        log.exception("Kutilmagan xato")
        try:
            tg.send_message(config.ADMIN_CHAT_ID,
                            f"❌ <b>Tizimda xato</b>\n<code>{str(exc)[:500]}</code>",
                            raise_on_error=False)
        except Exception:  # noqa: BLE001
            pass
        sys.exit(1)
