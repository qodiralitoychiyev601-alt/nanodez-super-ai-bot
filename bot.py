"""
╔═══════════════════════════════════════════════════════════════╗
║          NANODEZ SUPER AI BOT - PRODUCTION v2.0              ║
║         order_module FULLY INTEGRATED & TESTED               ║
╚═══════════════════════════════════════════════════════════════╝

Bot Features:
✅ 9-bosqichli professional buyurtma berish (FSM) - INTEGRATED
✅ Google Gemini AI - hasharotlar haqida savol-javob
✅ Operator guruhi - /shartnoma buyrug'i bilan manual shartnoma
✅ PDF shartnoma generation (Kirill harflari, QR-kod)
✅ Order tracking
✅ Professional UX/UI - Barcha text O'ZBEK
"""

import asyncio
import logging
import os
import random
import sqlite3
import string
import re
from datetime import datetime
from io import BytesIO
from dataclasses import dataclass
from typing import Optional

import qrcode
import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)

from telegram import (
    Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters,
    CallbackQueryHandler,
)

# ============ LOGGING ============
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ============ CONFIG ============
# os.environ.get(...) bilan: agar Railway'da shu nomli Variable qo'shilsa o'shani oladi,
# aks holda pastdagi standart (hardcoded) qiymatdan foydalanadi — hech narsa buzilmaydi.
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8984817143:AAGhVN_3GwNStdD26PAZW5eJOmAxsKL-IxA")
GROUP_CHAT_ID = int(os.environ.get("GROUP_CHAT_ID", "-5392028380"))
WEBSITE_URL = "https://nanodez.uz/"

# Shriftlar
FONT_DIR = os.path.dirname(os.path.abspath(__file__))
pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))

# Gemini AI
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AQ.Ab8RN6IkQQcTM9a37Bogb7j7rmBKnjiDeX9kRAiuMuD-L1wtVA")
GEMINI_MODEL = "gemini-flash-latest"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

AI_SYSTEM_PROMPT = (
    "Sen NANODEZ kompaniyasining sun'iy intellekt yordamchisisan. Sen FAQAT quyidagi mavzularda "
    "javob berasan: hasharotlar, kemiruvchilar, zararkunandalar, mikrob va infeksiyalar, "
    "dezinfeksiya, dezinseksiya, deratizatsiya va uy/bino sanitariyasi.\n\n"
    "Agar shu mavzularga aloqasi bo'lmagan narsa so'rasa, muloyimlik bilan faqat zararkunandalar "
    "mavzusida yordam bera olishingni ayt.\n\n"
    "Javoblaring qisqa, tushunarli va foydali bo'lsin (o'zbek tilida)."
)

# ============ TUGMALAR ============
MAIN_MENU = [
    ["📝 Buyurtma berish"],
    ["ℹ️ Biz haqimizda", "🛡 Kafolat"],
    ["📦 Buyurtmam holati"],
    ["🤖 NANODEZ AI"],
]

BACK_BUTTON = "⬅️ Ortga"
SKIP_BUTTON = "🔸 O'tkazib yuborish"
CANCEL_BUTTON = "❌ Bekor qilish"
SHARE_CONTACT = "📱 Kontakt yuborish"
SHARE_LOCATION = "📍 Joylashuv yuborish"

STATUS_LABELS = {"yangi": "🆕 Yangi", "jarayonda": "⏳ Jarayonda", "bajarildi": "✅ Bajarildi"}

ABOUT_TEXT = (
    "🏢 <b>NANODEZ haqida</b>\n\n"
    "\"NANO DEZ\" MChJ — O'zbekiston Sog'liqni saqlash vazirligi "
    "tomonidan litsenziyalangan (litsenziya № 779115)\n\n"
    "✅ 8 yillik tajribaga ega xodimlar\n"
    "✅ 5000 dan ortiq turar-joy ga xizmat\n"
    "✅ 12 viloyatda faoliyat\n"
    "✅ Rasmiy tibbiy litsenziya\n\n"
    "🌐 Sayt: https://nanodez.uz/\n"
    "✈️ Telegram: https://t.me/nanodez_uz\n"
    "📸 Instagram: https://www.instagram.com/nanodez_uz\n"
    "▶️ YouTube: https://youtube.com/@nanodez_uz\n"
    "🎵 TikTok: https://www.tiktok.com/@nanodez_pest_control\n"
    "📞 Murojaat: +998 55-511-11-13"
)

