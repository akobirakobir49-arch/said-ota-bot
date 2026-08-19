"""Markaziy konfiguratsiya. Sozlamalarni shu yerdan o'zgartiring."""
import os
from zoneinfo import ZoneInfo

# ---------- Maxfiy kalitlar (GitHub Secrets orqali keladi) ----------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
CHANNEL_ID = os.environ.get("CHANNEL_ID", "@Said_Ota_Market").strip()
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "748753861").strip()

# ---------- Kanal ma'lumotlari ----------
CHANNEL_NAME = "Said Ota Market"
CHANNEL_LINK = "https://t.me/Said_Ota_Market"

# ---------- Post oxiridagi footer (CTA + havolalar + telefonlar) ----------
FOOTER_DIVIDER = "➖➖➖➖➖➖➖➖➖"

# Obunaga undovchi chaqiruv. Bo'sh qoldirsangiz — chiqarilmaydi.
CTA_TEXT = "📌 Foydali bo'ldimi? Bizga obuna bo'ling 👇"

# Ijtimoiy tarmoqlar: (emoji, ko'rinadigan nom, havola).
# Nomning o'zi bosiladigan havola bo'ladi. Havolasi bo'sh bo'lganlari chiqarilmaydi.
SOCIAL_LINKS = [
    ("📸", "Instagram", "https://www.instagram.com/said_ota_market"),
    ("✈️", "Telegram", "https://t.me/Said_Ota_Market"),
    ("▶️", "YouTube", "https://youtube.com/@saidotamarket"),
]
SOCIAL_SEPARATOR = " | "

# Aloqa telefonlari (Telegram ularni o'zi bosiladigan qiladi). Bo'sh ro'yxat = chiqmaydi.
PHONE_EMOJI = "☎️"
PHONE_NUMBERS = [
    "+998701203000",
    "+998957761929",
]

# ---------- Vaqt ----------
TZ = ZoneInfo("Asia/Tashkent")

# ---------- Preview / tasdiq oqimi ----------
# Post chiqishidan necha daqiqa oldin adminga preview yuboriladi
PREVIEW_LEAD_MINUTES = 30
# "Qayta qilish" bosilgandan keyin yangi preview uchun necha daqiqa kutiladi
REGEN_WAIT_MINUTES = 12
# Maksimal necha marta qayta generatsiya qilish mumkin
MAX_REGENERATIONS = 3

# ---------- Gemini modellari ----------
# "auto" = tizim Google'dan mavjud modellar ro'yxatini so'rab, eng mosini o'zi tanlaydi.
# Aniq model nomini yozsangiz (masalan "gemini-3.6-flash"), aynan o'sha ishlatiladi.
TEXT_MODEL = "auto"
IMAGE_MODEL = "auto"

GEMINI_API = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_BASE = GEMINI_API + "/models"
GEMINI_INTERACTIONS = GEMINI_API + "/interactions"

# Avtomatik tanlashda ustuvorlik tartibi (yuqoridagisi birinchi sinaladi).
# Ro'yxatdagilarning hech biri mavjud bo'lmasa, tizim mos keladigan boshqasini topadi.
TEXT_MODEL_PREFERENCE = [
    "gemini-3.6-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3-flash",
    "gemini-2.5-flash",
]
IMAGE_MODEL_PREFERENCE = [
    "gemini-3.1-flash-image",
    "gemini-3.1-flash-lite-image",
    "gemini-3-pro-image",
    "gemini-2.5-flash-image",
]

# Gemini 3 modellari javob berishdan oldin "o'ylaydi" va o'ylash ham token sarflaydi.
# "minimal" | "low" | "medium" | "high" | None (o'chirish).
# Model bu parametrni qo'llamasa, tizim uni avtomatik olib tashlaydi.
THINKING_LEVEL = "low"

