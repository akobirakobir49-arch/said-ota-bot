# Said Ota Market — avtomatik Telegram kontent tizimi

Kuniga 2 ta "Foydali ma'lumotlar" posti + har biriga test savoli. To'liq avtomatik,
GitHub Actions'da ishlaydi, server kerak emas.

---

## Qanday ishlaydi

| Vaqt (Toshkent) | Nima bo'ladi |
|---|---|
| **08:15** | Agent internetdan mavzu qidiradi → post yozadi → rasm chizadi → sifat nazoratidan o'tkazadi → sizga **preview** yuboradi |
| **08:15–09:00** | Siz **🔄 Qayta qilish** tugmasini bosishingiz mumkin. Bossangiz — hammasi qaytadan tayyorlanadi va yangi preview keladi (12 daqiqa kutiladi, max 3 marta) |
| **09:00** | Hech narsa bosmasangiz — post kanalga chiqadi. Qayta qilingan bo'lsa, vaqt o'tgan bo'lsa ham chiqadi |
| **15:00** | Ertalabki post bo'yicha **test savoli** (poll) kanalga chiqadi |
| **16:15** | Kechqurungi post uchun xuddi shu jarayon |
| **17:00** | Kechqurungi post kanalga chiqadi |
| **20:00** | Kechqurungi post bo'yicha test savoli chiqadi |

### Sifat nazorati 2 bosqichli
1. **Dasturiy tekshiruv** — uzunlik, HTML teglar, struktura (sarlavha/faktlar/maslahat/hashtag),
   narx yo'qligi, tibbiy da'volar yo'qligi, quiz to'g'riligi.
2. **AI-muharrir** — fakt aniqligi, til sifati, xavfsizlik, qiziqarlilik bo'yicha 0–100 ball.
   80 dan past bo'lsa post avtomatik qayta yoziladi (3 martagacha).

---

## O'rnatish (10 daqiqa)

### 1-qadam. Botni kanalga admin qiling
1. Telegramda **@Said_Ota_Market** kanalini oching
2. `Kanal nomi` → `Administrators` → `Add Administrator`
3. Botingizni qidirib qo'shing
4. **"Post Messages"** (Xabar yuborish) huquqini yoqing ✅

### 2-qadam. O'z Telegram ID'ingizni oling
Botingizga Telegramda `/start` deb yozing, keyin @userinfobot ga `/start` yozing —
u sizga `Id: 123456789` ko'rinishida raqam beradi. Shu raqam kerak.

> ⚠️ Botga **hech bo'lmasa bir marta** `/start` yozishingiz shart — aks holda bot sizga
> preview yubora olmaydi (Telegram qoidasi).

### 3-qadam. GitHub repo yarating
1. github.com → `New repository` → nom: `said-ota-bot` → **Private** → Create
2. Shu papkadagi barcha fayllarni repoga yuklang
   (`Add file` → `Upload files` → papkani sudrab tashlang → Commit)

### 4-qadam. Secrets kiriting
Repo → `Settings` → `Secrets and variables` → `Actions` → `New repository secret`.
4 ta secret qo'shing:

| Nomi | Qiymati |
|---|---|
| `TELEGRAM_TOKEN` | Bot tokeni (BotFather bergan) |
| `CHANNEL_ID` | `@Said_Ota_Market` |
| `ADMIN_CHAT_ID` | 2-qadamda olgan raqamingiz |
| `GEMINI_API_KEY` | Gemini API kaliti |

### 5-qadam. Actions'ga yozish huquqini bering
Repo → `Settings` → `Actions` → `General` → pastda **Workflow permissions** →
**"Read and write permissions"** ni tanlang → `Save`.

### 6-qadam. Tekshiring
Repo → `Actions` → **"Sozlamalarni tekshirish"** → `Run workflow`.

6 ta tekshiruv o'tadi. Hammasi ✅ bo'lsa — tizim tayyor. Telegramda test xabari va
test rasmi keladi.

### 7-qadam. Sinov posti
`Actions` → **"Kanalga post chiqarish"** → `Run workflow` →
`Sinov rejimi` = **true** → Run.

Bu kanalga hech narsa chiqarmaydi, faqat sizga preview yuboradi. Yoqsa —
`Sinov rejimi` = false bilan qayta ishga tushiring.

Shundan keyin tizim har kuni o'zi ishlaydi.

---

## Sozlash

| Nima o'zgartirmoqchisiz | Qaysi fayl |
|---|---|
| **Post stili, tuzilishi, uzunligi** | `src/prompts.py` → `STYLE_GUIDE` |
| Mahsulot kategoriyalari ro'yxati | `src/config.py` → `CATEGORIES` |
| Rasm uslubi | `src/config.py` → `IMAGE_STYLE` |
| Post oxiridagi footer | `src/config.py` → `POST_FOOTER` |
| Preview necha daqiqa oldin kelishi | `src/config.py` → `PREVIEW_LEAD_MINUTES` |
| "Qayta qilish"dan keyin kutish vaqti | `src/config.py` → `REGEN_WAIT_MINUTES` |
| **Chiqish vaqtlari** | `.github/workflows/post.yml` va `poll.yml` → `cron` |

> Cron vaqtlari **UTC** da. Toshkent vaqtidan **5 soat ayiring**.
> Masalan 09:00 Toshkent = `0 4 * * *` UTC.

---

## Muhim eslatmalar

**⏰ Kechikish.** GitHub Actions cron'i ba'zan 5–15 daqiqa kechikadi. Shuning uchun ish
08:15 da boshlanadi, lekin post aynan 09:00 da chiqadi — skript vaqtni o'zi kutadi.
Agar GitHub 45 daqiqadan ko'p kechiktirsa, post kechikib chiqadi.

**💳 Gemini tarifi.** `gemini-2.5-flash-image` (nanobanana) **bepul tarifda ishlamaydi**.
Google AI Studio'da billing yoqilgan bo'lishi kerak. Rasm chiqmasa — post matn holida
chiqadi va sizga ogohlantirish keladi.

**💰 Taxminiy xarajat.** Kuniga 2 post ≈ 2 ta rasm + ~10 ta matn so'rovi.
Oyiga taxminan **$3–6** atrofida.

**🔁 Takrorlanmaslik.** Chiqqan mavzular `data/history.json` ga yoziladi va keyingi
postlarda takrorlanmaydi. Oxirgi 8 ta postda ishlatilgan kategoriya qayta tanlanmaydi.

**❌ Xatolar.** Biror bosqichda xato bo'lsa, sizga Telegramda xabar keladi.
Batafsil log: repo → `Actions` → kerakli ishni oching.

---

## Fayllar

```
src/config.py        — sozlamalar, kategoriyalar, chegaralar
src/prompts.py       — barcha AI promptlari (STIL SHU YERDA)
src/gemini_api.py    — mavzu qidirish, matn yozish, rasm generatsiya
src/telegram_api.py  — Telegram bilan ishlash, tugma, poll
src/quality.py       — dasturiy sifat tekshiruvlari
src/history.py       — mavzular tarixi va poll navbati
src/publish.py       — asosiy oqim
src/send_poll.py     — test savolini yuborish
src/check.py         — sozlamalarni tekshirish
data/history.json    — chiqqan mavzular arxivi
data/pending/        — poll kutayotgan postlar
```
