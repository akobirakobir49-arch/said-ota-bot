"""Oflayn tekshiruv: tarmoqsiz ishlaydigan qismlarni sinaydi."""
import glob
import json
import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
os.environ.setdefault("TELEGRAM_TOKEN", "x")
os.environ.setdefault("GEMINI_API_KEY", "x")
os.environ.setdefault("ADMIN_CHAT_ID", "1")

import config  # noqa: E402
import history  # noqa: E402
import prompts  # noqa: E402
import quality  # noqa: E402

fails = []


def check(name, cond, info=""):
    print(("  ✅ " if cond else "  ❌ ") + name + (f" — {info}" if info and not cond else ""))
    if not cond:
        fails.append(name)


print("\n[1] Workflow YAML fayllari")
for f in sorted(glob.glob(".github/workflows/*.yml")):
    try:
        d = yaml.safe_load(open(f))
        jobs = list(d.get("jobs", {}).keys())
        check(f"{f} (jobs: {jobs})", bool(jobs))
    except Exception as e:
        check(f, False, str(e))

print("\n[2] Jadval sozlamalari")
_tickf = ".github/workflows/tick.yml"
check("tick.yml mavjud", os.path.exists(_tickf))
_tick = yaml.safe_load(open(_tickf))
_crons = [c["cron"] for c in _tick[True]["schedule"]]   # YAML da 'on:' -> True
check(f"Cron: {_crons}", _crons == ["3,18,33,48 * * * *"], str(_crons))
check("Eski post.yml o'chirilgan", not os.path.exists(".github/workflows/post.yml"))
check("Eski poll.yml o'chirilgan", not os.path.exists(".github/workflows/poll.yml"))
check("Timeout 75 daqiqadan oshmaydi",
      _tick["jobs"]["tick"]["timeout-minutes"] <= 75)
_slots = {e["slot"]: e["publish_at"] for e in config.POST_SCHEDULE}
check(f"Chiqish vaqtlari: {_slots}",
      _slots == {"morning": "09:00", "evening": "17:00"}, str(_slots))
check("Kechikishga chidamlilik sozlangan",
      config.SKIP_IF_LATER_THAN_HOURS >= 2 and config.LATE_START_GRACE_MINUTES >= 5)

print("\n[3] Promptlar to'g'ri format bo'ladimi")
try:
    p = prompts.RESEARCH_PROMPT.format(category="Mevalar", month_name="avgust",
                                       recent_topics="- yo'q")
    check("RESEARCH_PROMPT", "Mevalar" in p and "{" not in p.split("Javobni")[0])
except Exception as e:
    check("RESEARCH_PROMPT", False, str(e))

try:
    p = prompts.WRITE_PROMPT.format(research_json="{}", style_guide=prompts.STYLE_GUIDE)
    check("WRITE_PROMPT", "POST STILI" in p)
except Exception as e:
    check("WRITE_PROMPT", False, str(e))

try:
    p = prompts.QC_PROMPT.format(post_text="salom", research_json="{}")
    check("QC_PROMPT", "salom" in p)
except Exception as e:
    check("QC_PROMPT", False, str(e))

try:
    p = prompts.FIX_PROMPT.format(post_text="a", problems="b", fix_instructions="c",
                                  research_json="{}", style_guide=prompts.STYLE_GUIDE)
    check("FIX_PROMPT", "c" in p)
except Exception as e:
    check("FIX_PROMPT", False, str(e))

