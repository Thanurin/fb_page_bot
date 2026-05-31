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

# 🔥 ADD THIS (Render gives PORT automatically)
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://your-app.onrender.com

DB_FILE = "db.json"

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN is missing!")

if not WEBHOOK_URL:
    print("⚠️ WARNING: WEBHOOK_URL is not set")

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
# HANDLERS (UNCHANGED)
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 សួស្តី!\n\n"
        "/free - ប្រើគម្រោងឥតគិតថ្លៃ\n"
        "/buy - តម្លៃគម្រោង\n"
        "/status - មើលស្ថានភាព"
    )

async def free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    users[user_id] = {
        "plan": "free",
        "limit": 1,
        "expire": time.time() + 9999999999,
        "pages": []
    }

    save_db(users)

    await update.message.reply_text("🎉 អ្នកបានបើកគម្រោងឥតគិតថ្លៃ (1 page)")

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 តម្លៃគម្រោង៖\n\n"
        "$3 → 10 pages\n"
        "$6 → 20 pages\n"
        "$12 → 30 pages\n\n"
        "ផ្ញើរូបភាពបង់ប្រាក់មក 📩"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if text.startswith("/"):
        return

    if user_id not in users:
        await update.message.reply_text("សូមប្រើ /free មុនសិន 🙏")
        return

    user = users[user_id]

    if not is_facebook_link(text):
        await update.message.reply_text("❌ Link Facebook មិនត្រឹមត្រូវ")
        return

    if len(user["pages"]) >= user["limit"]:
        await update.message.reply_text("❌ អស់ចំនួនហើយ! សូម upgrade គម្រោង")
        return

    user["pages"].append(text)
    save_db(users)

    await update.message.reply_text("✅ បានរក្សាទុក page រួចហើយ")

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
        caption=f"💰 Payment ពី user {user.id}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    await update.message.reply_text("📩 បានផ្ញើទៅ admin ហើយ")

async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        return

    _, user_id, plan = query.data.split(":")

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
        text=f"🎉 អនុម័តរួចហើយ!\n💳 Plan: ${plan}\n📄 Limit: {plan_map[plan]} pages",
    )

    await query.message.reply_text("✅ Approved")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if user_id not in users:
        await update.message.reply_text("❌ អ្នកមិនទាន់មាន plan")
        return

    user = users[user_id]

    await update.message.reply_text(
        f"📌 Plan: ${user['plan']}\n"
        f"📄 Pages: {len(user['pages'])}/{user['limit']}"
    )

# =====================
# 🔥 FIXED MAIN (WEBHOOK MODE FOR RENDER)
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

    print("🚀 Bot running in WEBHOOK mode...")

    # 🔥 THIS IS THE ONLY CORRECT WAY ON RENDER WEB SERVICE
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
