from __future__ import annotations

import logging
import random
from dataclasses import dataclass, asdict
from enum import IntEnum
from typing import Any, Optional

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# =========================
# CONFIG
# =========================

BOT_TOKEN = "YOUR_BOT_TOKEN"
GROUP_CHAT_ID = -1001234567890

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

SKIP_VALUE = "Kiritilmagan"
ORDER_PREFIX = "NDZ"


# =========================
# STATES
# =========================

class OrderState(IntEnum):
    NAME = 0
    PHONE = 1
    ADDRESS = 2
    OBJECT_TYPE = 3
    PEST_TYPE = 4
    MEDIA = 5
    TIME = 6
    PAYMENT = 7
    NOTE = 8
    CONFIRM = 9


# =========================
# DATA MODEL
# =========================

@dataclass
class OrderDraft:
    name: str = ""
    phone: str = ""
    address: str = ""
    object_type: str = SKIP_VALUE
    pest_type: str = SKIP_VALUE
    media_type: str = SKIP_VALUE
    media_file_id: str = SKIP_VALUE
    time: str = SKIP_VALUE
    payment: str = SKIP_VALUE
    note: str = SKIP_VALUE


# =========================
# HELPERS
# =========================

def get_draft(context: ContextTypes.DEFAULT_TYPE) -> OrderDraft:
    raw = context.user_data.get("order_draft")
    if not raw:
        draft = OrderDraft()
        context.user_data["order_draft"] = asdict(draft)
        return draft
    return OrderDraft(**raw)


def save_draft(context: ContextTypes.DEFAULT_TYPE, draft: OrderDraft) -> None:
    context.user_data["order_draft"] = asdict(draft)


def clear_draft(context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("order_draft", None)
    context.user_data.pop("order_step", None)


def set_step(context: ContextTypes.DEFAULT_TYPE, state: OrderState) -> None:
    context.user_data["order_step"] = int(state)


def normalize_text(text: str) -> str:
    return text.strip()


def normalize_phone(text: str) -> str:
    return (
        text.replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )


def is_valid_name(text: str) -> bool:
    return len(text.strip()) >= 2


def is_valid_phone(text: str) -> bool:
    phone = normalize_phone(text)
    return phone.startswith("+") or phone.isdigit()


def generate_order_id() -> str:
    return f"{ORDER_PREFIX}-{random.randint(100000, 999999)}"


def format_location(update: Update) -> str:
    loc = update.message.location
    return f"{loc.latitude}, {loc.longitude}"


def confirmation_text(draft: OrderDraft) -> str:
    return (
        "━━━━━━━━━━━━━━
"
        "📋 BUYURTMA MA'LUMOTLARI
"
        f"👤 Ism: {draft.name}
"
        f"📞 Telefon: {draft.phone}
"
        f"📍 Manzil: {draft.address}
"
        f"🏠 Obyekt: {draft.object_type}
"
        f"🐜 Zararkunanda: {draft.pest_type}
"
        f"🖼 Rasm: {draft.media_type}
"
        f"🕒 Qulay vaqt: {draft.time}
"
        f"💳 To'lov: {draft.payment}
"
        f"📝 Izoh: {draft.note}
"
        "━━━━━━━━━━━━━━"
    )


# =========================
# KEYBOARDS
# =========================

def kb_name():
    return ReplyKeyboardMarkup(
        [["⬅️ Ortga", "❌ Bekor qilish"]],
        resize_keyboard=True
    )


def kb_phone():
    return ReplyKeyboardMarkup(
        [["📱 Kontakt yuborish"], ["⬅️ Ortga", "❌ Bekor qilish"]],
        resize_keyboard=True
    )


def kb_address():
    return ReplyKeyboardMarkup(
        [["📍 Joylashuv yuborish"], ["⬅️ Ortga", "❌ Bekor qilish"]],
        resize_keyboard=True
    )


def kb_object_type():
    return ReplyKeyboardMarkup(
        [
            ["🏠 Xonadon", "🏢 Ofis"],
            ["🏬 Do'kon", "🏭 Korxona"],
            ["🌾 Ferma", "🏫 Davlat tashkiloti"],
            ["🏨 Mehmonxona", "📦 Ombor"],
            ["🔹 Boshqa", "🔸 O'tkazib yuborish"],
            ["⬅️ Ortga", "❌ Bekor qilish"],
        ],
        resize_keyboard=True
    )


def kb_pest_type():
    return ReplyKeyboardMarkup(
        [
            ["🪳 Suvarak", "🐭 Sichqon"],
            ["🐜 Chumoli", "🦟 Chivin"],
            ["🕷 O'rgimchak", "🐝 Ari"],
            ["🐍 Ilon", "🦂 Chayon"],
            ["🔹 Boshqa", "🔸 O'tkazib yuborish"],
            ["⬅️ Ortga", "❌ Bekor qilish"],
        ],
        resize_keyboard=True
    )


def kb_media():
    return ReplyKeyboardMarkup(
        [["🔸 O'tkazib yuborish"], ["⬅️ Ortga", "❌ Bekor qilish"]],
        resize_keyboard=True
    )


def kb_time():
    return ReplyKeyboardMarkup(
        [
            ["🌅 Ertalab", "☀️ Kunduzi"],
            ["🌆 Kechqurun", "📞 Operator bilan kelishaman"],
            ["🔸 O'tkazib yuborish"],
            ["⬅️ Ortga", "❌ Bekor qilish"],
        ],
        resize_keyboard=True
    )


def kb_payment():
    return ReplyKeyboardMarkup(
        [
            ["💵 Naqd", "💳 Karta"],
            ["🏦 Bank o'tkazmasi", "🔸 O'tkazib yuborish"],
            ["⬅️ Ortga", "❌ Bekor qilish"],
        ],
        resize_keyboard=True
    )


def kb_note():
    return ReplyKeyboardMarkup(
        [["🔸 O'tkazib yuborish"], ["⬅️ Ortga", "❌ Bekor qilish"]],
        resize_keyboard=True
    )


def kb_confirm():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Tasdiqlash va yuborish", callback_data="confirm")],
            [
                InlineKeyboardButton("✏️ Tahrirlash", callback_data="edit"),
                InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel"),
            ],
        ]
    )


