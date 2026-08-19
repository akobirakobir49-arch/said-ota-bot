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

# Har bir post oxiriga qo'shiladigan footer (kanal uslubidagi ajratuvchi chiziq bilan).
# O'chirish uchun bo'sh qator ("") qiling.
POST_FOOTER = "➖➖➖➖➖➖➖➖➖\n🛒 <b>Said Ota Market</b> — sifat va ishonch"

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

# ---------- Sifat nazorati chegaralari ----------
MIN_POST_CHARS = 300          # kanal uslubidagi postlar medianasi ~465 belgi
MAX_POST_CHARS = 850          # Telegram rasm izohi (caption) limiti = 1024
MAX_CONTENT_ATTEMPTS = 3      # sifat nazoratidan o'tmasa qayta yozish soni

# ---------- Fayl yo'llari ----------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
PENDING_DIR = os.path.join(DATA_DIR, "pending")

# ---------- Rubrika: mahsulot kategoriyalari ----------
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
    "Bolalar oziq-ovqati",
    "Mahsulotlarni to'g'ri saqlash va muddatlar",
    "Oziq-ovqat xavfsizligi va sifatini tanlash",
]

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
