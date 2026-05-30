import time
import json
import os
import re
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

# =====================
# CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

QR_IMAGE = "qr.png"
DB_FILE = "db.json"

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN is missing!")

# =====================
# DB
# =====================
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(users, f)

users = load_db()

# =====================
# VALIDATION
# =====================
def is_facebook_link(text: str):
    return bool(re.match(r"https?://(www\.)?facebook\.com/.+", text))

# =====================
# HANDLERS
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "សួស្តី! 🙏\n\n"
        "👉 /free - FREE PLAN (1 page)\n"
        "👉 /buy - PREMIUM PLAN\n"
        "👉 /status - ស្ថានភាព"
    )

async def free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    users[user_id] = {
        "plan": "free",
        "limit": 1,
        "expire": time.time() + 9999999999,
        "pages": []
    }

    save_db()
    await update.message.reply_text("🎉 FREE PLAN ACTIVATED (1 page)")

# =====================
# BUY (UPDATED PRICING)
# =====================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        with open(QR_IMAGE, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=(
                    "💳 Pricing Plans:\n\n"
                    "💵 $3  → 10 Pages\n"
                    "💵 $6  → 20 Pages\n"
                    "💵 $12 → 30 Pages\n\n"
                    "📩 Send payment screenshot"
                )
            )
    except Exception as e:
        await update.message.reply_text(f"❌ QR error: {e}")

# =====================
# TEXT HANDLER
# =====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if text.startswith("/"):
        return

    if user_id not in users:
        await update.message.reply_text("សូមចុច /free មុនសិន")
        return

    user = users[user_id]

    if not is_facebook_link(text):
        await update.message.reply_text("❌ សូមផ្ញើ Facebook link ត្រឹមត្រូវ")
        return

    if len(user["pages"]) >= user["limit"]:
        await update.message.reply_text("❌ Limit reached. Upgrade plan!")
        return

    user["pages"].append(text)
    save_db()

    await update.message.reply_text("✅ Page saved")

# =====================
# PHOTO HANDLER (ADMIN REVIEW)
# =====================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    keyboard = [
        [InlineKeyboardButton("💵 $3 (10 pages)", callback_data=f"approve:{user.id}:3")],
        [InlineKeyboardButton("💵 $6 (20 pages)", callback_data=f"approve:{user.id}:6")],
        [InlineKeyboardButton("💵 $12 (30 pages)", callback_data=f"approve:{user.id}:12")],
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"💰 Payment from User ID: {user.id}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await update.message.reply_text("📩 Sent to admin")

# =====================
# APPROVE CALLBACK (FIXED + CONSISTENT)
# =====================
async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("❌ Not allowed")
        return

    _, user_id, plan = query.data.split(":")

    # ✅ FIXED PLAN MAPPING
    plan_map = {
        "3": 10,
        "6": 20,
        "12": 30
    }

    if plan not in plan_map:
        await query.edit_message_text("❌ Invalid plan")
        return

    limit = plan_map[plan]

    users[user_id] = {
        "plan": plan,
        "limit": limit,
        "expire": time.time() + 365 * 86400,
        "pages": []
    }

    save_db()

    await context.bot.send_message(
        chat_id=int(user_id),
        text=f"🎉 Approved!\n💳 ${plan}\n📌 Limit: {limit} pages"
    )

    await query.edit_message_text(f"✅ Approved user {user_id} → ${plan}")

# =====================
# STATUS
# =====================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if user_id not in users:
        await update.message.reply_text("❌ No plan")
        return

    user = users[user_id]

    if user["expire"] < time.time():
        await update.message.reply_text("❌ Expired! /buy")
        return

    await update.message.reply_text(
        f"📌 Plan: ${user['plan']}\n"
        f"📄 Pages: {len(user['pages'])}/{user['limit']}"
    )

# =====================
# MAIN (RENDER SAFE FIXED)
# =====================
async def main():
    request = HTTPXRequest(connect_timeout=30, read_timeout=30)

    app = ApplicationBuilder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("free", free))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("status", status))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(approve_callback))

    print("Bot running on Render...")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