print("\n[4] Sifat nazorati — YAXSHI post o'tishi kerak (kanal uslubi)")
GOOD = (
    "🍎 <b>Olma po‘stlog‘ini archib tashlash — eng katta xato</b>\n\n"
    "🥗 Ko‘pchilik olmani archib yeydi va eng qimmatli qismini axlatga tashlaydi.\n\n"
    "📊 Po‘stloqda mevaning tolasi taxminan <b>2 barobar</b> ko‘p to‘planadi.\n\n"
    "🌿 Kversetin nomli antioksidant ham asosan aynan po‘stloqda bo‘ladi.\n\n"
    "💧 Uni iliq suvda yaxshilab yuvish kifoya — archish shart emas.\n\n"
    "🤔 <b>Siz olmani po‘stlog‘i bilan yeysizmi?</b>"
)
good_post = {
    "post_text": GOOD,
    "image_prompt": "fresh red apples",
    "quiz": {"question": "Olmaning qaysi qismida tola ko'proq?",
             "options": ["Po'stlog'ida", "Urug'ida", "Bandida", "Faqat ichida"],
             "correct_index": 0, "explanation": "Po'stloqda tola ~2 barobar ko'p."},
}
ok, probs = quality.check_post(good_post)
check("Yaxshi post PASS bo'ldi", ok, str(probs))
check(f"Uzunlik {len(GOOD)} < 1024", len(GOOD) < 1024)

print("\n[5] Sifat nazorati — YOMON postlarni ushlashi kerak")
cases = {
    "juda qisqa": {**good_post, "post_text": "🍎 <b>Salom</b>\n\n🥗 a\n\n📊 b\n\n🤔 <b>Savol?</b>"},
    "markdown bor": {**good_post, "post_text": GOOD.replace("<b>", "**").replace("</b>", "**")},
    "tibbiy da'vo": {**good_post, "post_text": GOOD + "\n\n🩺 Bu kasallikni davolaydi."},
    "narx bor": {**good_post, "post_text": GOOD + "\n\n💵 Narxi: 15000 so'm"},
    "yopilmagan teg": {**good_post, "post_text": GOOD.replace("</b>", "", 1)},
    "quiz 3 variant": {**good_post, "quiz": {**good_post["quiz"], "options": ["a", "b", "c"]}},
    "correct_index xato": {**good_post, "quiz": {**good_post["quiz"], "correct_index": 9}},
    "shablon qavs": {**good_post, "post_text": GOOD + "\n\n📝 [bu yerga matn]"},
    "hashtag bor": {**good_post, "post_text": GOOD + "\n\n#SaidOtaMarket"},
    "sarlavhada emoji yo'q": {**good_post, "post_text": GOOD.replace("🍎 ", "", 1)},
    "yakuniy savol yo'q": {**good_post,
                           "post_text": GOOD.rsplit("\n\n", 1)[0] + "\n\n🛒 Marketga keling."},
    "emoji takrorlangan": {**good_post, "post_text": GOOD.replace("📊", "🥗").replace("🌿", "🥗")},
    "abzaslar kam": {**good_post,
                     "post_text": "🍎 <b>Sarlavha bu yerda uzun bo‘lsin</b>\n\n"
                                  + "🥗 " + "Bu juda uzun bitta abzas. " * 12
                                  + "\n\n🤔 <b>Savol?</b>"},
    "'-' li ro'yxat": {**good_post, "post_text": GOOD.replace("💧 Uni", "- Uni")},
}
for name, bad in cases.items():
    ok, probs = quality.check_post(bad)
    check(f"'{name}' ushlandi", not ok, "ushlanmadi!")

print("\n[6] Footer (CTA + havolalar)")
f = quality.build_footer()
t = quality.ensure_footer(GOOD)
check("Footer qo'shildi", config.FOOTER_DIVIDER in t)
check("Footer takrorlanmadi (idempotent)", quality.ensure_footer(t) == t)
check("CTA matni bor", (not config.CTA_TEXT) or config.CTA_TEXT in f)
active = [(e, n, u) for e, n, u in config.SOCIAL_LINKS if u.strip()]
for emoji, nom, url in active:
    check(f"Havola: {nom}", f'<a href="{url}">{nom}</a>' in f)
check("Bo'sh havolalar ko'rsatilmadi",
      all(n not in f for e, n, u in config.SOCIAL_LINKS if not u.strip()))
