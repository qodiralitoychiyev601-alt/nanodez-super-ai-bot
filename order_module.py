"""
NANODEZ Professional Order Module
==================================
9-bosqichli buyurtma berish FSM (Finite State Machine) modulli tizim.
Kod: modular, izohli, production-ready.

Bosqichlar:
1. Ism
2. Telefon
3. Manzil (Location + Text)
4. Obyekt turi (O'tkazib yuborish mumkin)
5. Zararkunanda turi (O'tkazib yuborish mumkin)
6. Muammo rasmi (Photo/Video/Document) (O'tkazib yuborish mumkin)
7. Qulay vaqt (O'tkazib yuborish mumkin)
8. To'lov turi (O'tkazib yuborish mumkin)
9. Qo'shimcha izoh (O'tkazib yuborish mumkin)

Keyin: Tasdiqlash → Google Sheets + CRM + Operator Group
"""

import logging
import re
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
)

logger = logging.getLogger(__name__)

# ============ STATE DEFINITIONS (9 bosqich + 1 confirm) ============
ORDER_STEP_1_NAME = 1
ORDER_STEP_2_PHONE = 2
ORDER_STEP_3_LOCATION = 3
ORDER_STEP_4_BUILDING_TYPE = 4
ORDER_STEP_5_PEST_TYPE = 5
ORDER_STEP_6_IMAGE = 6
ORDER_STEP_7_TIME = 7
ORDER_STEP_8_PAYMENT = 8
ORDER_STEP_9_NOTES = 9
ORDER_STEP_CONFIRM = 10

# ============ TUGMALAR (Buttons) ============
BACK_BUTTON = "⬅️ Ortga"
SKIP_BUTTON = "🔸 O'tkazib yuborish"
CANCEL_BUTTON = "❌ Bekor qilish"
SHARE_CONTACT = "📱 Kontakt yuborish"
SHARE_LOCATION = "📍 Joylashuv yuborish"
CONFIRM_BUTTON = "✅ Tasdiqlash va yuborish"
EDIT_BUTTON = "✏️ Tahrirlash"

# ============ VARIANTLAR (Options) ============
BUILDING_OPTIONS = [
    ["🏠 Xonadon", "🏢 Ofis"],
    ["🏬 Do'kon", "🏭 Korxona"],
    ["🌾 Ferma", "🏫 Davlat tashkiloti"],
    ["🏨 Mehmonxona", "📦 Ombor"],
    ["🔹 Boshqa", SKIP_BUTTON],
    [BACK_BUTTON],
]

PEST_OPTIONS = [
    ["🪳 Suvarak", "🐭 Sichqon"],
    ["🐜 Chumoli", "🦟 Chivin"],
    ["🕷 O'rgimchak", "🐝 Ari"],
    ["🐍 Ilon", "🦂 Chayon"],
    ["🔹 Boshqa", SKIP_BUTTON],
    [BACK_BUTTON],
]

TIME_OPTIONS = [
    ["🌅 Ertalab", "☀️ Kunduzi"],
    ["🌆 Kechqurun", "📞 Operator bilan kelishaman"],
    [SKIP_BUTTON, BACK_BUTTON],
]

PAYMENT_OPTIONS = [
    ["💵 Naqd", "💳 Karta"],
    ["🏦 Bank o'tkazmasi", SKIP_BUTTON],
    [BACK_BUTTON],
]

# ============ ORDER DATA CLASS ============
@dataclass
class OrderData:
    """Buyurtma ma'lumotlari modelini aniqlash"""
    name: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    location_latitude: Optional[float] = None
    location_longitude: Optional[float] = None
    building_type: Optional[str] = None
    pest_type: Optional[str] = None
    image_file_id: Optional[str] = None
    image_type: Optional[str] = None  # photo, video, document
    preferred_time: Optional[str] = None
    payment_method: Optional[str] = None
    notes: Optional[str] = None
    
    def get_display_dict(self) -> dict:
        """Ko'rsatish uchun ma'lumotlar dictionarysini qaytarish"""
        return {
            "👤 Ism": self.name or "—",
            "📞 Telefon": self.phone or "—",
            "📍 Manzil": self.location or "—",
            "🏠 Obyekt": self.building_type or "Kiritilmagan",
            "🐜 Zararkunanda": self.pest_type or "Kiritilmagan",
            "🖼 Rasm": "✅ Yuborildi" if self.image_file_id else "Yo'q",
            "🕒 Qulay vaqt": self.preferred_time or "Kiritilmagan",
            "💳 To'lov": self.payment_method or "Kiritilmagan",
            "📝 Izoh": self.notes or "Yo'q",
        }


