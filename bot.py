"""
╔═══════════════════════════════════════════════════════════════╗
║          NANODEZ SUPER AI BOT - PRODUCTION VERSION            ║
║                  Professional & Scalable                      ║
╚═══════════════════════════════════════════════════════════════╝

Bot Features:
✅ 9-bosqichli professional buyurtma berish (FSM)
✅ Google Gemini AI - hasharotlar haqida savol-javob
✅ Operator guruhi - /shartnoma buyrug'i bilan manual shartnoma
✅ PDF shartnoma generation (Kirill harflari, QR-kod)
✅ Order tracking
✅ Professional UX/UI

Token: 8984817143:AAGhVN_3GwNStdD26PAZW5eJOmAxsKL-IxA
Group ID: -5392028380
Gemini API: AQ.Ab8RN6IIor7qJxgkjkQ9nOypVf4kM57J0N7esF2mTUqj9CAPKw
"""

import asyncio
import logging
import os
import random
import sqlite3
import string
from datetime import datetime
from io import BytesIO

import qrcode
import requests
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputFile,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
    CallbackQueryHandler,
)

# ============ LOGGING SETUP ============
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ============ KONFIGURATSIYA ============
BOT_TOKEN = "8984817143:AAGhVN_3GwNStdD26PAZW5eJOmAxsKL-IxA"
GROUP_CHAT_ID = "-5392028380"
WEBSITE_URL = "https://nanodez.uz/"

# Shriftlar (Kirill harflari uchun)
FONT_DIR = os.path.dirname(os.path.abspath(__file__))
pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))

# Google Gemini AI
GEMINI_API_KEY = "AQ.Ab8RN6IIor7qJxgkjkQ9nOypVf4kM57J0N7esF2mTUqj9CAPKw"
GEMINI_MODEL = "gemini-flash-latest"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

AI_SYSTEM_PROMPT = (
    "Sen NANODEZ kompaniyasining sun'iy intellekt yordamchisisan. Sen FAQAT quyidagi mavzularda "
    "javob berasan: hasharotlar (tarakan, chumoli, qandala va h.k.), kemiruvchilar (sichqon, "
    "kalamush), zararkunandalar, mikrob va infeksiyalar, dezinfeksiya, dezinseksiya, deratizatsiya "
    "va uy/bino sanitariyasi.\n\n"
    "Agar foydalanuvchi shu mavzularga aloqasi bo'lmagan narsa so'rasa (masalan siyosat, sport, "
    "shaxsiy maslahat va h.k.), muloyimlik bilan faqat zararkunandalar va sanitariya mavzusida "
    "yordam bera olishingni ayt va suhbatni shu mavzuga qaytar.\n\n"
    "Javoblaring qisqa, tushunarli va foydali bo'lsin (o'zbek tilida, lotin alifbosida). "
    "Agar foydalanuvchining tavsifidan uning uyida yoki binosida jiddiy zararkunanda muammosi "
    "borligi ko'rinsa, javob oxirida NANODEZ xizmatlarini tavsiya qil — masalan, professional "
    "yordam uchun botdagi \"📝 Buyurtma berish\" tugmasidan foydalanishni taklif qil."
)

# ============ TUGMALAR ============
BACK_BUTTON = "⬅️ Ortga"
SKIP_BUTTON = "🔸 O'tkazib yuborish"
CANCEL_BUTTON = "❌ Bekor qilish"
SHARE_CONTACT = "📱 Kontakt yuborish"
SHARE_LOCATION = "📍 Joylashuv yuborish"

# ============ MAIN MENU ============
MAIN_MENU = [
    ["📝 Buyurtma berish"],
    ["ℹ️ Biz haqimizda", "🛡 Kafolat"],
    ["📦 Buyurtmam holati"],
    ["🤖 NANODEZ AI"],
]

STATUS_LABELS = {
    "yangi": "🆕 Yangi",
    "jarayonda": "⏳ Jarayonda",
    "bajarildi": "✅ Bajarildi",
}

