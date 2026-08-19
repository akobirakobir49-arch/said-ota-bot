"""Sozlamalarni tekshirish: bot, kanal, admin ID va Gemini kalitini sinaydi."""
import logging
import os
import sys

import config
import gemini_api
import telegram_api as tg

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("check")

ok_all = True


def step(name: str, fn):
    global ok_all
    print(f"\n=== {name} ===")
    try:
        fn()
        print("✅ OK")
    except Exception as e:  # noqa: BLE001
        ok_all = False
        print(f"❌ XATO: {e}")


def check_token():
    if not config.TELEGRAM_TOKEN:
        raise RuntimeError("TELEGRAM_TOKEN secret to'ldirilmagan.")
    me = tg.call("getMe")
    print(f"Bot: @{me.get('username')} (id={me.get('id')})")


def check_channel():
    if not config.CHANNEL_ID:
        raise RuntimeError("CHANNEL_ID secret to'ldirilmagan.")
    chat = tg.call("getChat", {"chat_id": config.CHANNEL_ID})
    print(f"Kanal: {chat.get('title')} (id={chat.get('id')}, turi={chat.get('type')})")
    me = tg.call("getMe")
    member = tg.call("getChatMember", {"chat_id": config.CHANNEL_ID, "user_id": me["id"]})
    status = member.get("status")
    print(f"Botning kanaldagi maqomi: {status}")
    if status != "administrator":
        raise RuntimeError("Bot kanalda ADMIN emas! Kanal sozlamalaridan admin qiling.")
    if not member.get("can_post_messages", True):
        raise RuntimeError("Botda 'Post yuborish' huquqi yo'q.")


def check_admin():
    if not config.ADMIN_CHAT_ID:
        updates = tg.call("getUpdates", {"timeout": 0}, raise_on_error=False) or []
        found = {}
        for u in updates:
            chat = (u.get("message") or u.get("edited_message") or {}).get("chat")
            if chat:
                found[str(chat.get("id"))] = chat.get("username") or chat.get("first_name")
        raise RuntimeError(
            "ADMIN_CHAT_ID to'ldirilmagan. Botingizga Telegramda /start yozing va shu "
            "tekshiruvni qayta ishga tushiring — ID shu yerda ko'rinadi. "
            f"Hozircha topilgan chatlar: {found or 'yo`q'}"
        )
    tg.send_message(config.ADMIN_CHAT_ID,
                    "🔧 <b>Tekshiruv</b>: bot siz bilan bog'lana oldi. Hammasi joyida ✅")
    print(f"Adminga ({config.ADMIN_CHAT_ID}) test xabari yuborildi.")


def check_gemini_models():
    if not config.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY secret to'ldirilmagan.")
    models = sorted(gemini_api._short(m.get("name", "")) for m in gemini_api.list_models())
    print(f"Kalit uchun mavjud modellar ({len(models)} ta):")
    for m in models:
        print("   ", m)
    print("\n➡️  Tanlangan MATN modeli :", gemini_api.text_model())
    print("➡️  Tanlangan RASM modeli :", gemini_api.image_model())


def check_gemini_text():
    resp = gemini_api._post(gemini_api.text_model(), {
        "contents": [{"role": "user", "parts": [{"text": "Javob sifatida faqat 'ishladi' deb yoz."}]}],
        "generationConfig": {"maxOutputTokens": 20},
    })
    print("Matn modeli javobi:", gemini_api._collect_text(resp)[:100])


def check_gemini_search():
    resp = gemini_api._post(gemini_api.text_model(), {
        "contents": [{"role": "user", "parts": [{"text": "Bugun O'zbekistonda qaysi mevalar mavsumda? Qisqa javob."}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"maxOutputTokens": 300},
    })
    print("Google Search grounding javobi:", gemini_api._collect_text(resp)[:200])


def check_gemini_image():
    img = gemini_api.generate_image("A bowl of fresh red apples on a wooden table")
    if not img:
        raise RuntimeError(
            "Rasm generatsiya qilinmadi. Gemini kaliti 'Paid tier' emasligi mumkin "
            "(gemini-2.5-flash-image bepul tarifda ishlamaydi)."
        )
    print(f"Rasm olindi: {len(img)} bayt")
    os.makedirs("data", exist_ok=True)
    with open("data/_test_image.png", "wb") as f:
        f.write(img)
    if config.ADMIN_CHAT_ID:
        tg.send_photo(config.ADMIN_CHAT_ID, img, "🖼 Test rasmi — Gemini rasm generatsiyasi ishlayapti.")


if __name__ == "__main__":
    step("1. Telegram bot tokeni", check_token)
    step("2. Kanal va bot huquqlari", check_channel)
    step("3. Admin bilan aloqa", check_admin)
    step("4. Gemini modellari ro'yxati", check_gemini_models)
    step("5. Gemini matn modeli", check_gemini_text)
    step("6. Gemini Google Search", check_gemini_search)
    step("7. Gemini rasm generatsiyasi (nanobanana)", check_gemini_image)

    print("\n" + "=" * 40)
    print("✅ BARCHA TEKSHIRUVLAR MUVAFFAQIYATLI" if ok_all else "❌ BA'ZI TEKSHIRUVLAR XATO BERDI")
    sys.exit(0 if ok_all else 1)