# ============ VALIDATION FUNCTIONS ============
def validate_name(name: str) -> tuple[bool, str]:
    """Ismni validatsiya qilish"""
    name = name.strip()
    if not name:
        return False, "Ism bo'sh bo'lishi mumkin emas."
    if len(name) < 2:
        return False, "Ism kamida 2 harfdan iborat bo'lishi kerak."
    if len(name) > 100:
        return False, "Ism 100 harfdan ko'p bo'lishi mumkin emas."
    return True, name


def validate_phone(phone: str) -> tuple[bool, str]:
    """Telefon raqamini validatsiya qilish"""
    phone = phone.strip()
    # +998, 0998, 998 formatlarini qabul qil
    phone_pattern = r'^(\+998|0998|998)?\s*\d{2}\s*\d{3}[-\s]?\d{2}[-\s]?\d{2}$'
    if not re.match(phone_pattern, phone):
        return False, (
            "❌ Telefon raqami noto'g'ri.\n\n"
            "To'g'ri formatlar:\n"
            "+998 90 123-45-67\n"
            "0998901234567\n"
            "yoki Kontakt tugmasini bosing."
        )
    return True, phone


def validate_location(location: str) -> tuple[bool, str]:
    """Manzilni validatsiya qilish"""
    location = location.strip()
    if not location:
        return False, "Manzil bo'sh bo'lishi mumkin emas."
    if len(location) < 5:
        return False, "Manzil juda qisqa. Batafsil yozing."
    if len(location) > 300:
        return False, "Manzil 300 harfdan ko'p bo'lishi mumkin emas."
    return True, location


