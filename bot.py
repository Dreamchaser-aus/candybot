import os
import requests
from dotenv import load_dotenv
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from telegram.ext import JobQueue

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_API = os.getenv("BACKEND_API")
LEADERBOARD_API = os.getenv("LEADERBOARD_API")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

if not BOT_TOKEN or not BACKEND_API or not LEADERBOARD_API or not GROUP_CHAT_ID:
    raise Exception("❌ Please configure BOT_TOKEN, BACKEND_API, LEADERBOARD_API, GROUP_CHAT_ID in your .env file!")

def mask_phone(phone: str) -> str:
    if len(phone) >= 6:
        return phone[:4] + "*" * (len(phone) - 6) + phone[-2:]
    return phone

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inviter = None
    if context.args and len(context.args) > 0:
        inviter = context.args[0]
        context.user_data['inviter'] = inviter
    keyboard = [[KeyboardButton("📱 Send phone number", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "Click the button below to link your Telegram phone number:\n\n"
        "• Used for security verification and in-game privileges\n"
        "• Your info will never be leaked, only for identity verification",
        reply_markup=reply_markup
    )

# /share command
async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start={user_id}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Invite friends", url=invite_link)]
    ])
    await update.message.reply_text(
        f"🎉 Your exclusive invitation link:\n\n{invite_link}\n\n"
        "Invite friends to join and bind their phone number via your link to earn extra Token rewards!",
        reply_markup=keyboard
    )

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send /start to begin linking your phone number.\n"
        "If you encounter any issues, please contact the administrator."
    )

# Bind phone number
async def bind_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.contact:
            await update.message.reply_text("❌ No phone number received, please click the button again.")
            return

        user_id = update.effective_user.id
        phone = update.message.contact.phone_number
        username = update.effective_user.username or ""
        first_name = update.effective_user.first_name or ""
        last_name = update.effective_user.last_name or ""
        nickname = username if username else (first_name + (last_name if last_name else ""))

        inviter = context.user_data.get('inviter')
        payload = {
            "user_id": user_id,
            "phone": phone,
            "username": nickname
        }
        if inviter:
            payload["inviter"] = inviter

        resp = requests.post(
            BACKEND_API,
            json=payload,
            timeout=10
        )
        if resp.status_code == 200:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Play Game", web_app=WebAppInfo(url="https://candyfrontend-production.up.railway.app/"))]
            ])
            await update.message.reply_text(
                "✅ Successfully linked! Click the button below to start playing:",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(f"❌ Link failed [{resp.status_code}]: {resp.text}")

    except Exception as e:
        await update.message.reply_text(f"❌ Failed to link, please contact admin.\n{e}")

# /leaderboard command (manual check)
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_leaderboard(context, update.effective_chat.id)

# Auto send leaderboard (every 3 hours)
async def auto_send_leaderboard(context: ContextTypes.DEFAULT_TYPE):
    await send_leaderboard(context, GROUP_CHAT_ID)

# Leaderboard logic
async def send_leaderboard(context, chat_id):
    try:
        res = requests.get(LEADERBOARD_API, timeout=10)
        if res.status_code != 200:
            await context.bot.send_message(chat_id=chat_id, text="❌ Unable to fetch leaderboard, please try again later.")
            return

        data = res.json()
        msg = "🏆 Today's TOP 10 Leaderboard\n\n"
        for idx, entry in enumerate(data[:10]):
            masked = mask_phone(entry['phone'])
            score = entry['max_score']

            if idx == 0:
                prefix = "👑"
            elif idx == 1:
                prefix = "🥈"
            elif idx == 2:
                prefix = "🥉"
            elif idx == 9:
                prefix = "🔟"
            else:
                prefix = f"{idx + 1}️⃣"

            msg += f"{prefix} {masked} — {score} pts\n"

        msg += "\n🔥 Keep challenging and aim for the top!"
        await context.bot.send_message(chat_id=chat_id, text=msg)

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ Failed to get leaderboard: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('share', share_command))
    app.add_handler(CommandHandler('leaderboard', leaderboard_command))
    app.add_handler(MessageHandler(filters.CONTACT, bind_phone))

    job_queue: JobQueue = app.job_queue
    if job_queue:
        job_queue.run_repeating(auto_send_leaderboard, interval=3*60*60, first=0)
    else:
        print("⚠️ JobQueue not enabled, auto leaderboard sending will not work.")

    print("🤖 Bot started and running!")
    app.run_polling()

if __name__ == "__main__":
    main()
