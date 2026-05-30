import time
import json
import os
import re

from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest

# =====================
# CONFIG (SAFE FOR RENDER)
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else 0

QR_IMAGE = "qr.png"
DB_FILE = "db.json"

if not BOT_TOKEN:
    raise Exception("BOT_TOKEN is missing!")

# =====================
# LOAD / SAVE DB
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
# HELP FUNCTION
# =====================
def is_facebook_link(text: str):
    return bool(re.match(r"https?://(www\.)?facebook\.com/.+", text))

# =====================
# START
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "សួស្តី! អតិថិជនជាទីគោរព 🙏\n\n"
        "👉 /free - FREE PLAN (1 page)\n"
        "👉 /buy - Premium plans\n"
        "👉 /status - មើលស្ថានភាព"
    )

# =====================
# FREE PLAN
# =====================
async def free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    users[user_id] = {
        "plan": "free",
        "expire": time.time() + 9999999999,
        "pages": []
    }

    save_db()

    await update.message.reply_text(
        "🎉 FREE PLAN ACTIVATED\n"
        "📌 អាចដាក់បាន 1 Facebook Page"
    )

# =====================
# BUY PLAN
# =====================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(
        photo=InputFile(QR_IMAGE),
        caption=(
            "💳 Payment Plans:\n"
            "1️⃣ $3 / week\n"
            "2️⃣ $11.5 / month\n"
            "3️⃣ $120 / year\n\n"
            "📩 Send screenshot after payment"
        )
    )

# =====================
# HANDLE PAGE LINK
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

    # only allow facebook links
    if not is_facebook_link(text):
        await update.message.reply_text("❌ សូមផ្ញើ Facebook Page link ត្រឹមត្រូវ")
        return

    # free limit
    if user["plan"] == "free" and len(user["pages"]) >= 1:
        await update.message.reply_text(
            "❌ FREE plan limit 1 page\n👉 /buy ដើម្បី upgrade"
        )
        return

    user["pages"].append(text)
    save_db()

    await update.message.reply_text("✅ Page បានរក្សាទុករួច")

# =====================
# PAYMENT SCREENSHOT
# =====================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user

    await context.bot.forward_message(
        chat_id=ADMIN_ID,
        from_chat_id=update.message.chat_id,
        message_id=update.message.message_id
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"💰 Payment Request\n"
            f"User ID: {user.id}\n"
            f"/approve {user.id} month"
        )
    )

    await update.message.reply_text("📩 បានផ្ញើទៅ Admin រួចហើយ")

# =====================
# APPROVE (ADMIN)
# =====================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    try:
        user_id = context.args[0]
        plan = context.args[1]

        days_map = {
            "week": 7,
            "month": 30,
            "year": 365
        }

        if plan not in days_map:
            await update.message.reply_text("❌ plan invalid")
            return

        users[user_id] = {
            "plan": plan,
            "expire": time.time() + days_map[plan] * 86400,
            "pages": []
        }

        save_db()

        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"🎉 Approved! Plan: {plan}"
        )

        await update.message.reply_text("✅ Approved done")

    except:
        await update.message.reply_text("❌ /approve user_id week|month|year")

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
        await update.message.reply_text("❌ Expired! /buy ដើម្បីបន្ត")
        return

    await update.message.reply_text(
        f"📌 Plan: {user['plan']}\n"
        f"📄 Pages: {len(user['pages'])}"
    )

# =====================
# MAIN (RENDER FIX)
# =====================
request = HTTPXRequest(connect_timeout=30, read_timeout=30)

app = ApplicationBuilder().token(BOT_TOKEN).request(request).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("free", free))
app.add_handler(CommandHandler("buy", buy))
app.add_handler(CommandHandler("approve", approve))
app.add_handler(CommandHandler("status", status))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

def main():
    print("Bot running on Render...")
    app.run_polling()

if __name__ == "__main__":
    main()
