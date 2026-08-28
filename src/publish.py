"""Asosiy oqim: mavzu qidirish -> post yozish -> sifat nazorati -> rasm ->
adminga preview -> 'Qayta qilish' kutish -> kanalga chiqarish."""
import argparse
import logging
import secrets
import sys
import time
from datetime import datetime, timedelta

import config
import gemini_api
import history
import quality
import telegram_api as tg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("publish")

MONTHS_UZ = ["yanvar", "fevral", "mart", "aprel", "may", "iyun",
             "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr"]


# ---------------------------------------------------------------- kontent
def build_content(rubric: str = "useful") -> tuple[dict, dict, dict]:
    """Tadqiqot -> post -> sifat nazorati sikli. Qaytaradi (post, research, qc)."""
    category = history.pick_category()
    now = datetime.now(config.TZ)
    log.info("Rubrika: %s (%s)", rubric, config.RUBRIC_NAMES.get(rubric, rubric))
    research = gemini_api.research(
        category=category,
        month_name=MONTHS_UZ[now.month - 1],
        recent_topics=history.recent_topics(),
        rubric=rubric,
    )

    post = gemini_api.write_post(research, rubric=rubric)
    post["_rubric"] = rubric
    post["_category"] = category
    post["_topic"] = research.get("topic", "")
    last_qc: dict = {}

    for attempt in range(1, config.MAX_CONTENT_ATTEMPTS + 1):
        ok, problems = quality.check_post(post, rubric=rubric)
        if not ok:
            log.warning("Dasturiy tekshiruv muammolari (%s-urinish): %s", attempt, problems)
            if attempt == config.MAX_CONTENT_ATTEMPTS:
                last_qc = {"verdict": "FAIL", "score": 0, "problems": problems,
                           "fix_instructions": "Yuqoridagi barcha muammolarni bartaraf eting."}
                break
            fixed = gemini_api.fix_post(
                post,
                {"problems": problems,
                 "fix_instructions": "Yuqoridagi texnik muammolarni bartaraf eting. "
                                     "Uzunlik va Telegram HTML qoidalariga qat'iy amal qiling."},
                research,
                rubric=rubric,
            )
            fixed["_category"], fixed["_topic"] = category, research.get("topic", "")
            fixed["_rubric"] = rubric
            post = fixed
            continue

        qc = gemini_api.quality_check(post["post_text"], research)
        last_qc = qc
        log.info("LLM sifat nazorati: %s (ball: %s)", qc.get("verdict"), qc.get("score"))
        if qc.get("verdict") == "PASS":
            break
        if attempt == config.MAX_CONTENT_ATTEMPTS:
            log.warning("Sifat nazorati %s urinishdan keyin ham PASS bo'lmadi.", attempt)
            break
        fixed = gemini_api.fix_post(post, qc, research, rubric=rubric)
        fixed["_category"], fixed["_topic"] = category, research.get("topic", "")
        fixed["_rubric"] = rubric
        post = fixed

    post["post_text"] = quality.ensure_footer(post["post_text"])
    return post, research, last_qc


def make_image(post: dict) -> bytes | None:
    return gemini_api.generate_image(post.get("image_prompt", post.get("_topic", "food")))