check(f"Ko'rinadigan uzunlik {quality._visible_length(t)} < 1024",
      quality._visible_length(t) < 1024)
for _ph in config.PHONE_NUMBERS:
    check(f"Telefon: {_ph}", _ph in f)
check("Havolalar '|' bilan ajratilgan",
      len(active) < 2 or config.SOCIAL_SEPARATOR.strip() in f)
check("Havolalar tartibi (Instagram -> Telegram -> YouTube)",
      [n for _, n, u in config.SOCIAL_LINKS if u.strip()] ==
      [n for n in ["Instagram", "Telegram", "YouTube"] if n in f])
ok_f, probs_f = quality.check_post({**good_post, "post_text": GOOD})
check("Footer joyi hisobga olingan (yaxshi post hali ham PASS)", ok_f, str(probs_f))

print("\n[6b] Kategoriya og'irliklari")
history.save([])
import collections as _c
dist = _c.Counter(history.pick_category() for _ in range(3000))
low = [k for k, v in config.CATEGORY_WEIGHTS.items() if v < 1]
for k in low:
    share = 100 * dist[k] / 3000
    check(f"'{k[:28]}...' kam chiqadi ({share:.1f}%)", share < 2.0, f"{share:.1f}%")
check("Barcha kategoriyalar ishlatilgan", len(dist) == len(config.CATEGORIES),
      f"{len(dist)}/{len(config.CATEGORIES)}")
history.save([])

print("\n[7] History / kategoriya tanlash")
history.save([])
cats = set()
for i in range(30):
    c = history.pick_category()
    cats.add(c)
    history.add(c, f"mavzu-{i}", f"sarlavha-{i}", "morning", i)
check(f"Turli kategoriyalar ishlatildi ({len(cats)} ta)", len(cats) >= 10)
recent = history.recent_topics(5)
check("recent_topics oxirgi 5 tani berdi", recent == [f"mavzu-{i}" for i in range(25, 30)],
      str(recent))
entries = history.load()
check("Tarix saqlandi", len(entries) == 30, str(len(entries)))

print("\n[8] Pending poll saqlash/o'qish")
history.save_pending("morning", {"channel_message_id": 5, "quiz": {"question": "q"}})
p = history.load_pending("morning")
check("Pending o'qildi", p and p["channel_message_id"] == 5)
history.clear_pending("morning")
check("Pending tozalandi", history.load_pending("morning") is None)

print("\n[9] Config butunligi")
check(f"Kategoriyalar: {len(config.CATEGORIES)} ta", len(config.CATEGORIES) >= 15)
check("MAX_POST_CHARS < 1024", config.MAX_POST_CHARS < 1024)
check("TZ = Asia/Tashkent", str(config.TZ) == "Asia/Tashkent")

print("\n[10] Model tanlash mantiqi (tarmoqsiz)")
import gemini_api as G  # noqa: E402

FAKE = [{"name": f"models/{n}", "supportedGenerationMethods": ["generateContent"]}
        for n in ["gemini-3.6-flash", "gemini-3.7-flash", "gemini-2.5-flash",
                  "gemini-3.1-flash-image", "gemini-2.5-flash-image",
                  "text-embedding-004"]]
G._models_cache, G._resolved = FAKE, {}
check("Matn modeli = gemini-3.6-flash", G.text_model() == "gemini-3.6-flash", G.text_model())
check("Rasm modeli = gemini-3.1-flash-image",
      G.image_model() == "gemini-3.1-flash-image", G.image_model())

# Ustuvor ro'yxatdagilarning hech biri yo'q — mos keladiganini topishi kerak
G._models_cache = [{"name": "models/gemini-9-flash", "supportedGenerationMethods": ["generateContent"]},
                   {"name": "models/gemini-9-flash-image"}]
