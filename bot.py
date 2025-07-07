import os
import requests
from dotenv import load_dotenv
from telegram import (
    Update, KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_API = os.getenv("BACKEND_API")  # 例: https://candybackend-production.up.railway.app/user/bind

if not BOT_TOKEN or not BACKEND_API:
    raise Exception("❌ 环境变量 BOT_TOKEN 或 BACKEND_API 未设置！")

# /start 命令，自动识别邀请人参数
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

# /share 命令，生成专属邀请链接
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

# 绑定手机号处理
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

        inviter = context.user_data.get('inviter')  # 如果有，通过/start带进来的
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
            # 发送 WebApp 按钮（根据你的实际游戏入口）
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

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('share', share_command))
    app.add_handler(MessageHandler(filters.CONTACT, bind_phone))

    print("🤖 Bot started and running!")
    app.run_polling()

if __name__ == "__main__":
    main()
