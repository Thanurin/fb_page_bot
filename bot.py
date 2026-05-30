import time
import json
import os

from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    Defaults,
)
from telegram.request import HTTPXRequest

# =====================
# CONFIG (SAFE)
# =====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
QR_IMAGE = "qr.png"
DB_FILE = "db.json"

# =====================
# LOAD / SAVE DB
# =====================
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(users, f)

users = load_db()

# =====================
# START
# =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "សួស្តី! អតិថិជនជាទីគោរព!\n\n"
        "👉 /free - FREE PLAN\n"
        "👉 /buy - Premium Plan\n"
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
        "🎉 អ្នកបានចូល FREE PLAN\n"
        "📌 អាចដាក់បាន 1 Page"
    )

# =====================
# BUY PLAN
# =====================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(
        photo=InputFile(QR_IMAGE),
        caption="💳 3$/week | 11.5$/month | 120$/year\nSend screenshot after payment"
    )

# =====================
# HANDLE PAGE TEXT
# =====================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if text.startswith("/"):
        return

    if user_id not in users:
        await update.message.reply_text("សូមចុច /free មុន")
        return

    user = users[user_id]

    if user["plan"] == "free" and len(user["pages"]) >= 1:
        await update.message.reply_text("FREE plan limit 1 page only")
        return

    user["pages"].append(text)
    save_db()

    await update.message.reply_text("✅ បានរក្សាទុក Page")

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
        text=f"Payment request\nUser: {user.id}\n/approve {user.id} month"
    )

    await update.message.reply_text("Admin កំពុងពិនិត្យ...")

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
            await update.message.reply_text("plan error")
            return

        users[user_id] = {
            "plan": plan,
            "expire": time.time() + days_map[plan] * 86400,
            "pages": []
        }

        save_db()

        await context.bot.send_message(
            chat_id=int(user_id),
            text=f"✅ Approved! Plan: {plan}"
        )

        await update.message.reply_text("Approved!")

    except:
        await update.message.reply_text("Use: /approve user_id week|month|year")

# =====================
# STATUS + EXPIRE CHECK
# =====================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if user_id not in users:
        await update.message.reply_text("No plan")
        return

    user = users[user_id]

    if user["expire"] < time.time():
        await update.message.reply_text("❌ Expired! Please /buy")
        return

    await update.message.reply_text(
        f"Plan: {user['plan']}\nPages: {len(user['pages'])}"
    )

# =====================
# MAIN (FIXED TIMEOUT)
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

print("Bot running...")
app.run_polling()