# Javob uchun token chegaralari. O'ylash tokenlari ham shu hisobga kirgani uchun
# katta qo'yilgan — aks holda JSON javob yarmida uzilib qoladi.
MAX_TOKENS_RESEARCH = 32768
MAX_TOKENS_WRITE = 16384
MAX_TOKENS_QC = 8192
JSON_RETRY_ATTEMPTS = 3      # JSON buzilsa necha marta qayta so'raladi

# ---------- Sifat nazorati chegaralari ----------
MIN_POST_CHARS = 300          # kanal uslubidagi postlar medianasi ~465 belgi
MAX_POST_CHARS = 850          # Telegram rasm izohi (caption) limiti = 1024
MAX_CONTENT_ATTEMPTS = 3      # sifat nazoratidan o'tmasa qayta yozish soni

# Rubrikaga qarab uzunlik chegarasi: (minimum, maksimum) ko'rinadigan belgilar
RUBRIC_LENGTH = {
    "useful": (300, 850),
    "facts": (280, 700),
}

# ---------- Fayl yo'llari ----------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
PENDING_DIR = os.path.join(DATA_DIR, "pending")

# ---------- Rubrikalar ----------
# Qaysi slotda qaysi rubrika chiqishi. Almashtirmoqchi bo'lsangiz shu yerni o'zgartiring.
SLOT_RUBRIC = {
    "morning": "useful",   # 09:00 — Foydali ma'lumotlar
    "evening": "facts",    # 17:00 — Qiziqarli faktlar ("Bilarmidingiz?")
}
RUBRIC_NAMES = {
    "useful": "Foydali ma'lumotlar",
    "facts": "Qiziqarli faktlar",
}

# ---------- Mahsulot kategoriyalari (ikkala rubrika uchun ham) ----------
# Agent har safar shu ro'yxatdan (yaqinda ishlatilmaganidan) bittasini tanlaydi
CATEGORIES = [
    "Mevalar (mavsumiy va import)",
    "Quruq mevalar va yong'oqlar",
    "Mol go'shti",
    "Tovuq go'shti va parranda",
    "Qo'y go'shti",
    "Baliq va dengiz mahsulotlari",
    "Sabzavotlar va ko'katlar",
    "Sut mahsulotlari (sut, qatiq, tvorog, pishloq)",
    "Tuxum",
    "Yormalar va dukkaklilar (guruch, grechka, no'xat, loviya)",
    "Un va non mahsulotlari",
    "Yog'lar (paxta, kungaboqar, zaytun, sariyog')",
    "Asal va tabiiy shirinliklar",
    "Ziravorlar va kraviy o'tlar",
    "Choy va ichimliklar",
    "Konservalar va tayyor mahsulotlar",
    "Muzlatilgan mahsulotlar",
    "Bolalar oziq-ovqati (mahsulot tanlash va saqlash)",
    "Mahsulotlarni to'g'ri saqlash va muddatlar",
    "Oziq-ovqat xavfsizligi va sifatini tanlash",
]

# Kategoriya chiqish ehtimoli. Yozilmagani = 1.0 (oddiy).
# Kichik son = kamroq chiqadi. Masalan 0.15 ≈ 7 barobar kam.
CATEGORY_WEIGHTS = {
    "Bolalar oziq-ovqati (mahsulot tanlash va saqlash)": 0.15,
}

# ---------- Rasm uslubi ----------
IMAGE_STYLE = (
    "Professional food photography, natural daylight, shallow depth of field, "
    "clean rustic wooden or marble surface, fresh appetizing produce, "
    "warm and inviting supermarket atmosphere, high resolution, "
    "no text, no letters, no words, no watermark, no logo, no people's faces"
)


def validate() -> None:
    """Kerakli kalitlar borligini tekshiradi."""
    missing = []
    if not TELEGRAM_TOKEN:
        missing.append("TELEGRAM_TOKEN")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not CHANNEL_ID:
        missing.append("CHANNEL_ID")
    if not ADMIN_CHAT_ID:
        missing.append("ADMIN_CHAT_ID")
    if missing:
        raise SystemExit(
            "XATO: quyidagi GitHub Secrets to'ldirilmagan: " + ", ".join(missing)
        )
