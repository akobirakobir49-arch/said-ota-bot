"""Avtomatik (dasturiy) sifat nazorati — LLM-judge dan oldin ishlaydi."""
import html
import logging
import re

import config

log = logging.getLogger("quality")

ALLOWED_TAGS = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
                "code", "pre", "a", "tg-spoiler", "blockquote"}

# Qator boshidagi emoji (variatsiya selektori va rang modifikatorlari bilan)
EMOJI_START = re.compile(
    r"^(?:[\U0001F300-\U0001FAFF←-⇿⌀-➿⬀-⯿〰〽"
    r"©®™ℹ️‍\U0001F1E6-\U0001F1FF]"
    r"[️‍\U0001F3FB-\U0001F3FF]*)+"
)

# Tibbiy da'volar — taqiqlangan
MEDICAL_CLAIMS = [
    r"\bdavola(y|ydi|ngan|sh)\b", r"\bshifo\s*bo['’]?l", r"\bsaraton(ni)?\s+yo['’]?q",
    r"\bkasallikdan\s+xalos", r"\bdori\s+o['’]?rnini", r"\bimmunitetni\s+100",
    r"\bbutunlay\s+yo['’]?q\s+qiladi",
]

# To'ldirilmagan joy / shablon qoldiqlari
PLACEHOLDERS = [r"\[[^\]]{2,40}\]", r"\{\{", r"TODO", r"Lorem ipsum", r"XXX", r"\.\.\.\s*$"]

# Narx belgilari
PRICE_PATTERNS = [r"\d[\d\s.,]*\s*(so['’]?m|sum|UZS|\$|USD)", r"narxi\s*[:—-]\s*\d"]


def _check_html(text: str) -> list[str]:
    """Telegram HTML teglarining to'g'riligini tekshiradi."""
    problems = []
    stack = []
    for m in re.finditer(r"<\s*(/?)\s*([a-zA-Z0-9-]+)([^>]*)>", text):
        closing, tag = m.group(1) == "/", m.group(2).lower()
        if tag not in ALLOWED_TAGS:
            problems.append(f"Telegram qo'llab-quvvatlamaydigan HTML teg: <{tag}>")
            continue
        if closing:
            if not stack or stack[-1] != tag:
                problems.append(f"Noto'g'ri yopilgan teg: </{tag}>")
            else:
                stack.pop()
        else:
            stack.append(tag)
    if stack:
        problems.append(f"Yopilmagan teg(lar): {', '.join('<%s>' % t for t in stack)}")
    return problems


def _visible_length(text: str) -> int:
    """HTML teglarsiz haqiqiy uzunlik."""
    return len(html.unescape(re.sub(r"<[^>]+>", "", text)))