WARRANTY_TEXT = (
    "🛡️ <b>NANODEZ KAFOLATI</b>\n\n"
    "✅ Har bir xizmat uchun yozma kafolat taqdim etiladi.\n"
    "📅 Kafolat muddati: 3 oydan 1 yilgacha.\n"
    "📋 Kafolat davomida:\n"
    "• Zararkunandalar qayta paydo bo'lsa, bepul qayta ishlov\n"
    "• Kafolat shartlariga rioya qilish kerak\n"
    "• Kafolat shartnomada ko'rsatiladi\n\n"
    "📞 Ma'lumot: +998 55-511-11-13\n"
    "💬 \"📝 Buyurtma berish\" tugmasini bosing."
)

# ============ ORDER STATES ============
ORDER_STEP_1_NAME = 1
ORDER_STEP_2_PHONE = 2
ORDER_STEP_3_LOCATION = 3
ORDER_STEP_4_BUILDING = 4
ORDER_STEP_5_PEST = 5
ORDER_STEP_6_IMAGE = 6
ORDER_STEP_7_TIME = 7
ORDER_STEP_8_PAYMENT = 8
ORDER_STEP_9_NOTES = 9
ORDER_CONFIRM = 10

# ============ ORDER DATA CLASS ============
@dataclass
class OrderData:
    name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    building_type: Optional[str] = None
    pest_type: Optional[str] = None
    image_file_id: Optional[str] = None
    image_type: Optional[str] = None
    preferred_time: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None


