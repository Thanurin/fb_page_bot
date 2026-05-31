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

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DB_FILE = "db.json"

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN is missing!")

# ================= DB =================
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

# ================= VALIDATION =================
def is_facebook_link(text: str):
    return bool(re.match(r"https?://(www\.)?facebook\.com/.+", text))

# ================= EXPIRE CHECK =================
def is_expired(user):
    return "expire" in user and time.time() > user["expire"]

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 សួស្តី!\n\n"
        "/free - គម្រោងឥតគិតថ្លៃ\n"
        "/buy - តម្លៃគម្រោង\n"
        "/status - ស្ថានភាព"
    )

# ================= FREE =================
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

# ================= BUY =================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 តម្លៃគម្រោង៖\n\n"
        "$3 → 10 pages\n"
        "$6 → 20 pages\n"
        "$12 → 30 pages\n\n"
        "ផ្ញើរូបភាពបង់ប្រាក់មក 📩"
    )

# ================= STATUS =================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if user_id not in users:
        return await update.message.reply_text("❌ អ្នកមិនទាន់មានគម្រោង")

    user = users[user_id]

    if is_expired(user):
        del users[user_id]
        save_db(users)
        return await update.message.reply_text("⛔ គម្រោងផុតកំណត់")

    await update.message.reply_text(
        f"📌 គម្រោង: {user['plan']}\n"
        f"📄 ចំនួន: {len(user['pages'])}/{user['limit']}"
    )

# ================= TEXT HANDLER =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if text.startswith("/"):
        return

    if user_id not in users:
        return await update.message.reply_text("⚠️ សូមប្រើ /free មុនសិន")

    user = users[user_id]

    if is_expired(user):
        del users[user_id]
        save_db(users)
        return await update.message.reply_text("⛔ គម្រោងផុតកំណត់")

    if not is_facebook_link(text):
        return await update.message.reply_text("❌ Link Facebook មិនត្រឹមត្រូវ")

    if len(user["pages"]) >= user["limit"]:
        return await update.message.reply_text("❌ អស់ចំនួនហើយ")

    user["pages"].append(text)
    save_db(users)

    await update.message.reply_text("✅ បានរក្សាទុករួចហើយ")

# ================= PHOTO (PAYMENT) =================
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

# ================= ADMIN APPROVE =================
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
        text=f"🎉 អនុម័តរួចហើយ!\n💳 Plan: ${plan}\n📄 Limit: {plan_map[plan]} pages",
    )

    await query.message.reply_text("✅ Approved")

# ================= MAIN (SAFE FOR RENDER) =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("free", free))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("status", status))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(approve_callback))

    print("🚀 Bot running safely on polling mode")

    # ✅ ONLY THIS (NO async, NO threads, NO webhook)
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