# ============ MATNLAR ============
ABOUT_TEXT = (
    "🏢 <b>NANODEZ haqida</b>\n\n"
    "\"NANO DEZ\" MChJ — O'zbekiston Respublikasi Sog'liqni saqlash vazirligi "
    "tomonidan litsenziyalangan (litsenziya № 779115) dezinfeksiya, dezinseksiya "
    "va deratizatsiya xizmatlari kompaniyasi.\n\n"
    "✅ 8 yillik tajribaga ega xodimlar\n"
    "✅ 5000 dan ortiq turar-joy va yuridik binolarga xizmat ko'rsatilgan\n"
    "✅ 12 viloyatda faoliyat yuritamiz\n"
    "✅ Rasmiy tibbiy litsenziya asosida ishlaymiz\n\n"
    "🌐 Sayt: https://nanodez.uz/\n"
    "✈️ Telegram kanal: https://t.me/nanodez_uz\n"
    "📸 Instagram: https://www.instagram.com/nanodez_uz\n"
    "▶️ YouTube: https://youtube.com/@nanodez_uz\n"
    "🎵 TikTok: https://www.tiktok.com/@nanodez_pest_control\n"
    "📞 Murojaat uchun: +998 55-511-11-13"
)

WARRANTY_TEXT = (
    "🛡️ <b>NANODEZ KAFOLATI</b>\n\n"
    "✅ Har bir xizmat uchun yozma yoki elektron kafolat taqdim etiladi.\n"
    "📅 Kafolat muddati: bajarilgan xizmat turiga qarab 3 oydan 1 yilgacha.\n"
    "📋 Kafolat davomida:\n"
    "• Zararkunandalar qayta paydo bo'lsa, bepul qayta ishlov beriladi.\n"
    "• Kafolat shartlariga rioya qilingan bo'lishi kerak.\n"
    "• Kafolat shartnomada ko'rsatiladi.\n\n"
    "📞 Batafsil ma'lumot: +998 55 511-11-13\n"
    "💬 Buyurtma berish uchun \"📝 Buyurtma berish\" tugmasini bosing."
)

# ============ DATABASE ============
def init_db():
    """SQLite database'ni initialize qilish"""
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute(
        """
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
        """
    )
    conn.commit()
    conn.close()


def save_order(
    order_id, user_id, username, name, phone, location, building_type, pest_type,
    image_file_id, preferred_time, payment_method, notes
):
    """Buyurtmani database'ga saqlash"""
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO orders
        (id, user_id, username, name, phone, location, building_type, pest_type,
         image_file_id, preferred_time, payment_method, notes, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (order_id, user_id, username, name, phone, location, building_type,
         pest_type, image_file_id, preferred_time, payment_method, notes, "yangi"),
    )
    conn.commit()
    conn.close()


def get_latest_order_for_user(user_id):
    """Foydalanuvchining oxirgi buyurtmasini olish"""
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return row


def get_order(order_id):
    """Order ID bo'yicha buyurtmani olish"""
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def update_order_status(order_id, status):
    """Buyurtma holatini yangilash"""
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    conn.close()


def update_order_final(order_id, amount, warranty):
    """Buyurtmani yakuniy (amount + warranty) ma'lumot bilan yangilash"""
    conn = sqlite3.connect("nanodez_orders.db")
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE orders SET status = ?, amount = ?, warranty = ? WHERE id = ?",
        ("bajarildi", amount, warranty, order_id),
    )
    conn.commit()
    conn.close()


# ============ SHARTNOMA GENERATION (PDF + QR) ============
UZ_MONTHS = {
    1: "январь", 2: "феврал", 3: "март", 4: "апрель", 5: "май", 6: "июнь",
    7: "июль", 8: "август", 9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь",
}

_styles = {
    "title": ParagraphStyle("title", fontName="DejaVu-Bold", fontSize=15, alignment=TA_CENTER, spaceAfter=10),
    "logo": ParagraphStyle("logo", fontName="DejaVu-Bold", fontSize=13, alignment=TA_RIGHT),
    "logo_sub": ParagraphStyle("logo_sub", fontName="DejaVu", fontSize=8, alignment=TA_RIGHT, textColor="#555555"),
    "city_date": ParagraphStyle("city_date", fontName="DejaVu-Bold", fontSize=10, spaceAfter=8),
    "body": ParagraphStyle("body", fontName="DejaVu", fontSize=9.5, alignment=TA_JUSTIFY, leading=13, spaceAfter=6),
    "heading": ParagraphStyle("heading", fontName="DejaVu-Bold", fontSize=10.5, alignment=TA_CENTER, spaceBefore=10, spaceAfter=6),
    "small": ParagraphStyle("small", fontName="DejaVu", fontSize=8.5, leading=12),
    "small_bold": ParagraphStyle("small_bold", fontName="DejaVu-Bold", fontSize=9),
}


