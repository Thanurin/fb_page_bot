import os
import json
import time
import re
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

# ================= HANDLERS (UNCHANGED LOGIC) =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 សួស្តី!")

async def free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    users[user_id] = {"plan": "free", "limit": 1, "pages": []}
    save_db(users)
    await update.message.reply_text("Free plan enabled")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if user_id not in users:
        return await update.message.reply_text("Use /free first")

    if not is_facebook_link(text):
        return await update.message.reply_text("Invalid link")

    if len(users[user_id]["pages"]) >= users[user_id]["limit"]:
        return await update.message.reply_text("Limit reached")

    users[user_id]["pages"].append(text)
    save_db(users)

    await update.message.reply_text("Saved")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Payment received")

async def approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

# ================= SAFE START =================
async def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("free", free))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(approve_callback))

    await app.initialize()
    await app.start()

    # IMPORTANT: NO polling, NO webhook runner
    print("Bot started safely")

    await asyncio.Event().wait()


# ================= WEB SERVER (RENDER NEED THIS) =================
async def home(request):
    return web.Response(text="Bot is running")

async def main():
    bot_task = asyncio.create_task(run_bot())

    web_app = web.Application()
    web_app.router.add_get("/", home)

    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)

    await site.start()

    print("Web server started")

    await bot_task


if __name__ == "__main__":
    asyncio.run(main())
