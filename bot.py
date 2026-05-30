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
# CONFIG
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
ADMIN_ID = int(ADMIN_ID) if ADMIN_ID else 0

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
# START
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "សួស្តី! 🙏\n\n"
        "👉 /free - FREE PLAN\n"
        "👉 /buy - PREMIUM PLAN\n"
        "👉 /status - ស្ថានភាព"
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

    save_db()

    await update.message.reply_text(
        "🎉 FREE PLAN ACTIVATED\n📌 Limit: 1 page"
    )

# =====================
# BUY PLAN (UPDATED PRICING)
# =====================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(
        photo=InputFile(QR_IMAGE),
        caption=(
            "💳 Pricing Plans:\n\n"
            "💵 $8  → 10 Pages\n"
            "💵 $15 → 20 Pages\n"
            "💵 $20 → 30 Pages\n"
            "💵 $50 → 80 Pages\n\n"
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

    if not is_facebook_link(text):
        await update.message.reply_text("❌ សូមផ្ញើ Facebook link ត្រឹមត្រូវ")
        return

    limit = user.get("limit", 1)

    if limit != -1 and len(user["pages"]) >= limit:
        await update.message.reply_text(
            f"❌ Limit reached ({limit} pages)\n👉 Upgrade plan"
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
        text=f"💰 Payment Request\nUser ID: {user.id}\n/approve {user.id} 8|15|20|50"
    )

    await update.message.reply_text("📩 Sent to admin")

# =====================
# APPROVE (NEW PRICING SYSTEM)
# =====================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    try:
        user_id = context.args[0]
        plan = context.args[1]

        plan_map = {
            "8": 10,
            "15": 20,
            "20": 30,
            "50": 80
        }

        if plan not in plan_map:
            await update.message.reply_text("❌ Use: 8 | 15 | 20 | 50")
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

        await update.message.reply_text("✅ Approved done")

    except:
        await update.message.reply_text("❌ /approve user_id 8|15|20|50")

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
# MAIN (RENDER SAFE)
# =====================
def main():
    request = HTTPXRequest(connect_timeout=30, read_timeout=30)

    app = ApplicationBuilder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("free", free))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("status", status))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Bot running on Render...")

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