def build_contract_pdf(order_row) -> BytesIO:
    """Professional PDF shartnoma yaratish (Kirill, QR-kod)"""
    (order_id, user_id, username, name, phone, location, building_type, pest_type,
     image_file_id, preferred_time, payment_method, notes, status, created_at, amount, warranty) = order_row

    try:
        order_date = datetime.fromisoformat(created_at)
    except Exception:
        order_date = datetime.now()
    
    day = order_date.day
    month_name = UZ_MONTHS.get(order_date.month, "")
    year = order_date.year

    amount_display = amount or "-"

    qr_content = (
        f"NANODEZ | Litsenziya No779115 | Shartnoma: {order_id} | "
        f"Mijoz: {name} | Summa: {amount_display} | Sana: {day}.{order_date.month:02d}.{year} | {WEBSITE_URL}"
    )
    qr_img = qrcode.make(qr_content)
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=15 * mm, bottomMargin=15 * mm,
    )
    story = []
    s = _styles

    # Sarlavha
    header_tbl = Table(
        [[Paragraph(f"Шартнома № {order_id}", ParagraphStyle("h", fontName="DejaVu-Bold", fontSize=13)),
          Paragraph("NANODEZ<br/><font size=8 color='#555555'>pest control</font>", s["logo"])]],
        colWidths=[110 * mm, 60 * mm],
    )
    header_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header_tbl)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph(
        f"Тошкент шаҳри&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;"
        f"&laquo;{day}&raquo; {month_name} {year} й.",
        s["city_date"],
    ))

    story.append(Paragraph(
        "2025 йил 19 май кунидаги 779115 - сонли лицензия ва Устави асосида фаолият олиб борувчи "
        "\"NANO DEZ\" МЧЖ бир томондан ва жамиятнинг (бундан кейин \"Бажарувчи\" деб юритилади) номидан "
        "иш юритувчи директор А.А.БОБОРАИМОВ бир томондан, иккинчи томондан (бундан кейин \"Буюртмачи\" "
        f"деб юритилади) <b>{name}</b> ва улар тақдим этган шахсий сўрови асосида ушбу шартномани "
        "қуйидагича туздик:",
        s["body"],
    ))

    story.append(Paragraph("1. ШАРТНОМА ПРЕДМЕТИ", s["heading"]))
    story.append(Paragraph(
        "1.1. Бажарувчи Буюртмачининг буюртмасига биноан қуйида келтирилган санитария ишларини ва "
        "бошқа турдаги хизматларни бажариш мажбуриятини ўз зиммасига олади:",
        s["body"],
    ))

    table_data = [
        ["№", "Хизматлар тури", "Ул.Бирл", "Миқ", "Нархи", "Сумма"],
        ["1", pest_type or "Хизмат", "хизмат", "1", amount_display, amount_display],
        ["", "Жами бўлиб:", "", "", "", amount_display],
    ]
    tbl = Table(table_data, colWidths=[10 * mm, 65 * mm, 20 * mm, 15 * mm, 25 * mm, 25 * mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "DejaVu"),
        ("FONTNAME", (0, 0), (-1, 0), "DejaVu-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, "#888888"),
        ("BACKGROUND", (0, 0), (-1, 0), "#e8f0fe"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("SPAN", (0, 2), (1, 2)),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph(
        "2.1. Шартномада кўрсатилган хизматлар эвазига амалга оширилиши лозим бўлган тўлов суммаси: "
        f"<b>{amount_display} сўм</b>.",
        s["body"],
    ))

    story.append(Paragraph("3. ТОМОНЛАРНИНГ ҲУҚУҚ ВА МАЖБУРИЯТЛАРИ", s["heading"]))
    story.append(Paragraph(
        "3.1. Бажарувчи мутахассисининг ўз ишини бажариши учун шароит яратиб бериш ва объектга эркин "
        "кириб чиқишини таъминлаш Буюртмачининг мажбурияти ҳисобланади.",
        s["body"],
    ))
    story.append(Paragraph(
        f"3.3. Бажарувчи объект эски бўлмаган ва зарарли ҳашаротлар ва кемирувчиларнинг кўпайишига "
        f"мойил бўлмаган тақдирда <b>{warranty or '____'}</b> давомида кўрсатилган санитария хизматлари "
        "учун қайта ишлов бериш кафолатини беради.",
        s["body"],
    ))

    story.append(Paragraph("8. ТОМОНЛАРНИНГ ҲУҚУҚИЙ МАНЗИЛЛАРИ ВА РЕКВИЗИТЛАРИ", s["heading"]))

    parties_data = [
        [Paragraph("<b>Бажарувчи:</b>", s["small_bold"]), Paragraph("<b>Буюртмачи:</b>", s["small_bold"])],
        [Paragraph(
            "\"NANO DEZ\" МЧЖ<br/>"
            "Адрес: Тошкент вил, Бекобод тумани, Қушчи МФЙ, Гулистон кўч 342-уй<br/>"
            "Тошкент ш., \"Ҳамкор-банк\" АТ Миробод филиали, МФО 00083<br/>"
            "Р/сч: 20208000207186790001<br/>"
            "ИНН 311813026<br/>"
            "Директор: BOBORAIMOV ABDURASHID<br/>"
            "Колл-центр: 55 511-11-13<br/>"
            f"Веб-сайт: {WEBSITE_URL}",
            s["small"],
        ), Paragraph(
            f"Ф.И.Ш: {name}<br/>"
            f"Манзил: {location}<br/>"
            f"Телефон: {phone}<br/>"
            f"Шартнома рақами: {order_id}<br/>"
            f"Хизмат тури: {pest_type}<br/>"
            f"Тўлов суммаси: {amount_display} сўм",
            s["small"],
        )],
    ]
    parties_tbl = Table(parties_data, colWidths=[90 * mm, 70 * mm])
    parties_tbl.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 1), (-1, 1), 4),
    ]))
    story.append(parties_tbl)

    story.append(Spacer(1, 8 * mm))
    qr_reader = __import__("reportlab.lib.utils", fromlist=["ImageReader"]).ImageReader(qr_buffer)
    qr_tbl = Table(
        [[Paragraph(
            "Ушбу ҳужжат NANODEZ tomonidan avtomatik yaratilgan bo'lib, "
            f"xizmat yakunlanganini tasdiqlaydi.<br/>Rasmiy sayt: {WEBSITE_URL}",
            s["small"],
        ), ""]],
        colWidths=[130 * mm, 30 * mm],
    )
    story.append(qr_tbl)

    def _draw_qr(canvas, doc_):
        canvas.saveState()
        canvas.drawImage(qr_reader, doc_.pagesize[0] - 45 * mm, 15 * mm, 30 * mm, 30 * mm)
        canvas.setFont("DejaVu", 7)
        canvas.drawCentredString(doc_.pagesize[0] - 30 * mm, 12 * mm, "Tekshirish uchun QR-kod")
        canvas.restoreState()

    doc.build(story, onFirstPage=_draw_qr, onLaterPages=_draw_qr)
    pdf_buffer.seek(0)
    return pdf_buffer