# ============ STEP 1: ISM ============
async def order_step_1_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    1-bosqich: Foydalanuvchi ismini kiritadi.
    
    Tugmalar:
    - ⬅️ Ortga (bosh menyuga qaytish)
    - ❌ Bekor qilish (FSM'ni bekor qilish)
    """
    if update.message and update.message.text == CANCEL_BUTTON:
        await update.message.reply_text(
            "❌ Buyurtma bekor qilindi. Bosh menyudan foydalaning.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    if update.message and update.message.text == BACK_BUTTON:
        # Bosh menyuning menyusu kerak, lekin bu birinchi bosqich, shuning uchun bekor qilaman
        await update.message.reply_text(
            "⬅️ Bosh menyuya qaytdingiz.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    if not context.user_data.get("order"):
        context.user_data["order"] = OrderData()
    
    await update.message.reply_text(
        "👤 <b>1-bosqich: Ismingiz</b>\n\n"
        "Iltimos, to'liq ismingizni kiriting:\n"
        "<i>(masalan: Qodirali, Rajab Qodirov)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            [[BACK_BUTTON], [CANCEL_BUTTON]],
            resize_keyboard=True,
            one_time_keyboard=False,
        ),
    )
    return ORDER_STEP_1_NAME


async def order_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ismni qabul qilish va validatsiya qilish"""
    text = update.message.text
    
    # Cancel va Back tugmalari
    if text == CANCEL_BUTTON:
        await update.message.reply_text(
            "❌ Buyurtma bekor qilindi.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    if text == BACK_BUTTON:
        await update.message.reply_text(
            "⬅️ Bosh menyuya qaytdingiz.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    # Validatsiya
    is_valid, result = validate_name(text)
    if not is_valid:
        await update.message.reply_text(f"❌ {result}")
        return ORDER_STEP_1_NAME
    
    # Saqlash
    context.user_data["order"].name = result
    
    # Keyingi bosqichga o'tish
    await update.message.reply_text(
        "✅ Ism saqlandi!\n\n"
        "📞 <b>2-bosqich: Telefon raqami</b>\n\n"
        "Iltimos, telefon raqamingizni kiriting yoki Kontakt tugmasini bosing:\n"
        "<i>(masalan: +998 90 123-45-67)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            [[SHARE_CONTACT], [BACK_BUTTON], [CANCEL_BUTTON]],
            resize_keyboard=True,
            one_time_keyboard=False,
        ),
    )
    return ORDER_STEP_2_PHONE


# ============ STEP 2: TELEFON ============
async def order_get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Telefon raqamini qabul qilish (text yoki contact)"""
    
    # Cancel va Back
    if update.message and update.message.text == CANCEL_BUTTON:
        await update.message.reply_text(
            "❌ Buyurtma bekor qilindi.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    if update.message and update.message.text == BACK_BUTTON:
        await update.message.reply_text(
            "👤 <b>1-bosqich: Ismingiz</b>\n\n"
            "Ismingizni qayta kiriting:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                [[BACK_BUTTON], [CANCEL_BUTTON]],
                resize_keyboard=True,
            ),
        )
        context.user_data["order"].name = None
        return ORDER_STEP_1_NAME
    
    # Contact tugmasidan yuborilgan?
    if update.message and update.message.contact:
        phone = update.message.contact.phone_number
        if not phone.startswith("+"):
            phone = f"+{phone}"
    else:
        phone = update.message.text
    
    # Validatsiya
    is_valid, result = validate_phone(phone)
    if not is_valid:
        await update.message.reply_text(f"{result}")
        return ORDER_STEP_2_PHONE
    
    context.user_data["order"].phone = result
    
    # Keyingi bosqich
    await update.message.reply_text(
        "✅ Telefon saqlandi!\n\n"
        "📍 <b>3-bosqich: Manzil</b>\n\n"
        "Manzilni kiriting yoki Joylashuv tugmasini bosing:\n"
        "<i>(masalan: Sirdaryo vl., Guliston t., Sayxun MFY)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            [[SHARE_LOCATION], [BACK_BUTTON], [CANCEL_BUTTON]],
            resize_keyboard=True,
        ),
    )
    return ORDER_STEP_3_LOCATION


# ============ STEP 3: MANZIL (Text + Location) ============
async def order_get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Manzilni qabul qilish (text yoki GPS location)"""
    
    # Cancel va Back
    if update.message and update.message.text == CANCEL_BUTTON:
        await update.message.reply_text(
            "❌ Buyurtma bekor qilindi.",
            reply_markup=ReplyKeyboardRemove(),
        )
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    if update.message and update.message.text == BACK_BUTTON:
        await update.message.reply_text(
            "📞 <b>2-bosqich: Telefon raqami</b>\n\n"
            "Telefon raqamingizni qayta kiriting:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                [[SHARE_CONTACT], [BACK_BUTTON], [CANCEL_BUTTON]],
                resize_keyboard=True,
            ),
        )
        context.user_data["order"].phone = None
        return ORDER_STEP_2_PHONE
    
    # Location yuborildi?
    if update.message and update.message.location:
        location = update.message.location
        context.user_data["order"].location_latitude = location.latitude
        context.user_data["order"].location_longitude = location.longitude
        context.user_data["order"].location = f"📍 {location.latitude}, {location.longitude}"
        display_location = f"📍 Joylashuv: {location.latitude:.4f}, {location.longitude:.4f}"
    else:
        # Text manzil
        location_text = update.message.text
        is_valid, result = validate_location(location_text)
        if not is_valid:
            await update.message.reply_text(f"❌ {result}")
            return ORDER_STEP_3_LOCATION
        context.user_data["order"].location = result
        display_location = f"📍 Manzil: {result}"
    
    # Keyingi bosqich
    await update.message.reply_text(
        f"✅ {display_location} saqlandi!\n\n"
        "🏠 <b>4-bosqich: Obyekt turi</b>\n\n"
        "<i>(O'tkazib yuborish mumkin)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(BUILDING_OPTIONS, resize_keyboard=True),
    )
    return ORDER_STEP_4_BUILDING_TYPE


# ============ STEP 4: OBYEKT TURI ============
async def order_get_building_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Obyekt turini qabul qilish"""
    
    text = update.message.text
    
    if text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Buyurtma bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    if text == BACK_BUTTON:
        await update.message.reply_text(
            "📍 <b>3-bosqich: Manzil</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                [[SHARE_LOCATION], [BACK_BUTTON], [CANCEL_BUTTON]],
                resize_keyboard=True,
            ),
        )
        context.user_data["order"].location = None
        return ORDER_STEP_3_LOCATION
    
    # Skip yoki variantlardan biri
    if text != SKIP_BUTTON:
        context.user_data["order"].building_type = text
    
    # Keyingi bosqich
    await update.message.reply_text(
        "🐜 <b>5-bosqich: Zararkunanda turi</b>\n\n"
        "<i>(O'tkazib yuborish mumkin)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(PEST_OPTIONS, resize_keyboard=True),
    )
    return ORDER_STEP_5_PEST_TYPE


# ============ STEP 5: ZARARKUNANDA TURI ============
async def order_get_pest_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Zararkunanda turini qabul qilish"""
    
    text = update.message.text
    
    if text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Buyurtma bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    if text == BACK_BUTTON:
        await update.message.reply_text(
            "🏠 <b>4-bosqich: Obyekt turi</b>\n\n"
            "<i>(O'tkazib yuborish mumkin)</i>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(BUILDING_OPTIONS, resize_keyboard=True),
        )
        context.user_data["order"].building_type = None
        return ORDER_STEP_4_BUILDING_TYPE
    
    if text != SKIP_BUTTON:
        context.user_data["order"].pest_type = text
    
    # Keyingi bosqich
    await update.message.reply_text(
        "🖼 <b>6-bosqich: Muammo rasmi</b>\n\n"
        "Photo, Video yoki fayl yuborishingiz mumkin.\n"
        "<i>(O'tkazib yuborish mumkin)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            [[SKIP_BUTTON], [BACK_BUTTON], [CANCEL_BUTTON]],
            resize_keyboard=True,
        ),
    )
    return ORDER_STEP_6_IMAGE