# =========================
# INTEGRATIONS
# =========================

async def write_to_google_sheets(order_id: str, draft: OrderDraft, user: Any) -> None:
    logger.info("Google Sheetsga yozish: %s | %s", order_id, draft)


async def send_to_crm(order_id: str, draft: OrderDraft, user: Any) -> None:
    logger.info("CRMga yuborish: %s | %s", order_id, draft)


async def send_to_operator(update: Update, order_id: str, draft: OrderDraft) -> None:
    text = (
        "🆕 YANGI BUYURTMA
"
        f"🆔 {order_id}
"
        f"👤 {draft.name}
"
        f"📞 {draft.phone}
"
        f"📍 {draft.address}
"
        f"🏠 {draft.object_type}
"
        f"🐜 {draft.pest_type}
"
        f"🖼 {draft.media_type}
"
        f"🕒 {draft.time}
"
        f"💳 {draft.payment}
"
        f"📝 {draft.note}"
    )
    await update.effective_chat.send_message(text)


# =========================
# START / CANCEL
# =========================

async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    clear_draft(context)
    save_draft(context, OrderDraft())
    set_step(context, OrderState.NAME)
    await update.message.reply_text(
        "Buyurtma berish uchun ismingizni kiriting.",
        reply_markup=kb_name(),
    )
    return OrderState.NAME


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    clear_draft(context)
    await update.message.reply_text(
        "Buyurtma bekor qilindi.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# =========================
# STATES
# =========================

async def name_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = normalize_text(update.message.text)

    if text == "❌ Bekor qilish":
        return await cancel_order(update, context)

    if text == "⬅️ Ortga":
        return await start_order(update, context)

    if not is_valid_name(text):
        await update.message.reply_text(
            "Iltimos, ismni to'g'ri kiriting. Masalan: Ali",
            reply_markup=kb_name(),
        )
        return OrderState.NAME

    draft = get_draft(context)
    draft.name = text
    save_draft(context, draft)
    set_step(context, OrderState.PHONE)

    await update.message.reply_text(
        "Telefon raqamingizni kiriting yoki kontakt yuboring.",
        reply_markup=kb_phone(),
    )
    return OrderState.PHONE


async def phone_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = normalize_text(update.message.text or "")

    if text == "❌ Bekor qilish":
        return await cancel_order(update, context)

    if text == "⬅️ Ortga":
        set_step(context, OrderState.NAME)
        await update.message.reply_text(
            "Ismingizni qayta kiriting.",
            reply_markup=kb_name(),
        )
        return OrderState.NAME

    draft = get_draft(context)

    if update.message.contact:
        draft.phone = normalize_phone(update.message.contact.phone_number)
        save_draft(context, draft)
        set_step(context, OrderState.ADDRESS)
        await update.message.reply_text(
            "Manzilingizni yozing yoki joylashuv yuboring.",
            reply_markup=kb_address(),
        )
        return OrderState.ADDRESS

    if not is_valid_phone(text):
        await update.message.reply_text(
            "Telefon raqam noto'g'ri. Masalan: +998901234567",
            reply_markup=kb_phone(),
        )
        return OrderState.PHONE

    draft.phone = normalize_phone(text)
    save_draft(context, draft)
    set_step(context, OrderState.ADDRESS)

    await update.message.reply_text(
        "Manzilingizni yozing yoki joylashuv yuboring.",
        reply_markup=kb_address(),
    )
    return OrderState.ADDRESS


async def address_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = normalize_text(update.message.text or "")

    if text == "❌ Bekor qilish":
        return await cancel_order(update, context)

    if text == "⬅️ Ortga":
        set_step(context, OrderState.PHONE)
        await update.message.reply_text(
            "Telefon raqamingizni qayta yuboring.",
            reply_markup=kb_phone(),
        )
        return OrderState.PHONE

    draft = get_draft(context)

    if update.message.location:
        draft.address = format_location(update)
    else:
        if len(text) < 4:
            await update.message.reply_text(
                "Manzil juda qisqa. To'liq manzil kiriting.",
                reply_markup=kb_address(),
            )
            return OrderState.ADDRESS
        draft.address = text

    save_draft(context, draft)
    set_step(context, OrderState.OBJECT_TYPE)

    await update.message.reply_text(
        "Obyekt turini tanlang yoki o'tkazib yuboring.",
        reply_markup=kb_object_type(),
    )
    return OrderState.OBJECT_TYPE


async def object_type_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = normalize_text(update.message.text)

    if text == "❌ Bekor qilish":
        return await cancel_order(update, context)

    if text == "⬅️ Ortga":
        set_step(context, OrderState.ADDRESS)
        await update.message.reply_text(
            "Manzilni qayta kiriting.",
            reply_markup=kb_address(),
        )
        return OrderState.ADDRESS

    draft = get_draft(context)
    draft.object_type = SKIP_VALUE if text == "🔸 O'tkazib yuborish" else text
    save_draft(context, draft)
    set_step(context, OrderState.PEST_TYPE)

    await update.message.reply_text(
        "Zararkunanda turini tanlang yoki o'tkazib yuboring.",
        reply_markup=kb_pest_type(),
    )
    return OrderState.PEST_TYPE


async def pest_type_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = normalize_text(update.message.text)

    if text == "❌ Bekor qilish":
        return await cancel_order(update, context)

    if text == "⬅️ Ortga":
        set_step(context, OrderState.OBJECT_TYPE)
        await update.message.reply_text(
            "Obyekt turini qayta tanlang.",
            reply_markup=kb_object_type(),
        )
        return OrderState.OBJECT_TYPE

    draft = get_draft(context)
    draft.pest_type = SKIP_VALUE if text == "🔸 O'tkazib yuborish" else text
    save_draft(context, draft)
    set_step(context, OrderState.MEDIA)

    await update.message.reply_text(
        "Muammo rasmi, video yoki dokument yuboring.",
        reply_markup=kb_media(),
    )
    return OrderState.MEDIA


async def media_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = normalize_text(update.message.text or "")

    if text == "❌ Bekor qilish":
        return await cancel_order(update, context)

    if text == "⬅️ Ortga":
        set_step(context, OrderState.PEST_TYPE)
        await update.message.reply_text(
            "Zararkunanda turini qayta tanlang.",
            reply_markup=kb_pest_type(),
        )
        return OrderState.PEST_TYPE

    draft = get_draft(context)

    if text == "🔸 O'tkazib yuborish":
        draft.media_type = SKIP_VALUE
        draft.media_file_id = SKIP_VALUE
    elif update.message.photo:
        draft.media_type = "Photo"
        draft.media_file_id = update.message.photo[-1].file_id
    elif update.message.video:
        draft.media_type = "Video"
        draft.media_file_id = update.message.video.file_id
    elif update.message.document:
        draft.media_type = "Document"
        draft.media_file_id = update.message.document.file_id
    else:
        await update.message.reply_text(
            "Iltimos, photo, video, document yuboring yoki o'tkazib yuboring.",
            reply_markup=kb_media(),
        )
        return OrderState.MEDIA

    save_draft(context, draft)
    set_step(context, OrderState.TIME)

    await update.message.reply_text(
        "Qulay vaqtni tanlang yoki o'tkazib yuboring.",
        reply_markup=kb_time(),
    )
    return OrderState.TIME


async def time_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = normalize_text(update.message.text)

    if text == "❌ Bekor qilish":
        return await cancel_order(update, context)

    if text == "⬅️ Ortga":
        set_step(context, OrderState.MEDIA)
        await update.message.reply_text(
            "Muammo rasmini qayta yuboring yoki o'tkazib yuboring.",
            reply_markup=kb_media(),
        )
        return OrderState.MEDIA

    draft = get_draft(context)
    draft.time = SKIP_VALUE if text == "🔸 O'tkazib yuborish" else text
    save_draft(context, draft)
    set_step(context, OrderState.PAYMENT)

    await update.message.reply_text(
        "To'lov turini tanlang yoki o'tkazib yuboring.",
        reply_markup=kb_payment(),
    )
    return OrderState.PAYMENT


async def payment_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = normalize_text(update.message.text)

    if text == "❌ Bekor qilish":
        return await cancel_order(update, context)

    if text == "⬅️ Ortga":
        set_step(context, OrderState.TIME)
        await update.message.reply_text(
            "Qulay vaqtni qayta tanlang.",
            reply_markup=kb_time(),
        )
        return OrderState.TIME

    draft = get_draft(context)
    draft.payment = SKIP_VALUE if text == "🔸 O'tkazib yuborish" else text
    save_draft(context, draft)
    set_step(context, OrderState.NOTE)

    await update.message.reply_text(
        "Qo'shimcha izoh yozing yoki o'tkazib yuboring.",
        reply_markup=kb_note(),
    )
    return OrderState.NOTE


async def note_state(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = normalize_text(update.message.text)

    if text == "❌ Bekor qilish":
        return await cancel_order(update, context)

    if text == "⬅️ Ortga":
        set_step(context, OrderState.PAYMENT)
        await update.message.reply_text(
            "To'lov turini qayta tanlang.",
            reply_markup=kb_payment(),
        )
        return OrderState.PAYMENT

    draft = get_draft(context)
    draft.note = SKIP_VALUE if text == "🔸 O'tkazib yuborish" else text
    save_draft(context, draft)
    set_step(context, OrderState.CONFIRM)

    await update.message.reply_text(
        confirmation_text(draft),
        reply_markup=kb_confirm(),
    )
    return OrderState.CONFIRM


# =========================
# CONFIRM CALLBACK
# =========================

async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    draft = get_draft(context)

    if query.data == "cancel":
        clear_draft(context)
        await query.edit_message_text("Buyurtma bekor qilindi.")
        return ConversationHandler.END

    if query.data == "edit":
        set_step(context, OrderState.NAME)
        await query.edit_message_text("Buyurtmani tahrirlash uchun qayta boshlang.")
        await query.message.reply_text(
            "Ismingizni kiriting.",
            reply_markup=kb_name(),
        )
        return OrderState.NAME

    if query.data == "confirm":
        order_id = generate_order_id()

        await write_to_google_sheets(order_id, draft, update.effective_user)
        await send_to_crm(order_id, draft, update.effective_user)
        await send_to_operator(update, order_id, draft)

        clear_draft(context)

        await query.edit_message_text(
            f"✅ Buyurtmangiz muvaffaqiyatli qabul qilindi!
"
            f"📄 Buyurtma raqami: {order_id}
"
            f"📞 Operatorlarimiz tez orada siz bilan bog'lanishadi.
"
            f"📦 Buyurtmangiz holatini "📦 Buyurtmam holati" bo'limi orqali kuzatishingiz mumkin."
        )
        return ConversationHandler.END

    return OrderState.CONFIRM


# =========================
# APP
# =========================

def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    order_conv = ConversationHandler(
        entry_points=[CommandHandler("order", start_order)],
        states={
            OrderState.NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_state)],
            OrderState.PHONE: [
                MessageHandler(filters.CONTACT, phone_state),
                MessageHandler(filters.TEXT & ~filters.COMMAND, phone_state),
            ],
            OrderState.ADDRESS: [
                MessageHandler(filters.LOCATION, address_state),
                MessageHandler(filters.TEXT & ~filters.COMMAND, address_state),
            ],
            OrderState.OBJECT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, object_type_state)],
            OrderState.PEST_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, pest_type_state)],
            OrderState.MEDIA: [
                MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, media_state),
                MessageHandler(filters.TEXT & ~filters.COMMAND, media_state),
            ],
            OrderState.TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, time_state)],
            OrderState.PAYMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, payment_state)],
            OrderState.NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, note_state)],
            OrderState.CONFIRM: [CallbackQueryHandler(confirm_callback)],
        },
        fallbacks=[CommandHandler("cancel", cancel_order)],
        allow_reentry=True,
    )

    app.add_handler(order_conv)
    app.add_handler(CommandHandler("cancel", cancel_order))
    return app


def main() -> None:
    app = build_app()
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()