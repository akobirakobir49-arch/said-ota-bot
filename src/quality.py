"""Avtomatik (dasturiy) sifat nazorati — LLM-judge dan oldin ishlaydi."""
import html
import logging
import re

import config

log = logging.getLogger("quality")

# O'zbek matnida apostrof turli belgilar bilan yoziladi: ' ‘ ’ ʻ ʼ `
APOS = "['‘’ʻʼ`´]"

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
    r"\bdavola(y|ydi|ngan|sh)\b", r"\bshifo\s*bo"+APOS+"?l", r"\bsaraton(ni)?\s+yo"+APOS+"?q",
    r"\bkasallikdan\s+xalos", r"\bdori\s+o"+APOS+"?rnini", r"\bimmunitetni\s+100",
    r"\bbutunlay\s+yo"+APOS+"?q\s+qiladi",
]

# To'ldirilmagan joy / shablon qoldiqlari
PLACEHOLDERS = [r"\[[^\]]{2,40}\]", r"\{\{", r"TODO", r"Lorem ipsum", r"XXX", r"\.\.\.\s*$"]

# Narx belgilari
PRICE_PATTERNS = [r"\d[\d\s.,]*\s*(so"+APOS+"?m|sum|UZS|\$|USD)", r"narxi\s*[:—-]\s*\d"]

# Supermarket savdosiga qarshi ishlaydigan iboralar — taqiqlangan
ANTI_COMMERCIAL = [
    (r"\b(sotib\s+olma|xarid\s+qilma|iste"+APOS+r"?mol\s+qilma|yeb\s+bo"+APOS+r"?lma)(ng|ylik|slik)",
     "«sotib olmang / iste'mol qilmang» turidagi chaqiriq"),
    (r"\bvoz\s+kech(ing|ish|ing?lar)", "«voz keching» chaqirig'i"),
    (r"\b(umuman|hech\s+qachon)\s+\w{0,12}(yema|ishlatma|olma)", "keskin taqiq chaqirig'i"),
    (r"\b(konserva\w*|muzlatilgan\s+\w+|yarim\s*tayyor\w*|sanoat\s+\w+|do"+APOS+"?kon\s+\w+)"
     r"[^.!?]{0,40}\b(zararli|xavfli|yomon|foydasiz|sifatsiz|zaharli)",
     "mahsulot turini yomonlash"),
    (r"\b(zararli|xavfli|zaharli)[^.!?]{0,40}\b(konserva\w*|qo"+APOS+"?shimcha\w*|"
     r"konservant\w*|bo"+APOS+"?yoq\w*)", "qo'shimchalar haqida qo'rqitish"),
    (r"\bE-?\s?\d{3}\b[^.!?]{0,50}(zarar|xavf|saraton|allergi)", "E-qo'shimchalar bilan qo'rqitish"),
    (r"\bkimyo(viy)?\s*(ga)?\s*to"+APOS+"?la", "«kimyoga to'la» iborasi"),
    (r"do"+APOS+"?kondan\s+olma(ng|slik)", "do'kondan chetlashtirish"),
    (r"bozordan\s+ol(gan|ing)[^.!?]{0,30}(yaxshi|foydali|toza)", "do'konni bozorga qarama-qarshi qo'yish"),
    (r"\buyda\s+tayyorlang[^.!?]{0,40}do"+APOS+"?kon", "do'kon mahsulotini rad etishga undash"),
]


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


def check_post(post: dict, rubric: str = "useful") -> tuple[bool, list[str]]:
    """Dasturiy tekshiruvlar. Qaytaradi: (o'tdimi, muammolar)."""
    problems: list[str] = []
    text = (post.get("post_text") or "").strip()
    min_chars, max_chars = config.RUBRIC_LENGTH.get(
        rubric, (config.MIN_POST_CHARS, config.MAX_POST_CHARS))

    if not text:
        return False, ["Post matni bo'sh."]

    # Uzunlik. Telegram limiti (1024) HTML teglarsiz, ko'rinadigan matnga nisbatan.
    # Footer keyinroq qo'shilgani uchun unga joy qoldiramiz.
    vis = _visible_length(text)
    footer_len = _visible_length(build_footer())
    if vis + footer_len > 1010:
        problems.append(
            f"Post juda uzun: {vis} belgi + footer {footer_len} "
            "(Telegram rasm izohi limiti 1024)."
        )
    if vis < min_chars:
        problems.append(f"Post juda qisqa: {vis} belgi (minimum {min_chars}).")
    if vis > max_chars:
        problems.append(f"Post uzun: {vis} belgi (maksimum {max_chars}).")

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
    for pat, nom in ANTI_COMMERCIAL:
        if re.search(pat, low):
            problems.append(f"Supermarket savdosiga qarshi ishlaydi: {nom}.")
            break

    # "Bilarmidingiz?" rubrikasi uchun qo'shimcha tekshiruv
    if rubric == "facts" and "bilarmidingiz" not in low:
        problems.append("Sarlavhada «Bilarmidingiz?» yo'q.")

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


def build_footer() -> str:
    """Ajratuvchi chiziq + CTA + ijtimoiy tarmoq havolalari + telefonlar."""
    lines = [config.FOOTER_DIVIDER]
    if config.CTA_TEXT:
        lines.append(config.CTA_TEXT)

    links = [f'{emoji} <a href="{html.escape(url, quote=True)}">{name}</a>'
             for emoji, name, url in config.SOCIAL_LINKS if url.strip()]
    if links:
        lines.append(config.SOCIAL_SEPARATOR.join(links))

    phones = [p.strip() for p in config.PHONE_NUMBERS if p.strip()]
    if phones:
        lines.append("")
        for i, p in enumerate(phones):
            lines.append(f"{config.PHONE_EMOJI} {p}" if i == 0 else f"{p}")

    return "\n".join(lines).strip()


def ensure_footer(text: str) -> str:
    """Kanal footerini qo'shadi (agar hali qo'shilmagan bo'lsa)."""
    footer = build_footer()
    if not footer:
        return text.strip()
    if config.FOOTER_DIVIDER in text:
        return text.strip()
    return text.strip() + "\n\n" + footer
