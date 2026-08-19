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

print("\n[2] Cron vaqtlari -> Toshkent vaqti")
CRONS = {"15 3 * * *": "08:15", "15 11 * * *": "16:15",
         "0 10 * * *": "15:00", "0 15 * * *": "20:00"}
for cron, expected in CRONS.items():
    m, h = cron.split()[0], cron.split()[1]
    tosh = f"{(int(h) + 5) % 24:02d}:{int(m):02d}"
    check(f"'{cron}' UTC = {tosh} Toshkent", tosh == expected, f"kutilgan {expected}")

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

print("\n[6] ensure_footer")
t = quality.ensure_footer(GOOD)
check("Footer qo'shildi", config.CHANNEL_NAME in t and "➖➖" in t)
check("Footer takrorlanmadi (idempotent)", quality.ensure_footer(t) == t)
check(f"Footer bilan umumiy uzunlik {len(t)} < 1024", len(t) < 1024)

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

print("\n[10] Modullar import bo'ladimi")
for m in ["gemini_api", "telegram_api", "publish", "send_poll", "check"]:
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
