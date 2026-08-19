# Post uslubi — qayerdan olingan va qanday qoidalarga aylantirildi

Uslub buyurtmachi yuborgan Telegram eksportidan (956 xabar, shundan **551 tasi matnli**)
avtomatik tahlil qilib chiqarildi.

## O'lchangan ko'rsatkichlar

| Ko'rsatkich | Qiymat |
|---|---|
| Post uzunligi (median) | **465 belgi** |
| Emoji bilan boshlanuvchi qatorlar | **44%** (868 / 1987 qator) |
| Emoji bilan boshlanuvchi postlar | 138 / 320 |
| Qalin (bold) matn ishlatilgan postlar | 111 / 320 |
| Savol bor postlar | 36% |
| 👇 ko'rsatkichi | 125 / 320 |
| Ajratuvchi chiziq (➖➖➖) + footer | 46 / 320 |
| Eng ko'p emojilar | ✅ 👇 🔥 🚀 ⚡ 🎬 📩 ❗ 📌 🤔 💬 |

## Ajratib olingan shablon

```
[emoji] <b>Jasur/kutilmagan sarlavha</b>

[emoji] Kirish — kontekst, 1-2 qisqa jumla.

[emoji] Fakt, asosiy raqam <b>qalin</b> qilingan.

[emoji] Yana bir fakt yoki tafsilot.

[emoji] Amaliy jihat / xulosa.

🤔 <b>Auditoriyaga savol?</b>

➖➖➖➖➖➖➖➖➖
🛒 <b>Said Ota Market</b> — sifat va ishonch
```

**Asosiy tamoyillar:**

1. Har bir abzas yangi qatordan boshlanadi va **o'z, takrorlanmaydigan** emojisi bor.
2. Abzaslar qisqa — 1-2 jumla, bitta fikr. Abzaslar orasida bo'sh qator.
3. Raqamlar va kalit so'zlar `<b>` bilan urg'ulanadi.
4. Post oxirida doim auditoriyaga savol (🤔 yoki 💬) — kommentariyaga chorlash uchun.
5. Emoji abzas **boshida** turadi, matn ichida emas.
6. Hashtag ishlatilmaydi (manba kanalda ham deyarli yo'q).
7. Tipografik apostrof: `o‘`, `g‘`.

## Manba uslubidan olinmagan narsalar (supermarket kanaliga mos emas)

- Narx va chegirma bloklari (`💳 Narxlar: ...`) — tizimda **taqiqlangan**
- 🔥/👍 reaksiya ovoz berish chaqiruvi — hozircha ishlatilmaydi
- `👇` + havola bloklari — post ichida tashqi havola yo'q

## Bu qoidalar qayerda yozilgan

| Nima | Fayl |
|---|---|
| Uslub ko'rsatmasi + 2 ta namuna post | `src/prompts.py` → `STYLE_GUIDE` |
| Uslubni majburlash (avtomatik tekshiruv) | `src/quality.py` → `check_post()` |
| AI-muharrir mezonlari | `src/prompts.py` → `QC_PROMPT`, 4-band |
| Footer | `src/config.py` → `POST_FOOTER` |

Uslubni o'zgartirmoqchi bo'lsangiz — `STYLE_GUIDE` va `check_post()` ni **birga**
yangilang, aks holda sifat nazorati postni rad etaveradi.