G._resolved = {}
check("Notanish matn modeli topildi", G.text_model() == "gemini-9-flash", G.text_model())
check("Notanish rasm modeli topildi", G.image_model() == "gemini-9-flash-image", G.image_model())

# Ro'yxat umuman bo'lmasa — ustuvor birinchisiga qaytadi
G._models_cache, G._resolved = [], {}
check("Ro'yxat bo'sh bo'lsa zaxira model", G.text_model() == config.TEXT_MODEL_PREFERENCE[0])

print("\n[10b] Javobdan rasmni ajratib olish")
PNG = "iVBORw0KGgo" + "A" * 600
check("inlineData (eski format)",
      G._find_image_b64({"candidates": [{"content": {"parts": [{"inlineData": {"data": PNG}}]}}]}) == PNG)
check("Interactions formati",
      G._find_image_b64({"steps": [{"output_image": {"b64_json": PNG}}]}) == PNG)
check("Chuqur joylashgan ro'yxat",
      G._find_image_b64({"a": [{"b": {"imageBytes": PNG}}]}) == PNG)
check("Rasm yo'q bo'lsa None", G._find_image_b64({"text": "salom"}) is None)
check("Qisqa matnni rasm deb olmaydi", G._find_image_b64({"data": "iVBORw0KGgo"}) is None)
G._models_cache, G._resolved = None, {}

print("\n[10c] JSON ajratib olish (uzilib qolgan javoblar ham)")
check("Toza JSON", G._extract_json('{"a": 1}') == {"a": 1})
check("```json blok ichida", G._extract_json('Mana:\n```json\n{"a": 2}\n```') == {"a": 2})
check("Yopilmagan blok", G._extract_json('```json\n{"a": 3}') == {"a": 3})
check("Matn orasidagi JSON", G._extract_json('Javob: {"a": 4} tamom') == {"a": 4})
for bad, nom in [('```json\n{\n "topic": "Muzlatilgan baliq", "facts": [', "uzilib qolgan"),
                 ('', "bo'sh javob"),
                 ('shunchaki matn', "JSON yo'q")]:
    try:
        G._extract_json(bad)
        check(f"'{nom}' xato beradi", False, "xato bermadi")
    except G.GeminiError as e:
        check(f"'{nom}' xato beradi", True)
        if nom == "uzilib qolgan":
            check("  ...va sababini aytadi", "uzilib qolgan" in str(e), str(e)[:80])

print("\n[10d] finishReason va token chegarasi")
check("MAX_TOKENS aniqlanadi",
      G._finish_reason({"candidates": [{"finishReason": "MAX_TOKENS"}]}) == "MAX_TOKENS")
check("STOP aniqlanadi", G._finish_reason({"candidates": [{"finishReason": "STOP"}]}) == "STOP")
check("finishReason yo'q", G._finish_reason({"candidates": [{}]}) == "")
check("Tadqiqot token chegarasi katta", config.MAX_TOKENS_RESEARCH >= 16384,
      str(config.MAX_TOKENS_RESEARCH))
check("Thinking darajasi belgilangan", config.THINKING_LEVEL in
      (None, "minimal", "low", "medium", "high"), str(config.THINKING_LEVEL))

# _json_generate: uzilgan javobdan keyin chegarani oshirib qayta so'rashi kerak
calls = []


def fake_gen(payload, timeout=180):
    budget = payload["generationConfig"]["maxOutputTokens"]
    calls.append(budget)
    if len(calls) == 1:
        return {"candidates": [{"finishReason": "MAX_TOKENS",
                                "content": {"parts": [{"text": '```json\n{"a":'}]}}]}
    return {"candidates": [{"finishReason": "STOP",
                            "content": {"parts": [{"text": '{"a": 1}'}]}}]}