# ---------------------------------------------------------------- preview
def send_preview(post: dict, image: bytes | None, qc: dict, token: str,
                 publish_at: datetime, round_no: int) -> int | None:
    quiz = post.get("quiz", {})
    opts = quiz.get("options", [])
    ci = quiz.get("correct_index", 0)
    correct = opts[ci] if isinstance(ci, int) and 0 <= ci < len(opts) else "?"

    header = (
        f"🧾 <b>PREVIEW</b> · {round_no}-variant\n"
        f"🗂 {config.RUBRIC_NAMES.get(post.get('_rubric', 'useful'), '-')}\n"
        f"📂 {post.get('_category', '-')}\n"
        f"🕒 Chiqish vaqti: <b>{publish_at.strftime('%H:%M')}</b>\n"
        f"✅ Sifat nazorati: {qc.get('verdict', '-')} ({qc.get('score', '-')}/100)\n"
    )
    if qc.get("problems"):
        header += "⚠️ " + "; ".join(str(p) for p in qc["problems"][:2])[:200] + "\n"
    if image is None:
        header += "🖼 <i>Rasm generatsiya qilinmadi — post matn holida chiqadi.</i>\n"
    header += "\n" + "─" * 20 + "\n\n"

    footer = (
        "\n\n" + "─" * 20 + "\n"
        f"❓ <b>Test savoli</b> (poll {post.get('_poll_time', '—')} da chiqadi):\n"
        f"{quiz.get('question', '-')}\n"
        + "\n".join(f"{'✅' if i == ci else '▫️'} {o}" for i, o in enumerate(opts))
        + "\n\n<i>Hech narsa bosmasangiz — post belgilangan vaqtda avtomatik chiqadi.\n"
          "Yoqmasa «🔄 Qayta qilish» tugmasini bosing.</i>"
    )

    kb = tg.regen_keyboard(token)
    body = post["post_text"]

    if image:
        # Rasm izohi 1024 belgi bilan cheklangan -> rasm + qisqa izoh, batafsil ma'lumot alohida
        cap = header + body
        if len(cap) > 1024:
            res = tg.send_photo(config.ADMIN_CHAT_ID, image, header[:1000])
            tg.send_message(config.ADMIN_CHAT_ID, body, raise_on_error=False)
            msg = tg.send_message(config.ADMIN_CHAT_ID, footer, reply_markup=kb,
                                  raise_on_error=False)
            return (msg or res or {}).get("message_id")
        res = tg.send_photo(config.ADMIN_CHAT_ID, image, cap)
        msg = tg.send_message(config.ADMIN_CHAT_ID, footer, reply_markup=kb,
                              raise_on_error=False)
        return (msg or res or {}).get("message_id")

    msg = tg.send_message(config.ADMIN_CHAT_ID, header + body + footer, reply_markup=kb,
                          raise_on_error=False)
    return (msg or {}).get("message_id")


# ---------------------------------------------------------------- publish
def publish(post: dict, image: bytes | None) -> int | None:
    text = post["post_text"]
    if image:
        res = tg.send_photo(config.CHANNEL_ID, image, text)
    else:
        res = tg.send_message(config.CHANNEL_ID, text)
    mid = (res or {}).get("message_id")
    log.info("Kanalga chiqarildi. message_id=%s", mid)
    return mid


