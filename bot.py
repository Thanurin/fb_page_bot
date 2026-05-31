import os
import json
import time
import re
import threading
import asyncio

from aiohttp import web
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
PORT = int(os.getenv("PORT", 10000))

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

# ================= AUTO EXPIRE CHECK =================
def check_expired(user):
    if "expire" in user and time.time() > user["expire"]:
        return True
    return False

# ================= KHMER ONLY RESPONSES =================
MSG_START = "👋 សួស្តី!\n\n/free - គម្រោងឥតគិតថ្លៃ\n/buy - តម្លៃគម្រោង\n/status - ស្ថានភាព"
MSG_FREE = "🎉 អ្នកបានបើកគម្រោងឥតគិតថ្លៃ (១ page)"
MSG_BUY = "💳 តម្លៃគម្រោង៖\n\n$3 → 10 pages\n$6 → 20 pages\n$12 → 30 pages\n\nផ្ញើរូបបង់ប្រាក់មក 📩"

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG_START)

async def free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    users[user_id] = {
        "plan": "free",
        "limit": 1,
        "expire": time.time() + 9999999999,
        "pages": []
    }

    save_db(users)
    await update.message.reply_text(MSG_FREE)

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MSG_BUY)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)

    if user_id not in users:
        return await update.message.reply_text("❌ អ្នកមិនទាន់មានគម្រោង")

    user = users[user_id]

    # ❗ CHECK EXPIRE HERE
    if check_expired(user):
        del users[user_id]
        save_db(users)
        return await update.message.reply_text("⛔ គម្រោងរបស់អ្នកបានផុតកំណត់")

    await update.message.reply_text(
        f"📌 គម្រោង: {user['plan']}\n"
        f"📄 ចំនួន: {len(user['pages'])}/{user['limit']}"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if text.startswith("/"):
        return

    if user_id not in users:
        return await update.message.reply_text("⚠️ សូមប្រើ /free មុនសិន")

    user = users[user_id]

    # ❗ EXPIRE CHECK
    if check_expired(user):
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

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📩 បានទទួលការបង់ប្រាក់")

async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

# ================= BOT =================
def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("free", free))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(CommandHandler("status", status))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(approve_callback))

    print("🚀 Bot running in Khmer mode only...")
    app.run_polling(drop_pending_updates=True)

# ================= WEB SERVER =================
async def home(request):
    return web.Response(text="Bot is running")

def start_web():
    web_app = web.Application()
    web_app.router.add_get("/", home)

    runner = web.AppRunner(web_app)

    async def _run():
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", PORT)
        await site.start()

    asyncio.get_event_loop().run_until_complete(_run())

# ================= MAIN =================
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    start_web()
