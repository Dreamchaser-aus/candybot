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
    raise Exception("❌ 请在 .env 文件中配置 BOT_TOKEN、BACKEND_API、LEADERBOARD_API、GROUP_CHAT_ID！")

def mask_phone(phone: str) -> str:
    if len(phone) >= 7:
        return phone[:3] + "****" + phone[-4:]
    return phone

# /start 命令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inviter = None
    if context.args and len(context.args) > 0:
        inviter = context.args[0]
        context.user_data['inviter'] = inviter
    keyboard = [[KeyboardButton("📱 发送手机号", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "点击下方按钮一键绑定你的 Telegram 手机号：\n\n"
        "• 用于安全验证和游戏权益保障\n"
        "• 信息绝不外泄，仅做身份识别",
        reply_markup=reply_markup
    )

# /share 命令
async def share_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = context.bot.username
    invite_link = f"https://t.me/{bot_username}?start={user_id}"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 点击邀请好友", url=invite_link)]
    ])
    await update.message.reply_text(
        f"🎉 你的专属邀请链接：\n\n{invite_link}\n\n"
        "邀请好友通过你的专属链接进入并绑定手机号，你将获得额外Token奖励！",
        reply_markup=keyboard
    )

# /help 命令
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 发送 /start 开始绑定手机号。\n"
        "如遇到任何问题请联系管理员。"
    )

# 绑定手机号
async def bind_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message or not update.message.contact:
            await update.message.reply_text("❌ 未收到手机号，请重新点击按钮。")
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
                [InlineKeyboardButton("🚀 进入游戏", web_app=WebAppInfo(url="https://candyfrontend-production.up.railway.app/"))]
            ])
            await update.message.reply_text(
                "✅ 绑定成功！点击下方按钮直接进入游戏：",
                reply_markup=keyboard
            )
        else:
            await update.message.reply_text(f"❌ 绑定失败 [{resp.status_code}]：{resp.text}")

    except Exception as e:
        await update.message.reply_text(f"❌ 绑定失败，请联系管理员。\n{e}")

# /leaderboard 命令（手动查看）
async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_leaderboard(context, update.effective_chat.id)

# 自动发送排行榜（每 3 小时）
async def auto_send_leaderboard(context: ContextTypes.DEFAULT_TYPE):
    await send_leaderboard(context, GROUP_CHAT_ID)

# 排行榜逻辑
async def send_leaderboard(context, chat_id):
    try:
        res = requests.get(LEADERBOARD_API, timeout=10)
        if res.status_code != 200:
            await context.bot.send_message(chat_id=chat_id, text="❌ 无法获取排行榜，请稍后再试。")
            return

        data = res.json()
        msg = "🏆 今日 TOP10 排行榜\n\n"
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

            msg += f"{prefix} {idx + 1}. {masked} — {score} 分\n"

        msg += "\n🔥 继续挑战，争取冲到榜首吧！"
        await context.bot.send_message(chat_id=chat_id, text=msg)

    except Exception as e:
        await context.bot.send_message(chat_id=chat_id, text=f"❌ 获取排行榜失败：{e}")

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
        print("⚠️ JobQueue 未启用，自动发送排行榜将无法运行。")

    print("🤖 Bot started and running!")
    app.run_polling()

if __name__ == "__main__":
    main()
