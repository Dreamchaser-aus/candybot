import os
import requests
from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_API = os.getenv("BACKEND_API")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("📱 发送手机号", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        "点击下方按钮一键绑定你的 Telegram 手机号：\n\n"
        "• 用于安全验证和游戏权益保障\n"
        "• 信息绝不外泄，仅做身份识别",
        reply_markup=reply_markup
    )

async def bind_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    phone = update.message.contact.phone_number
    try:
        resp = requests.post(BACKEND_API, json={"user_id": user_id, "phone": phone}, timeout=10)
        if resp.status_code == 200:
            await update.message.reply_text("✅ 绑定成功！请返回游戏页面开始畅玩。")
        else:
            await update.message.reply_text("❌ 绑定失败，请稍后重试。")
    except Exception as e:
        await update.message.reply_text(f"❌ 绑定失败，请联系管理员。\n{e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("输入 /start 开始绑定手机号。\n如有问题请联系管理员。")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(MessageHandler(filters.CONTACT, bind_phone))

    print("🤖 Bot started and running!")
    app.run_polling()

if __name__ == "__main__":
    main()