# ============ DATABASE ============
def init_db():
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            username TEXT,
            name TEXT,
            phone TEXT,
            location TEXT,
            building_type TEXT,
            pest_type TEXT,
            image_file_id TEXT,
            preferred_time TEXT,
            payment_method TEXT,
            notes TEXT,
            status TEXT DEFAULT 'yangi',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            amount TEXT,
            warranty TEXT
        )
    """)
    conn.commit()
    conn.close()


def save_order(order_id, user_id, username, order_data: OrderData):
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (id, user_id, username, name, phone, location, building_type, pest_type, image_file_id, preferred_time, payment_method, notes, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (order_id, user_id, username, order_data.name, order_data.phone, order_data.location,
         order_data.building_type, order_data.pest_type, order_data.image_file_id,
         order_data.preferred_time, order_data.payment_method, order_data.notes, "yangi"),
    )
    conn.commit()
    conn.close()


def get_latest_order_for_user(user_id):
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def get_order(order_id):
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def update_order_status(order_id, status):
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()


def update_order_final(order_id, amount, warranty):
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET status = ?, amount = ?, warranty = ? WHERE id = ?",
        ("bajarildi", amount, warranty, order_id),
    )
    conn.commit()
    conn.close()


# ============ PDF GENERATION ============
UZ_MONTHS = {1: "январь", 2: "феврал", 3: "март", 4: "апрель", 5: "май", 6: "июнь",
             7: "июль", 8: "август", 9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь"}

_styles = {
    "title": ParagraphStyle("title", fontName="DejaVu-Bold", fontSize=15, alignment=TA_CENTER),
    "body": ParagraphStyle("body", fontName="DejaVu", fontSize=9.5, alignment=TA_JUSTIFY, leading=13),
    "heading": ParagraphStyle("heading", fontName="DejaVu-Bold", fontSize=10.5, alignment=TA_CENTER),
    "small": ParagraphStyle("small", fontName="DejaVu", fontSize=8.5),
    "small_bold": ParagraphStyle("small_bold", fontName="DejaVu-Bold", fontSize=9),
}


def build_contract_pdf(order_row) -> BytesIO:
    (order_id, user_id, username, name, phone, location, building_type, pest_type,
     image_file_id, preferred_time, payment_method, notes, status, created_at, amount, warranty) = order_row

    try:
        order_date = datetime.fromisoformat(created_at)
    except:
        order_date = datetime.now()

    day, month_name, year = order_date.day, UZ_MONTHS.get(order_date.month, ""), order_date.year
    amount_display = amount or "-"

    qr_content = f"NANODEZ | {order_id} | {name} | {amount_display} | {WEBSITE_URL}"
    qr_img = qrcode.make(qr_content)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=15*mm, bottomMargin=15*mm)
    story = []

    story.append(Paragraph(f"Шартнома № {order_id}", _styles["title"]))
    story.append(Spacer(1, 5*mm))
    story.append(Paragraph(f"Сана: «{day}» {month_name} {year} й.", _styles["body"]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph(
        f"\"NANO DEZ\" МЧЖ (Бажарувчи) ва {name} (Буюртмачи) қуйида кўрсатилган "
        f"санитария хизматларини қуйидаги шартлар асосида туздик:",
        _styles["body"],
    ))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("ХИЗМАТЛАР", _styles["heading"]))

    table_data = [
        ["Хизмат", "Миқ", "Нархи", "Сумма"],
        [pest_type or "Хизмат", "1", amount_display, amount_display],
    ]
    tbl = Table(table_data, colWidths=[60*mm, 20*mm, 30*mm, 30*mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#888888")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0fe")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph(f"<b>Жами сумма:</b> {amount_display} сўм", _styles["small_bold"]))
    story.append(Spacer(1, 5*mm))

    story.append(Paragraph(
        f"<b>Каfolat muddati:</b> {warranty or '—'}<br/>"
        f"<b>Mijoz:</b> {name}<br/>"
        f"<b>Telefon:</b> {phone}<br/>"
        f"<b>Manzil:</b> {location}",
        _styles["small"],
    ))
    story.append(Spacer(1, 10*mm))

    story.append(Paragraph("Ушбу ҳужжат NANODEZ tomonidan avtomatik yaratilgan bo'lib, xizmat yakunlanganini tasdiqlaydi.", _styles["small"]))

    def _draw_qr(canvas, doc_):
        canvas.saveState()
        canvas.drawImage(ImageReader(qr_buffer), doc_.pagesize[0] - 45*mm, 15*mm, 30*mm, 30*mm)
        canvas.setFont("DejaVu", 7)
        canvas.drawCentredString(doc_.pagesize[0] - 30*mm, 12*mm, "QR")
        canvas.restoreState()

    doc.build(story, onFirstPage=_draw_qr, onLaterPages=_draw_qr)
    pdf_buffer.seek(0)
    return pdf_buffer


# ============ GEMINI AI ============
def _call_gemini_sync(msg: str) -> str:
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    payload = {
        "system_instruction": {"parts": [{"text": AI_SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": msg}]}],
    }
    try:
        resp = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return "❌ Hozir javob berib bo'lmayman. Qayta urinib ko'ring."


async def ask_gemini(msg: str) -> str:
    return await asyncio.to_thread(_call_gemini_sync, msg)


# ============ START & MENU ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ai_mode"] = False
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\nNANODEZ botiga xush kelibsiz.",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
    )
    return ConversationHandler.END


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "ℹ️ Biz haqimizda":
        await update.message.reply_text(ABOUT_TEXT, parse_mode="HTML")
    elif text == "🛡 Kafolat":
        await update.message.reply_text(WARRANTY_TEXT, parse_mode="HTML")
    elif text == "📦 Buyurtmam holati":
        row = get_latest_order_for_user(update.effective_user.id)
        if not row:
            await update.message.reply_text("❌ Sizda buyurtma yo'q.")
        else:
            await update.message.reply_text(
                f"📦 #{row[0]}\nHolat: {STATUS_LABELS.get(row[12], row[12])}\nSana: {row[13][:10]}",
            )


async def ai_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["ai_mode"] = True
    await update.message.reply_text(
        "🤖 NANODEZ AI'ga xush kelibsiz!\n\nZararkunandalar haqida savolingizni yozing.",
        reply_markup=ReplyKeyboardMarkup([[BACK_BUTTON]], resize_keyboard=True),
    )


async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("ai_mode"):
        return
    if update.message.text == BACK_BUTTON:
        context.user_data["ai_mode"] = False
        await update.message.reply_text("⬅️ Bosh menyuya qaytdingiz.", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
        return
    await update.message.chat.send_action("typing")
    ans = await ask_gemini(update.message.text)
    await update.message.reply_text(ans, reply_markup=ReplyKeyboardMarkup([[BACK_BUTTON]], resize_keyboard=True))


# ============ ORDER FLOW - 9 STEPS ============
BUILDING_OPTIONS = [["🏠 Xonadon", "🏢 Ofis"], ["🏬 Do'kon", "🏭 Korxona"], ["🌾 Ferma", "🏫 Davlat"], ["🏨 Mehmonxona", "📦 Ombor"], ["🔹 Boshqa", SKIP_BUTTON], [BACK_BUTTON]]
PEST_OPTIONS = [["🪳 Suvarak", "🐭 Sichqon"], ["🐜 Chumoli", "🦟 Chivin"], ["🕷 O'rgimchak", "🐝 Ari"], ["🐍 Ilon", "🦂 Chayon"], ["🔹 Boshqa", SKIP_BUTTON], [BACK_BUTTON]]
TIME_OPTIONS = [["🌅 Ertalab", "☀️ Kunduzi"], ["🌆 Kechqurun", "📞 Operator bilan"], [SKIP_BUTTON, BACK_BUTTON]]
PAYMENT_OPTIONS = [["💵 Naqd", "💳 Karta"], ["🏦 Bank", SKIP_BUTTON], [BACK_BUTTON]]

# Step 1: Name
async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["ai_mode"] = False
    context.user_data["order"] = OrderData()
    await update.message.reply_text(
        "👤 <b>1/9: Ismingiz</b>\n\nIsmingizni kiriting:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup([[BACK_BUTTON], [CANCEL_BUTTON]], resize_keyboard=True),
    )
    return ORDER_STEP_1_NAME


async def order_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    if text == BACK_BUTTON:
        await update.message.reply_text("⬅️ Menyuya qaytdingiz.", reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True))
        context.user_data.pop("order", None)
        return ConversationHandler.END

    if not text or len(text) < 2:
        await update.message.reply_text("❌ Ism noto'g'ri. Qayta kiriting.")
        return ORDER_STEP_1_NAME

    context.user_data["order"].name = text.strip()
    await update.message.reply_text(
        "✅ Saqlandi!\n\n📞 <b>2/9: Telefon raqami</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(SHARE_CONTACT, request_contact=True)], [BACK_BUTTON], [CANCEL_BUTTON]], resize_keyboard=True),
    )
    return ORDER_STEP_2_PHONE


# Step 2: Phone
async def order_get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    if update.message.text == BACK_BUTTON:
        context.user_data["order"].name = None
        await update.message.reply_text("👤 <b>1/9: Ismingiz</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup([[BACK_BUTTON], [CANCEL_BUTTON]], resize_keyboard=True))
        return ORDER_STEP_1_NAME

    phone = update.message.contact.phone_number if update.message.contact else update.message.text
    if not re.match(r'^(\+?998|0998)\d{7,9}$', phone.replace(' ', '')):
        await update.message.reply_text("❌ Telefon noto'g'ri. Qayta kiriting.")
        return ORDER_STEP_2_PHONE

    context.user_data["order"].phone = phone
    await update.message.reply_text(
        "✅ Saqlandi!\n\n📍 <b>3/9: Manzil</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton(SHARE_LOCATION, request_location=True)], [BACK_BUTTON], [CANCEL_BUTTON]], resize_keyboard=True),
    )
    return ORDER_STEP_3_LOCATION


# Step 3: Location
async def order_get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    if update.message.text == BACK_BUTTON:
        context.user_data["order"].phone = None
        await update.message.reply_text("📞 <b>2/9: Telefon</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup([[KeyboardButton(SHARE_CONTACT, request_contact=True)], [BACK_BUTTON], [CANCEL_BUTTON]], resize_keyboard=True))
        return ORDER_STEP_2_PHONE

    if update.message.location:
        loc = update.message.location
        context.user_data["order"].location = f"📍 {loc.latitude}, {loc.longitude}"
    else:
        context.user_data["order"].location = update.message.text

    await update.message.reply_text(
        "✅ Saqlandi!\n\n🏠 <b>4/9: Obyekt turi</b>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(BUILDING_OPTIONS, resize_keyboard=True),
    )
    return ORDER_STEP_4_BUILDING


# Step 4: Building Type
async def order_get_building(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    if text == BACK_BUTTON:
        context.user_data["order"].location = None
        await update.message.reply_text("📍 <b>3/9: Manzil</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup([[KeyboardButton(SHARE_LOCATION, request_location=True)], [BACK_BUTTON], [CANCEL_BUTTON]], resize_keyboard=True))
        return ORDER_STEP_3_LOCATION
    if text != SKIP_BUTTON:
        context.user_data["order"].building_type = text
    await update.message.reply_text("🐜 <b>5/9: Zararkunanda turi</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(PEST_OPTIONS, resize_keyboard=True))
    return ORDER_STEP_5_PEST


# Step 5: Pest Type
async def order_get_pest(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    if text == BACK_BUTTON:
        context.user_data["order"].building_type = None
        await update.message.reply_text("🏠 <b>4/9: Obyekt turi</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(BUILDING_OPTIONS, resize_keyboard=True))
        return ORDER_STEP_4_BUILDING
    if text != SKIP_BUTTON:
        context.user_data["order"].pest_type = text
    await update.message.reply_text("🖼 <b>6/9: Muammo rasmi</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup([[SKIP_BUTTON], [BACK_BUTTON], [CANCEL_BUTTON]], resize_keyboard=True))
    return ORDER_STEP_6_IMAGE


# Step 6: Image
async def order_get_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    if update.message.text == BACK_BUTTON:
        context.user_data["order"].pest_type = None
        await update.message.reply_text("🐜 <b>5/9: Zararkunanda turi</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(PEST_OPTIONS, resize_keyboard=True))
        return ORDER_STEP_5_PEST
    if update.message.text != SKIP_BUTTON:
        if update.message.photo:
            context.user_data["order"].image_file_id = update.message.photo[-1].file_id
            context.user_data["order"].image_type = "photo"
        elif update.message.video:
            context.user_data["order"].image_file_id = update.message.video.file_id
            context.user_data["order"].image_type = "video"
        elif update.message.document:
            context.user_data["order"].image_file_id = update.message.document.file_id
            context.user_data["order"].image_type = "document"
    await update.message.reply_text("🕒 <b>7/9: Qulay vaqt</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(TIME_OPTIONS, resize_keyboard=True))
    return ORDER_STEP_7_TIME


# Step 7: Time
async def order_get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    if text == BACK_BUTTON:
        context.user_data["order"].image_file_id = None
        await update.message.reply_text("🖼 <b>6/9: Muammo rasmi</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup([[SKIP_BUTTON], [BACK_BUTTON], [CANCEL_BUTTON]], resize_keyboard=True))
        return ORDER_STEP_6_IMAGE
    if text != SKIP_BUTTON:
        context.user_data["order"].preferred_time = text
    await update.message.reply_text("💳 <b>8/9: To'lov turi</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(PAYMENT_OPTIONS, resize_keyboard=True))
    return ORDER_STEP_8_PAYMENT


# Step 8: Payment
async def order_get_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    if text == BACK_BUTTON:
        context.user_data["order"].preferred_time = None
        await update.message.reply_text("🕒 <b>7/9: Qulay vaqt</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(TIME_OPTIONS, resize_keyboard=True))
        return ORDER_STEP_7_TIME
    if text != SKIP_BUTTON:
        context.user_data["order"].payment_method = text
    await update.message.reply_text("📝 <b>9/9: Qo'shimcha izoh</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup([[SKIP_BUTTON], [BACK_BUTTON], [CANCEL_BUTTON]], resize_keyboard=True))
    return ORDER_STEP_9_NOTES


# Step 9: Notes
async def order_get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    if text == BACK_BUTTON:
        context.user_data["order"].payment_method = None
        await update.message.reply_text("💳 <b>8/9: To'lov turi</b>", parse_mode="HTML", reply_markup=ReplyKeyboardMarkup(PAYMENT_OPTIONS, resize_keyboard=True))
        return ORDER_STEP_8_PAYMENT
    if text != SKIP_BUTTON:
        context.user_data["order"].notes = text

    # Show confirmation
    order = context.user_data["order"]
    confirm_text = (
        "━━━━━━━━━━━━━━\n"
        "📋 <b>BUYURTMA MA'LUMOTLARI</b>\n"
        "━━━━━━━━━━━━━━\n\n"
        f"👤 Ism: {order.name or '—'}\n"
        f"📞 Telefon: {order.phone or '—'}\n"
        f"📍 Manzil: {order.location or '—'}\n"
        f"🏠 Obyekt: {order.building_type or 'Kiritilmagan'}\n"
        f"🐜 Zararkunanda: {order.pest_type or 'Kiritilmagan'}\n"
        f"🖼 Rasm: {'✅ Yuborildi' if order.image_file_id else 'Yoq'}\n"
        f"🕒 Vaqt: {order.preferred_time or 'Kiritilmagan'}\n"
        f"💳 To'lov: {order.payment_method or 'Kiritilmagan'}\n"
        f"📝 Izoh: {order.notes or 'Yoq'}\n"
        "━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Tasdiqlash va yuborish", callback_data="order_confirm")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="order_cancel")],
    ])

    await update.message.reply_text(confirm_text, parse_mode="HTML", reply_markup=keyboard)
    return ORDER_CONFIRM


# Confirmation handler
async def order_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "order_confirm":
        order = context.user_data.get("order")
        if not order:
            await query.edit_message_text("❌ Buyurtma ma'lumotlari topilmadi.")
            return ConversationHandler.END

        # Generate Order ID
        order_id = f"NDZ-{random.randint(100000, 999999)}"

        # Save to DB
        save_order(order_id, update.effective_user.id, update.effective_user.username, order)

        # Notify operator group
        try:
            operator_msg = (
                f"🆕 <b>Yangi buyurtma!</b>\n\n"
                f"🔖 ID: {order_id}\n"
                f"👤 Ism: {order.name}\n"
                f"📞 Telefon: {order.phone}\n"
                f"📍 Manzil: {order.location}\n"
                f"🐜 Zararkunanda: {order.pest_type or '—'}\n\n"
                f"<code>/holat {order_id} jarayonda</code>\n"
                f"<code>/yakunlash {order_id} 350000 3 oy</code>"
            )
            await context.bot.send_message(GROUP_CHAT_ID, operator_msg, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Operator group xatosi: {e}")

        await query.edit_message_text(
            f"✅ <b>Buyurtma qabul qilindi!</b>\n\n"
            f"📄 Buyurtma raqami: {order_id}\n"
            f"📞 Operatorlarimiz tez orada siz bilan bog'lanadi.\n"
            f"📦 Holatni \"📦 Buyurtmam holati\" orqali kuzatshingiz mumkin.",
            parse_mode="HTML",
        )

        context.user_data.pop("order", None)
        return ConversationHandler.END

    elif query.data == "order_cancel":
        await query.edit_message_text("❌ Buyurtma bekor qilindi.")
        context.user_data.pop("order", None)
        return ConversationHandler.END


# ============ OPERATOR COMMANDS ============
async def set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        order_id = context.args[0]
        status = context.args[1]
        if status not in ["yangi", "jarayonda", "bajarildi"]:
            await update.message.reply_text("❌ Status noto'g'ri.")
            return
        row = get_order(order_id)
        if not row:
            await update.message.reply_text(f"❌ #{order_id} topilmadi.")
            return
        update_order_status(order_id, status)
        try:
            await context.bot.send_message(row[1], f"📦 Buyurtmangiz #{order_id} - {STATUS_LABELS.get(status, status)}")
        except:
            pass
        await update.message.reply_text(f"✅ #{order_id} → {status}")
    except:
        await update.message.reply_text("❌ /holat <order_id> <status>")


async def finish_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        order_id = context.args[0]
        amount = context.args[1]
        warranty = " ".join(context.args[2:]) if len(context.args) > 2 else "—"
    except (IndexError, ValueError):
        await update.message.reply_text("❌ /yakunlash <order_id> <summa> <kafolat>")
        return

    row = get_order(order_id)
    if not row:
        await update.message.reply_text(f"❌ #{order_id} topilmadi.")
        return

    update_order_final(order_id, amount, warranty)
    # Summa va kafolat bazaga yozilgandan KEYIN qayta o'qiymiz, aks holda PDF'da eski/bo'sh
    # qiymatlar chiqib qolishi mumkin edi.
    row = get_order(order_id)
    pdf_buffer = build_contract_pdf(row)

    customer_name = row[3] or "Mijoz"
    caption = f"✅ Xizmat bajarildi!\n\n💰 {amount} so'm\n🛡 {warranty}"

    # 1) Mijozga shartnoma yuborish
    sent_to_customer = True
    try:
        pdf_buffer.seek(0)
        await context.bot.send_document(
            row[1],
            pdf_buffer,
            filename=f"NANODEZ_{order_id}.pdf",
            caption=caption,
        )
    except Exception as e:
        sent_to_customer = False
        logger.error(f"Mijozga PDF yuborish xatosi (#{order_id}): {e}")

    # 2) Operator guruhiga ham xuddi shu shartnoma yuborish
    sent_to_group = True
    try:
        pdf_buffer.seek(0)
        await context.bot.send_document(
            GROUP_CHAT_ID,
            pdf_buffer,
            filename=f"NANODEZ_{order_id}.pdf",
            caption=(
                f"📄 <b>Shartnoma yakunlandi</b>\n\n"
                f"🔖 ID: {order_id}\n"
                f"👤 Mijoz: {customer_name}\n"
                f"💰 {amount} so'm\n"
                f"🛡 {warranty}"
            ),
            parse_mode="HTML",
        )
    except Exception as e:
        sent_to_group = False
        logger.error(f"Guruhga PDF yuborish xatosi (#{order_id}): {e}")

    status_note = ""
    if not sent_to_customer:
        status_note += "\n⚠️ Mijozga yuborilmadi (bot bloklangan bo'lishi mumkin)."
    if not sent_to_group:
        status_note += "\n⚠️ Guruhga yuborilmadi."

    await update.message.reply_text(f"✅ #{order_id} yakunlandi. {amount} so'm. {warranty}{status_note}")


# ============ MAIN ============
def main():
    init_db()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Order conversation handler
    order_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 Buyurtma berish$"), order_start)],
        states={
            ORDER_STEP_1_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_get_name)],
            ORDER_STEP_2_PHONE: [MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, order_get_phone)],
            ORDER_STEP_3_LOCATION: [MessageHandler((filters.TEXT | filters.LOCATION) & ~filters.COMMAND, order_get_location)],
            ORDER_STEP_4_BUILDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_get_building)],
            ORDER_STEP_5_PEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_get_pest)],
            ORDER_STEP_6_IMAGE: [MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL) & ~filters.COMMAND, order_get_image)],
            ORDER_STEP_7_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_get_time)],
            ORDER_STEP_8_PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, order_get_payment)],
            ORDER_STEP_9_NOTES: [MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO | filters.Document.ALL) & ~filters.COMMAND, order_get_notes)],
            ORDER_CONFIRM: [CallbackQueryHandler(order_confirmation, pattern="^order_")],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(order_conv)
    app.add_handler(CommandHandler("holat", set_status))
    app.add_handler(CommandHandler("yakunlash", finish_order))
    app.add_handler(MessageHandler(filters.Regex("^(ℹ️ Biz haqimizda|🛡 Kafolat|📦 Buyurtmam holati)$"), menu_router))
    app.add_handler(MessageHandler(filters.Regex("^🤖 NANODEZ AI$"), ai_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