_real_gen = G._gen
G._gen = fake_gen
try:
    res = G._json_generate({"contents": []}, 1000)
    check("Uzilgan javobdan keyin qayta urinadi", res == {"a": 1} and len(calls) == 2, str(calls))
    check("Token chegarasi oshirildi", calls[1] > calls[0], str(calls))
finally:
    G._gen = _real_gen

print("\n[10e] Rubrika 2: Qiziqarli faktlar")
FACTS_POST = {
    "post_text": (
        "🤔 <b>Bilarmidingiz? — asal haqida 4 ta hayratlanarli fakt</b>\n\n"
        "🍯 Asal deyarli hech qachon buzilmaydi. Misr piramidalaridan topilgan "
        "<b>3000 yillik</b> asal hali ham yeyishga yaroqli bo‘lgan.\n\n"
        "🐝 Bir choy qoshiq asal uchun asalari butun umri davomida ishlaydi.\n\n"
        "🌍 Bir kilogramm asal uchun asalarilar <b>4 million</b> gulni aylanib chiqadi.\n\n"
        "🎨 Asalning rangi gulga bog‘liq: qarag‘ay asali deyarli qora, akatsiyaniki tiniq.\n\n"
        "💬 <b>Qaysi fakt sizni ko‘proq hayratlantirdi?</b>"
    ),
    "image_prompt": "honey jar",
    "quiz": {"question": "1 kg asal uchun necha gul kerak?",
             "options": ["4 million", "4 ming", "400", "40 million"],
             "correct_index": 0, "explanation": "Taxminan 4 million gul."},
}
okf, pf = quality.check_post(FACTS_POST, rubric="facts")
check("Fakt posti PASS bo'ldi", okf, str(pf))
no_bilar = {**FACTS_POST, "post_text": FACTS_POST["post_text"].replace("Bilarmidingiz? — ", "")}
check("«Bilarmidingiz?» yo'qligi ushlanadi",
      not quality.check_post(no_bilar, rubric="facts")[0])
check("Rubrikalar slotga bog'langan",
      set(config.SLOT_RUBRIC.values()) == {"useful", "facts"}, str(config.SLOT_RUBRIC))
check("Fakt uslub qo'llanmasi tijorat qoidasini o'z ichiga oladi",
      "SAVDOGA OID" in prompts.style_guide("facts"))
check("Foydali uslub qo'llanmasi ham",
      "SAVDOGA OID" in prompts.style_guide("useful"))
check("{commercial_rules} qoldig'i yo'q",
      "{commercial_rules}" not in prompts.style_guide("facts")
      and "{commercial_rules}" not in prompts.style_guide("useful"))
try:
    prompts.research_prompt("facts").format(category="Asal", month_name="avgust",
                                            recent_topics="- yo'q")
    check("Fakt tadqiqot prompti formatlanadi", True)
except Exception as e:
    check("Fakt tadqiqot prompti formatlanadi", False, str(e))

print("\n[10f] Supermarketga qarshi iboralar filtri")
ANTI = {
    "sotib olmang": "🚫 Bu mahsulotni sotib olmang.",
    "voz keching": "🚫 Konservalardan butunlay voz keching.",
    "mahsulot turi yomonlangan": "🚫 Konservalar juda zararli hisoblanadi.",
    "kimyoga to'la": "🚫 Bu mahsulotlar kimyoga to‘la.",
    "do'kondan olmang": "🚫 Buni do‘kondan olmang, o‘zingiz qiling.",
}
for nom, jumla in ANTI.items():
    bad = {**good_post, "post_text": GOOD.rsplit("\n\n", 1)[0] + "\n\n" + jumla
           + "\n\n🤔 <b>Savol?</b>"}
    okx, px = quality.check_post(bad)
    hit = any("savdosiga qarshi" in str(x) for x in px)
    check(f"'{nom}' ushlandi", hit, str(px)[:120])
check("Yaxshi post filtrga tushmadi",
      not any("savdosiga qarshi" in str(x) for x in quality.check_post(good_post)[1]))