# ============ GEMINI AI ============
def _call_gemini_sync(user_message: str) -> str:
    """Gemini API ga qo'lday so'rov yuborish"""
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    payload = {
        "system_instruction": {"parts": [{"text": AI_SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
    }
    resp = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


async def ask_gemini(user_message: str) -> str:
    """Gemini AI dan javob olish (async)"""
    try:
        return await asyncio.to_thread(_call_gemini_sync, user_message)
    except Exception as e:
        logger.warning("Gemini AI xatosi: %s", e)
        return (
            "❌ Kechirasiz, hozir javob berishda muammo yuzaga keldi. "
            "Birozdan so'ng qayta urinib ko'ring, yoki \"📝 Buyurtma berish\" orqali "
            "to'g'ridan-to'g'ri operatorga murojaat qiling."
        )


# ============ START COMMAND ============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Bot /start buyrug'i"""
    context.user_data["ai_mode"] = False
    await update.message.reply_text(
        "Assalomu alaykum! 👋\n\n"
        "NANODEZ zararkunandalarga qarshi xizmat botiga xush kelibsiz.\n\n"
        "Quyidagi menyudan foydalaning:",
        reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
    )
    return ConversationHandler.END


# ============ MENU ROUTER ============
async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bosh menu tugmalarining handleri"""
    text = update.message.text
    
    if text == "ℹ️ Biz haqimizda":
        await update.message.reply_text(ABOUT_TEXT, parse_mode="HTML")
    elif text == "🛡 Kafolat":
        await update.message.reply_text(WARRANTY_TEXT, parse_mode="HTML")
    elif text == "📦 Buyurtmam holati":
        user_id = update.effective_user.id
        row = get_latest_order_for_user(user_id)
        if not row:
            await update.message.reply_text(
                "❌ Sizda hali buyurtma topilmadi.\n\n"
                "\"📝 Buyurtma berish\" tugmasini bosing."
            )
        else:
            order_id = row[0]
            status = row[12]
            created_at = row[13]
            label = STATUS_LABELS.get(status, status)
            await update.message.reply_text(
                f"📦 <b>Buyurtma ma'lumotlari</b>\n\n"
                f"🔖 Raqami: {order_id}\n"
                f"Holat: {label}\n"
                f"📅 Sana: {created_at[:10]}",
                parse_mode="HTML",
            )


# ============ AI MODE ============
async def ai_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🤖 NANODEZ AI tugmasini bosgan vaqt"""
    context.user_data["ai_mode"] = True
    await update.message.reply_text(
        "🤖 <b>NANODEZ AI ga xush kelibsiz!</b>\n\n"
        "Hasharotlar, kemiruvchilar, zararkunandalar va mikrob-infeksiyalar haqida "
        "istalgan savolingizni yozing.\n\n"
        "Chiqish uchun: \"⬅️ Ortga\" tugmasini bosing.",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            [[BACK_BUTTON]],
            resize_keyboard=True,
            one_time_keyboard=False,
        ),
    )


async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI bilan suhbat"""
    if not context.user_data.get("ai_mode"):
        return

    if update.message.text == BACK_BUTTON:
        context.user_data["ai_mode"] = False
        await update.message.reply_text(
            "⬅️ Bosh menyuya qaytdingiz.",
            reply_markup=ReplyKeyboardMarkup(MAIN_MENU, resize_keyboard=True),
        )
        return

    await update.message.chat.send_action("typing")
    answer = await ask_gemini(update.message.text)
    await update.message.reply_text(answer, reply_markup=ReplyKeyboardMarkup(
        [[BACK_BUTTON]],
        resize_keyboard=True,
    ))


# ============ OPERATOR COMMANDS ============
async def set_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/holat <order_id> <yangi|jarayonda> - Holat yangilash"""
    try:
        order_id = context.args[0]
        status = context.args[1]
        
        if status not in ["yangi", "jarayonda", "bajarildi"]:
            await update.message.reply_text("❌ Holat noto'g'ri. Variantlar: yangi, jarayonda, bajarildi")
            return
        
        row = get_order(order_id)
        if not row:
            await update.message.reply_text(f"❌ Buyurtma {order_id} topilmadi.")
            return
        
        update_order_status(order_id, status)
        
        # Mijozga xabar
        user_id = row[1]
        label = STATUS_LABELS.get(status, status)
        
        try:
            await context.bot.send_message(
                user_id,
                f"📦 Buyurtmangiz (#{order_id}) holati yangilandi:\n\n"
                f"Holat: {label}",
            )
        except Exception:
            pass
        
        await update.message.reply_text(f"✅ Holat yangilandi: {order_id} → {label}")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format: /holat <order_id> <yangi|jarayonda|bajarildi>")


async def finish_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/yakunlash <order_id> <summa> <kafolat> - Ishni yakunlash va PDF shartnoma yuborish"""
    try:
        order_id = context.args[0]
        amount = context.args[1]
        warranty = " ".join(context.args[2:]) if len(context.args) > 2 else "—"
        
        row = get_order(order_id)
        if not row:
            await update.message.reply_text(f"❌ Buyurtma {order_id} topilmadi.")
            return
        
        # DB yangilash
        update_order_final(order_id, amount, warranty)
        
        # PDF yaratish
        pdf_buffer = build_contract_pdf(row)
        
        # Mijozga shartnoma yuborish
        user_id = row[1]
        try:
            await context.bot.send_document(
                user_id,
                pdf_buffer,
                filename=f"NANODEZ_shartnoma_{order_id}.pdf",
                caption=f"✅ Xizmat bajarildi!\n\n📄 Shartnoma #{order_id}\n"
                        f"💰 Summa: {amount} so'm\n"
                        f"🛡 Kafolat: {warranty}",
            )
        except Exception as e:
            logger.error(f"PDF yuborishda xato: {e}")
        
        await update.message.reply_text(
            f"✅ Buyurtma yakunlandi!\n"
            f"📄 #{order_id}\n"
            f"💰 {amount} so'm\n"
            f"🛡 Kafolat: {warranty}"
        )
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Format: /yakunlash <order_id> <summa> <kafolat_muddati>")


# ============ MAIN ============
def main():
    """Bot ishga tushirish"""
    init_db()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Minimal order handler (for compatibility)
    # Order module integrate qilish uchun kerak bo'lgan handler
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("holat", set_status))
    app.add_handler(CommandHandler("yakunlash", finish_order))
    
    # Menu router
    app.add_handler(
        MessageHandler(
            filters.Regex("^(ℹ️ Biz haqimizda|🛡 Kafolat|📦 Buyurtmam holati)$"),
            menu_router,
        )
    )
    
    # AI mode
    app.add_handler(MessageHandler(filters.Regex("^🤖 NANODEZ AI$"), ai_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))
    
    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
