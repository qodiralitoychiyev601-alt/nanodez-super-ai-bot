# NANODEZ Super AI Bot

Professional Telegram bot dezinfeksiya/dezinseksiya xizmatlarining buyurtmalarini qabul qilish uchun.

## Features

✅ 9-bosqichli professional buyurtma berish
✅ Google Gemini AI - hasharotlar haqida savol-javob
✅ PDF shartnoma generation (Kirill harflari, QR-kod)
✅ Operator guruhi bilan integratsiya
✅ Order tracking (SQLite)
✅ Multi-language support (Uzbek)

## Installation

```bash
pip install -r requirements.txt
python bot.py
```

## Configuration

- Bot Token: Environment variable `BOT_TOKEN`
- Group Chat ID: Environment variable `GROUP_CHAT_ID`
- Gemini API Key: Environment variable `GEMINI_API_KEY`

## Deploy to Railway

1. GitHub'ga push qiling
2. Railway.app da yangi project yarating
3. GitHub repo ulab, deploy qiling
4. Environment variables qo'shing

## Bot Commands

- `/start` - Botni boshlash
- `/holat <order_id> <status>` - Buyurtma holatini yangilash (operator)
- `/yakunlash <order_id> <summa> <kafolat>` - Buyurtmani yakunlash (operator)

## Menu

- 📝 Buyurtma berish - 9-bosqichli FSM
- ℹ️ Biz haqimizda - Kompaniya ma'lumoti + ijtimoiy tarmoqlar
- 🛡 Kafolat - Kafolat shartlari
- 📦 Buyurtmam holati - Order tracking
- 🤖 NANODEZ AI - Gemini AI (hasharotlar haqida)

## Author

NANODEZ - Dezinfeksiya va dezinseksiya xizmatları