print("\n[10g] Jadval mantiqi (kechikishga chidamlilik)")
import telegram_api as _tg  # noqa: E402
_tg.send_message = lambda *a, **k: None          # tarmoqqa chiqmaslik uchun
_tg.call = lambda *a, **k: None
import tick  # noqa: E402
from datetime import datetime as _dt, timedelta as _td  # noqa: E402


def _at(h, m=0):
    return _dt.now(config.TZ).replace(hour=h, minute=m, second=0, microsecond=0)


history.save_state({})
CASES = [(7, 0, None, "juda erta"), (8, 29, None, "1 daqiqa erta"),
         (8, 30, "morning", "lead boshlanishi"), (8, 45, "morning", "lead ichida"),
         (9, 30, "morning", "30 daq kechikkan — baribir bajariladi"),
         (12, 59, "morning", "4 soatga yaqin kechikkan — hali bajariladi"),
         (13, 1, None, "4 soatdan oshdi — o'tkaziladi"),
         (16, 30, "evening", "kechqurun lead"),
         (17, 45, "evening", "45 daq kechikkan"),
         (21, 30, None, "juda kech")]
for h, m, exp, izoh in CASES:
    history.save_state({})
    e, _ = tick.due_slot(_at(h, m))
    check(f"{h:02d}:{m:02d} -> {e['slot'] if e else 'yo`q'} ({izoh})",
          (e["slot"] if e else None) == exp)

history.save_state({})
_day = _at(9).strftime("%Y-%m-%d")
history.mark_slot(_day, "morning", "published")
check("Chiqqan post takror chiqmaydi", tick.due_slot(_at(9, 30))[0] is None)
history.save_state({})
tick.due_slot(_at(14, 0))
check("Juda kechikkan slot 'skipped' deb belgilanadi",
      history.slot_status(_at(14).strftime("%Y-%m-%d"), "morning") == "skipped")
history.save_state({})

print("\n[10h] Poll navbati (vaqti kelganda yuboriladi)")
import send_poll as _sp  # noqa: E402
_now = _dt.now(config.TZ)
history.save_pending("morning", {
    "channel_message_id": 1, "topic": "test", "poll_after_hours": 6,
    "published_at": (_now - _td(hours=1)).isoformat(timespec="seconds"),
    "poll_due_at": (_now + _td(hours=5)).isoformat(timespec="seconds"),
    "quiz": {"question": "q?", "options": ["a", "b", "c", "d"], "correct_index": 0},
})
check("Vaqti kelmagan poll yuborilmaydi", _sp.send_one("morning") is False)
check("...va navbatda qoladi", history.load_pending("morning") is not None)

history.save_pending("morning", {
    "channel_message_id": 1, "topic": "test", "poll_after_hours": 6,
    "published_at": (_now - _td(hours=30)).isoformat(timespec="seconds"),
    "poll_due_at": (_now - _td(hours=24)).isoformat(timespec="seconds"),
    "quiz": {"question": "q?", "options": ["a", "b", "c", "d"], "correct_index": 0},
})
check("Juda eskirgan poll yuborilmaydi", _sp.send_one("morning") is False)
check("...va navbatdan o'chiriladi", history.load_pending("morning") is None)
history.save_state({})

print("\n[11] Modullar import bo'ladimi")
for m in ["gemini_api", "telegram_api", "publish", "send_poll", "check", "tick"]:
    try:
        __import__(m)
        check(m, True)
    except SystemExit:
        check(m, True)  # config.validate() chaqirilgan bo'lishi mumkin
    except Exception as e:
        check(m, False, str(e))

# tozalash
history.save([])

print("\n" + "=" * 50)
if fails:
    print(f"❌ {len(fails)} ta tekshiruv xato: {fails}")
    sys.exit(1)
print("✅ BARCHA OFLAYN TEKSHIRUVLAR MUVAFFAQIYATLI")