# ---------------------------------------------------------------- slotni bajarish
def run_slot(entry: dict, dry_run: bool = False) -> bool:
    """Bitta slotni to'liq bajaradi. Muvaffaqiyatli bo'lsa True."""
    slot = entry["slot"]
    rubric = entry.get("rubric", "useful")
    poll_after = float(entry.get("poll_after_hours", 6))

    now = datetime.now(config.TZ)
    hh, mm = (int(x) for x in entry["publish_at"].split(":"))
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)

    # Kechikib ishga tushgan bo'lsak, adminga baribir qisqa vaqt beramiz
    if now < target:
        deadline = target
    else:
        deadline = now + timedelta(minutes=config.LATE_START_GRACE_MINUTES)
        log.warning("Kechikib ishga tushdik (%s o'rniga %s) — adminga %s daqiqa beriladi.",
                    target.strftime("%H:%M"), now.strftime("%H:%M"),
                    config.LATE_START_GRACE_MINUTES)

    log.info("=== SLOT: %s | rubrika: %s | mo'ljal: %s | deadline: %s ===",
             slot, rubric, target.strftime("%H:%M"), deadline.strftime("%H:%M"))

    offset = tg.drop_pending_updates()

    post, research, qc = build_content(rubric)
    image = make_image(post)
    post["_poll_time"] = (datetime.now(config.TZ)
                          + timedelta(hours=poll_after)).strftime("%H:%M")

    round_no = 1
    while True:
        token = secrets.token_hex(4)
        send_preview(post, image, qc, token, deadline, round_no)

        clicked, offset = tg.wait_for_regen_click(deadline.timestamp(), offset, token)
        if not clicked:
            break
        if round_no >= config.MAX_REGENERATIONS:
            tg.send_message(
                config.ADMIN_CHAT_ID,
                f"⚠️ Qayta generatsiya limiti ({config.MAX_REGENERATIONS}) tugadi. "
                "Oxirgi variant kanalga chiqarilmoqda.",
                raise_on_error=False,
            )
            break

        round_no += 1
        tg.send_message(config.ADMIN_CHAT_ID,
                        f"♻️ <b>{round_no}-variant</b> tayyorlanmoqda, biroz kuting...",
                        raise_on_error=False)
        try:
            post, research, qc = build_content(rubric)
            image = make_image(post)
        except Exception as e:  # noqa: BLE001
            log.exception("Qayta generatsiya xatosi")
            tg.send_message(config.ADMIN_CHAT_ID,
                            f"❌ Qayta generatsiya xatosi: <code>{str(e)[:300]}</code>\n"
                            "Oldingi variant chiqariladi.", raise_on_error=False)
            break
        deadline = datetime.now(config.TZ) + timedelta(minutes=config.REGEN_WAIT_MINUTES)
        post["_poll_time"] = (deadline + timedelta(hours=poll_after)).strftime("%H:%M")

    if dry_run:
        log.info("DRY-RUN: kanalga chiqarilmadi.")
        tg.send_message(config.ADMIN_CHAT_ID, "🧪 <b>DRY-RUN</b> — kanalga chiqarilmadi.",
                        raise_on_error=False)
        return True

    mid = publish(post, image)
    published_at = datetime.now(config.TZ)

    history.save_pending(slot, {
        "channel_message_id": mid,
        "topic": post.get("_topic", ""),
        "category": post.get("_category", ""),
        "rubric": rubric,
        "published_at": published_at.isoformat(timespec="seconds"),
        "poll_after_hours": poll_after,
        "poll_due_at": (published_at + timedelta(hours=poll_after)).isoformat(timespec="seconds"),
        "quiz": post.get("quiz", {}),
    })
    history.add(post.get("_category", ""), post.get("_topic", ""),
                post.get("title", ""), slot, mid)
    history.mark_slot(published_at.strftime("%Y-%m-%d"), slot, "published")

    tg.send_message(
        config.ADMIN_CHAT_ID,
        f"✅ <b>Post kanalga chiqarildi</b>\n"
        f"🗂 {config.RUBRIC_NAMES.get(rubric, '-')}\n"
        f"📂 {post.get('_category', '-')}\n"
        f"📝 {post.get('_topic', '-')}\n"
        f"❓ Test savoli ~{(published_at + timedelta(hours=poll_after)).strftime('%H:%M')} da chiqadi.",
        raise_on_error=False,
    )
    return True


# ---------------------------------------------------------------- CLI (qo'lda)
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", required=True, choices=[e["slot"] for e in config.POST_SCHEDULE])
    ap.add_argument("--dry-run", action="store_true",
                    help="kanalga chiqarmaydi, faqat adminga preview yuboradi")
    args = ap.parse_args()

    config.validate()
    entry = next(e for e in config.POST_SCHEDULE if e["slot"] == args.slot)
    run_slot(entry, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        log.exception("Kutilmagan xato")
        try:
            tg.send_message(config.ADMIN_CHAT_ID,
                            f"❌ <b>Post tayyorlashda xato</b>\n<code>{str(exc)[:500]}</code>",
                            raise_on_error=False)
        except Exception:  # noqa: BLE001
            pass
        sys.exit(1)
