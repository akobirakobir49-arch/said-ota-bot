"""Tizim chiqaradigan postlarning namunasi (qo'lda yozilgan, sifat nazoratidan o'tkaziladi)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
os.environ.setdefault("TELEGRAM_TOKEN", "x")
os.environ.setdefault("GEMINI_API_KEY", "x")
os.environ.setdefault("ADMIN_CHAT_ID", "1")

import quality  # noqa: E402

SAMPLES = [
    {
        "post_text": (
            "🥩 <b>Go‘shtni iliq suvda eritish — eng keng tarqalgan xato</b>\n\n"
            "⚠️ Iliq suvda go‘shtning sirti tez isiydi, ichi esa hali muzday qoladi.\n\n"
            "🦠 Aynan shu oraliqda sirtdagi bakteriyalar jadal ko‘paya boshlaydi.\n\n"
            "❄️ Xavfsiz usul — go‘shtni bir kecha oldin muzxonadan sovutgichning "
            "pastki javoniga olib qo‘yish.\n\n"
            "⏱ Shoshilinch bo‘lsa: germetik paketga solib, faqat <b>sovuq</b> oqar "
            "suv ostida eriting.\n\n"
            "🤔 <b>Siz go‘shtni odatda qanday eritasiz?</b>"
        ),
        "image_prompt": "raw beef thawing on a plate in a fridge",
        "quiz": {
            "question": "Muzlatilgan go‘shtni eritishning eng xavfsiz usuli qaysi?",
            "options": ["Sovutgichning pastki javonida", "Iliq suvda",
                        "Xona haroratida stolda", "Mikroto‘lqinli pechda to‘liq"],
            "correct_index": 0,
            "explanation": "Sekin, past haroratda erish bakteriyalar ko‘payishiga yo‘l qo‘ymaydi.",
        },
    },
    {
        "post_text": (
            "🍯 <b>Asal qotib qolgani — buzilgani emas, aksincha</b>\n\n"
            "🍶 Ko‘pchilik kristallangan asalni «eskirgan» deb o‘ylab, sotib olmaydi.\n\n"
            "📊 Aslida kristallanish — tabiiy asalning belgisi. Tarkibida glyukoza "
            "ko‘p bo‘lsa, u tezroq qotadi.\n\n"
            "🔥 Asalni <b>40 darajadan</b> yuqori qizdirmang — foydali fermentlari "
            "yo‘qoladi.\n\n"
            "💧 Idishni iliq suvga qo‘yib, sekin eritish kifoya.\n\n"
            "💬 <b>Sizga qaysi asal ko‘proq yoqadi — suyuqmi yoki qotgani?</b>"
        ),
        "image_prompt": "crystallized honey in a glass jar with a wooden dipper",
        "quiz": {
            "question": "Asalning kristallanishi nimani bildiradi?",
            "options": ["Tabiiy ekanini", "Buzilganini", "Shakar qo‘shilganini",
                        "Muddati o‘tganini"],
            "correct_index": 0,
            "explanation": "Kristallanish tabiiy asalda glyukoza ko‘pligidan darak beradi.",
        },
    },
    {
        "post_text": (
            "🥬 <b>Ko‘katlarni yuvib saqlash — ular tezroq chiriydi</b>\n\n"
            "💦 Yuvilgan ko‘katda qolgan namlik barglarni ichkaridan buzadi.\n\n"
            "🧻 To‘g‘ri usul: quruq holda quruq sochiqqa o‘rab, konteynerga soling.\n\n"
            "🌿 Shu tarzda jambil, kashnich va ukrop <b>2 baravar</b> uzoq turadi.\n\n"
            "🔪 Yuvishni esa faqat dasturxonga tortishdan oldin qiling.\n\n"
            "🤔 <b>Sizning ko‘katlaringiz sovutgichda necha kun chidaydi?</b>"
        ),
        "image_prompt": "fresh herbs wrapped in a kitchen towel inside a container",
        "quiz": {
            "question": "Ko‘katlarni sovutgichda uzoq saqlash uchun nima qilish kerak?",
            "options": ["Quruq sochiqqa o‘rab qo‘yish", "Yuvib, suvli idishga solish",
                        "Paketda yuvilgan holda saqlash", "Muzxonaga solib qo‘yish"],
            "correct_index": 0,
            "explanation": "Ortiqcha namlik barglarning tez chirishiga sabab bo‘ladi.",
        },
    },
]

print("Tizim chiqaradigan postlar namunasi\n" + "=" * 60)
all_ok = True
for i, s in enumerate(SAMPLES, 1):
    ok, probs = quality.check_post(s)
    all_ok &= ok
    final = quality.ensure_footer(s["post_text"])
    print(f"\n───────── NAMUNA {i} ─────────")
    print(final)
    q = s["quiz"]
    print(f"\n  [6 soatdan keyin poll]")
    print(f"  ❓ {q['question']}")
    for j, o in enumerate(q["options"]):
        print(f"     {'✅' if j == q['correct_index'] else '▫️'} {o}")
    print(f"\n  Sifat nazorati: {'✅ PASS' if ok else '❌ FAIL ' + str(probs)}"
          f"  |  uzunlik: {len(final)} belgi")

print("\n" + "=" * 60)
print("✅ Barcha namunalar sifat nazoratidan o'tdi" if all_ok else "❌ Xato bor")
sys.exit(0 if all_ok else 1)