# ============ STEP 6: MUAMMO RASMI ============
async def order_get_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Photo/Video/Document qabul qilish"""
    
    if update.message.text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Buyurtma bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    if update.message.text == BACK_BUTTON:
        await update.message.reply_text(
            "🐜 <b>5-bosqich: Zararkunanda turi</b>\n\n"
            "<i>(O'tkazib yuborish mumkin)</i>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(PEST_OPTIONS, resize_keyboard=True),
        )
        context.user_data["order"].pest_type = None
        return ORDER_STEP_5_PEST_TYPE
    
    if update.message.text == SKIP_BUTTON:
        pass  # Rasm yo'q
    elif update.message.photo:
        context.user_data["order"].image_file_id = update.message.photo[-1].file_id
        context.user_data["order"].image_type = "photo"
    elif update.message.video:
        context.user_data["order"].image_file_id = update.message.video.file_id
        context.user_data["order"].image_type = "video"
    elif update.message.document:
        context.user_data["order"].image_file_id = update.message.document.file_id
        context.user_data["order"].image_type = "document"
    else:
        await update.message.reply_text("❌ Faqat Photo, Video yoki fayl yuborishingiz mumkin.")
        return ORDER_STEP_6_IMAGE
    
    # Keyingi bosqich
    await update.message.reply_text(
        "🕒 <b>7-bosqich: Qulay vaqt</b>\n\n"
        "<i>(O'tkazib yuborish mumkin)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(TIME_OPTIONS, resize_keyboard=True),
    )
    return ORDER_STEP_7_TIME


# ============ STEP 7: QULAY VAQT ============
async def order_get_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Qulay vaqtni qabul qilish"""
    
    text = update.message.text
    
    if text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Buyurtma bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    if text == BACK_BUTTON:
        await update.message.reply_text(
            "🖼 <b>6-bosqich: Muammo rasmi</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(
                [[SKIP_BUTTON], [BACK_BUTTON], [CANCEL_BUTTON]],
                resize_keyboard=True,
            ),
        )
        context.user_data["order"].image_file_id = None
        return ORDER_STEP_6_IMAGE
    
    if text != SKIP_BUTTON:
        context.user_data["order"].preferred_time = text
    
    # Keyingi bosqich
    await update.message.reply_text(
        "💳 <b>8-bosqich: To'lov turi</b>\n\n"
        "<i>(O'tkazib yuborish mumkin)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(PAYMENT_OPTIONS, resize_keyboard=True),
    )
    return ORDER_STEP_8_PAYMENT


# ============ STEP 8: TO'LOV TURI ============
async def order_get_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """To'lov turini qabul qilish"""
    
    text = update.message.text
    
    if text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Buyurtma bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    if text == BACK_BUTTON:
        await update.message.reply_text(
            "🕒 <b>7-bosqich: Qulay vaqt</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(TIME_OPTIONS, resize_keyboard=True),
        )
        context.user_data["order"].preferred_time = None
        return ORDER_STEP_7_TIME
    
    if text != SKIP_BUTTON:
        context.user_data["order"].payment_method = text
    
    # Keyingi bosqich
    await update.message.reply_text(
        "📝 <b>9-bosqich: Qo'shimcha izoh</b>\n\n"
        "Masalan: 3-qavat, Darvoza kodi, It bor.\n"
        "<i>(O'tkazib yuborish mumkin)</i>",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            [[SKIP_BUTTON], [BACK_BUTTON], [CANCEL_BUTTON]],
            resize_keyboard=True,
        ),
    )
    return ORDER_STEP_9_NOTES


# ============ STEP 9: QO'SHIMCHA IZOH ============
async def order_get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Qo'shimcha izohni qabul qilish"""
    
    text = update.message.text
    
    if text == CANCEL_BUTTON:
        await update.message.reply_text("❌ Buyurtma bekor qilindi.", reply_markup=ReplyKeyboardRemove())
        context.user_data.pop("order", None)
        return ConversationHandler.END
    
    if text == BACK_BUTTON:
        await update.message.reply_text(
            "💳 <b>8-bosqich: To'lov turi</b>",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardMarkup(PAYMENT_OPTIONS, resize_keyboard=True),
        )
        context.user_data["order"].payment_method = None
        return ORDER_STEP_8_PAYME