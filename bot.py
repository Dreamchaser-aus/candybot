import os
import requests
from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# 加载环境变量（Railway 会自动注入）
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
BACKEND_API = os.getenv("BACKEND_API")

def start(update: Update, context: CallbackContext):
    keyboard = [[KeyboardButton("📱 发送手机号", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text(
        "点击下方按钮一键绑定你的 Telegram 手机号：\n\n"
        "• 用于安全验证和游戏权益保障\n"
        "• 信息绝不外泄，仅做身份识别",
        reply_markup=reply_markup
    )

def bind_phone(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    phone = update.message.contact.phone_number
    # 调用你的后端接口写入数据库
    try:
        resp = requests.post(BACKEND_API, json={"user_id": user_id, "phone": phone}, timeout=10)
        if resp.status_code == 200:
            update.message.reply_text("✅ 绑定成功！请返回游戏页面开始畅玩。")
        else:
            update.message.reply_text("❌ 绑定失败，请稍后重试。")
    except Exception as e:
        update.message.reply_text(f"❌ 绑定失败，请联系管理员。\n{e}")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("输入 /start 开始绑定手机号。\n如有问题请联系管理员。")

def main():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('help', help_command))
    dp.add_handler(MessageHandler(Filters.contact, bind_phone))

    print("🤖 Bot started and running!")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
