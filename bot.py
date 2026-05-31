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

# ================= CONFIG =================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PORT = int(os.getenv("PORT", 10000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # https://your-app.onrender.com/webhook

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

# ================= HELPERS =================
def is_facebook_link(text: str):
    return bool(re.match(r"https?://(www\.)?facebook\.com/.+", text))

def expired(user):
    return "expire" in user and time.time() > user["expire"]

def ensure_user(user_id):
    if user_id not in users:
        users[user_id] = {
            "plan": "free",
            "limit": 1,
            "expire": time.time() + 9999999999,
            "pages": []
        }
        save_db(users)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 សួស្តី! ប្រើ /free /buy /status")

# ================= FREE =================
async def free(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    ensure_user(user_id)

    users[user_id]["plan"] = "free"
    users[user_id]["limit"] = 1
    users[user_id]["expire"] = time.time() + 9999999999
    save_db(users)

    await update.message.reply_text("🎉 អ្នកបានប្រើ Free plan រួចហើយ (1 page)")

# ================= BUY =================
async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    qr_path = "qr.png"

    keyboard = [
        [InlineKeyboardButton("$3 → 10 pages", callback_data="buy:3")],
        [InlineKeyboardButton("$6 → 20 pages", callback_data="buy:6")],
        [InlineKeyboardButton("$12 → 30 pages", callback_data="buy:12")],
    ]

    caption = "💳 ស្កេន QR ដើម្បីបង់ប្រាក់\n\nជ្រើស Plan ខាងក្រោម៖"

    if os.path.exists(qr_path):
        with open(qr_path, "rb") as f:
            await update.message.reply_photo(
                photo=f,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        await update.message.reply_text(
            "⚠️ QR មិនមាន (qr.png missing)\n\n💳 ជ្រើស Plan:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ================= STATUS =================
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    ensure_user(user_id)

    user = users[user_id]

    await update.message.reply_text(
        f"📌 Plan: {user['plan']}\n"
        f"📄 Pages: {len(user['pages'])}/{user['limit']}"
    )

# ================= TEXT =================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    text = update.message.text

    if text.startswith("/"):
        return

    ensure_user(user_id)
    user = users[user_id]

    # expired check
    if expired(user):
        user["plan"] = "expired"
        user["limit"] = 0
        save_db(users)
        return await update.message.reply_text("❌ Plan អស់សុពលភាព")

    if not is_facebook_link(text):
        return await update.message.reply_text("❌ Link Facebook មិនត្រឹមត្រូវ")

    if len(user["pages"]) >= user["limit"]:
        return await update.message.reply_text("❌ អ្នកបានដល់ Limit ហើយ")

    user["pages"].append(text)
    save_db(users)

    await update.message.reply_text("✅ បានរក្សាទុករួចហើយ")

# ================= PAYMENT PHOTO =================
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
        caption=f"💰 Payment ពី user {user.id}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    await update.message.reply_text("📩 បានផ្ញើទៅ Admin")

# ================= APPROVE =================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.from_user.id != ADMIN_ID:
        return

    _, user_id, plan = q.data.split(":")
    plans = {"3": 10, "6": 20, "12": 30}

    ensure_user(user_id)

    # IMPORTANT: DON'T RESET DATA
    users[user_id]["plan"] = plan
    users[user_id]["limit"] = plans[plan]
    users[user_id]["expire"] = time.time() + 365 * 86400

    save_db(users)

    await context.bot.send_message(
        chat_id=int(user_id),
        text=f"🎉 អ្នកបានអនុម័ត Plan ${plan} រួចហើយ!"
    )

    await q.message.reply_text("✅ Done")

# ================= APP =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("free", free))
app.add_handler(CommandHandler("buy", buy))
app.add_handler(CommandHandler("status", status))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
app.add_handler(CallbackQueryHandler(approve))

# ================= WEBHOOK SERVER =================
async def webhook(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.process_update(update)
    return web.Response(text="ok")

async def health(request):
    return web.Response(text="Bot is running")

async def main():
    await app.initialize()
    await app.start()

    # set webhook
    await app.bot.set_webhook(WEBHOOK_URL)

    web_app = web.Application()
    web_app.router.add_post("/webhook", webhook)
    web_app.router.add_get("/", health)

    runner = web.AppRunner(web_app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    print("🚀 Bot running in WEBHOOK mode (stable)")

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
