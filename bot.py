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

def expired(user):
    return "expire" in user and time.time() > user["expire"]

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 សួស្តី! (/free /buy /status)")

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
    await update.message.reply_text("🎉 Free plan activated (1 page)")

# ================= BUY =================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 Plans:\n"
        "$3 → 10 pages\n"
        "$6 → 20 pages\n"
        "$12 → 30 pages"
    )

# ================= TEXT =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if text.startswith("/"):
        return

    if user_id not in users:
        return await update.message.reply_text("Use /free first")

    user = users[user_id]

    if expired(user):
        del users[user_id]
        save_db(users)
        return await update.message.reply_text("Plan expired")

    if not is_facebook_link(text):
        return await update.message.reply_text("Invalid Facebook link")

    if len(user["pages"]) >= user["limit"]:
        return await update.message.reply_text("Limit reached")

    user["pages"].append(text)
    save_db(users)

    await update.message.reply_text("Saved")

# ================= PHOTO =================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    keyboard = [
        [InlineKeyboardButton("$3", callback_data=f"approve:{user.id}:3")],
        [InlineKeyboardButton("$6", callback_data=f"approve:{user.id}:6")],
        [InlineKeyboardButton("$12", callback_data=f"approve:{user.id}:12")],
    ]

    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=f"Payment from {user.id}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    await update.message.reply_text("Sent to admin")

# ================= APPROVE =================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.from_user.id != ADMIN_ID:
        return

    _, user_id, plan = q.data.split(":")

    plans = {"3": 10, "6": 20, "12": 30}

    users[user_id] = {
        "plan": plan,
        "limit": plans[plan],
        "expire": time.time() + 365 * 86400,
        "pages": []
    }

    save_db(users)

    await context.bot.send_message(
        chat_id=int(user_id),
        text=f"Approved: ${plan} plan"
    )

    await q.message.reply_text("Done")

# ================= MAIN (ONLY SAFE METHOD) =================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("free", free))
    app.add_handler(CommandHandler("buy", buy))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(approve))

    print("Bot running...")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