def check_post(post: dict) -> tuple[bool, list[str]]:
    """Dasturiy tekshiruvlar. Qaytaradi: (o'tdimi, muammolar)."""
    problems: list[str] = []
    text = (post.get("post_text") or "").strip()

    if not text:
        return False, ["Post matni bo'sh."]

    # Uzunlik (Telegram caption limiti = 1024 belgi, HTML teglar bilan birga)
    if len(text) > 1024:
        problems.append(f"Post juda uzun: {len(text)} belgi (Telegram limiti 1024).")
    vis = _visible_length(text)
    if vis < config.MIN_POST_CHARS:
        problems.append(f"Post juda qisqa: {vis} belgi (minimum {config.MIN_POST_CHARS}).")
    if vis > config.MAX_POST_CHARS:
        problems.append(f"Post uzun: {vis} belgi (maksimum {config.MAX_POST_CHARS}).")

    # HTML to'g'riligi
    problems += _check_html(text)

    # Markdown qoldiqlari
    if re.search(r"(\*\*|^#{1,6}\s|^\s*\*\s+)", text, re.MULTILINE):
        problems.append("Matnda Markdown belgilari bor (**, #, *). Faqat HTML ishlatilsin.")

    # ---- Struktura (kanal uslubi) ----
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # 1-qator: emoji + <b>sarlavha</b>
    if not lines:
        return False, ["Post matni bo'sh."]
    first = lines[0]
    if not EMOJI_START.match(first):
        problems.append("Sarlavha emoji bilan boshlanmagan.")
    if not re.search(r"<b>.+?</b>", first, re.DOTALL):
        problems.append("1-qatorda <b>qalin</b> sarlavha yo'q.")

    # Emoji bilan boshlanuvchi abzaslar
    emoji_lines = [l for l in lines if EMOJI_START.match(l)]
    if len(emoji_lines) < 4:
        problems.append(
            f"Emoji bilan boshlanuvchi abzaslar kam: {len(emoji_lines)} ta "
            "(sarlavha + kamida 3 ta abzas kerak)."
        )

    # Emojilar takrorlanmasin
    starts = [EMOJI_START.match(l).group(0) for l in emoji_lines]
    dupes = {e for e in starts if starts.count(e) > 1}
    if dupes:
        problems.append(f"Abzas boshidagi emojilar takrorlangan: {' '.join(dupes)}")

    # Yakuniy savol
    tail = "\n".join(lines[-2:])
    if "?" not in tail:
        problems.append("Post oxirida auditoriyaga savol yo'q.")
    elif not re.search(r"[🤔💬❓]", tail):
        problems.append("Yakuniy savol 🤔 yoki 💬 emojisi bilan boshlanmagan.")

    # Kanal uslubida hashtag ishlatilmaydi
    if re.search(r"(^|\s)#\w", text):
        problems.append("Matnda hashtag bor — kanal uslubida hashtag ishlatilmaydi.")

    # Markdown ro'yxat belgisi "*" o'rniga "•" ishlatilsin
    if re.search(r"^\s*-\s+", text, re.MULTILINE):
        problems.append("Ro'yxat uchun '-' ishlatilgan, '•' bo'lishi kerak.")

    # Taqiqlar
    low = text.lower()
    for pat in MEDICAL_CLAIMS:
        if re.search(pat, low):
            problems.append(f"Taqiqlangan tibbiy da'vo topildi (namuna: {pat}).")
            break
    for pat in PLACEHOLDERS:
        if re.search(pat, text, re.MULTILINE):
            problems.append("Matnda to'ldirilmagan shablon/qavs qoldiqlari bor.")
            break
    for pat in PRICE_PATTERNS:
        if re.search(pat, low):
            problems.append("Matnda narx ko'rsatilgan — bu taqiqlangan.")
            break

    # Quiz
    quiz = post.get("quiz") or {}
    q, opts = quiz.get("question", ""), quiz.get("options") or []
    if not q:
        problems.append("Quiz savoli yo'q.")
    elif len(q) > 300:
        problems.append(f"Quiz savoli juda uzun: {len(q)} belgi (limit 300).")
    if len(opts) != 4:
        problems.append(f"Quiz variantlari soni {len(opts)} ta (aynan 4 ta bo'lishi kerak).")
    else:
        for i, o in enumerate(opts):
            if not str(o).strip():
                problems.append(f"Quiz {i + 1}-varianti bo'sh.")
            elif len(str(o)) > 100:
                problems.append(f"Quiz {i + 1}-varianti uzun: {len(str(o))} belgi (limit 100).")
        if len(set(str(o).strip().lower() for o in opts)) != 4:
            problems.append("Quiz variantlari orasida takror bor.")
    ci = quiz.get("correct_index")
    if not isinstance(ci, int) or not (0 <= ci < max(1, len(opts))):
        problems.append(f"Quiz 'correct_index' noto'g'ri: {ci}")
    if len(quiz.get("explanation", "")) > 200:
        problems.append("Quiz tushuntirishi 200 belgidan uzun.")

    # Rasm prompti
    if not (post.get("image_prompt") or "").strip():
        problems.append("Rasm uchun tavsif (image_prompt) yo'q.")

    return (len(problems) == 0), problems


def ensure_footer(text: str) -> str:
    """Kanal footerini qo'shadi (agar hali qo'shilmagan bo'lsa)."""
    footer = (config.POST_FOOTER or "").strip()
    if not footer:
        return text.strip()
    if config.CHANNEL_NAME in text and "➖➖" in text:
        return text.strip()
    return text.strip() + "\n\n" + footer
