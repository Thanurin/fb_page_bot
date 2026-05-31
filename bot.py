import os
import json
import time
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =====================
# CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

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

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

users = load_db()

# =====================
# VALIDATION
# =====================
def is_facebook_link(text: str):
    return bool(re.match(r"https?://(www\.)?facebook\.com/.+", text))

# =====================
# START
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome!\n\n"
        "/free - Free plan\n"
        "/buy - Pricing\n"
        "/status - Status"
    )

# =====================
# FREE PLAN
# =====================
async def free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    users[user_id] = {
        "plan": "free",
        "limit": 1,
        "expire": time.time() + 9999999999,
        "pages": []
    }

    save_db(users)

    await update.message.reply_text("🎉 Free plan activated (1 page)")

# =====================
# BUY
# =====================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 Pricing Plans:\n\n"
        "$3 → 10 pages\n"
        "$6 → 20 pages\n"
        "$12 → 30 pages\n\n"
        "Send payment screenshot 📩"
    )

# =====================
# TEXT HANDLER
# =====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if text.startswith("/"):
        return

    if user_id not in users:
        await update.message.reply_text("Please use /free first")
        return

    user = users[user_id]

    if not is_facebook_link(text):
        await update.message.reply_text("❌ Invalid Facebook link")
        return

    if len(user["pages"]) >= user["limit"]:
        await update.message.reply_text("❌ Limit reached. Upgrade plan")
        return

    user["pages"].append(text)
    save_db(users)

    await update.message.reply_text("✅ Page saved")

# =====================
# PHOTO HANDLER (PAYMENT PROOF)
# =====================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    keyboard = [
        [InlineKeyboardButton("$3 (10 pages)", callback_data=f"approve:{user.id}:3")],
        [InlineKeyboardButton("$6 (20 pages)", callback_data=f"approve:{user.id}:6")],
        [InlineKeyboardButton("$12 (30 pages)", callback_data=f"approve:{user.id}:12")],
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"💰 Payment from user {user.id}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    await update.message.reply_text("📩 Sent to admin")

# =====================
# APPROVE PAYMENT
# =====================
async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    try:
        _, user_id, plan = query.data.split(":")
    except:
        return

    plan_map = {
        "3": 10,
        "6": 20,
        "12": 30,
    }

    if plan not in plan_map:
        return

    users[user_id] = {
        "plan": plan,
        "limit": plan_map[plan],
        "expire": time.time() + 365 * 86400,
        "pages": [],
    }

    save_db(users)

    await context.bot.send_message(
        chat_id=int(user_id),
        text=f"🎉 Approved!\n💳 Plan: ${plan}\n📄 Limit: {plan_map[plan]} pages",
    )

    await query.message.reply_text("✅ Approved")

# =====================
# STATUS
# =====================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if user_id not in users:
        await update.message.reply_text("❌ No plan")
        return

    user = users[user_id]

    await update.message.reply_text(
        f"📌 Plan: ${user['plan']}\n"
        f"📄 Pages: {len(user['pages'])}/{user['limit']}"
    )
# =====================
# MAIN
# =====================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("free", free))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("status", status))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(approve_callback))

    print("Bot running...")

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
