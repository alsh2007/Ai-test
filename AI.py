import logging
import time
import asyncio
import os
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import openai
from flask import Flask
from threading import Thread

# ====== Keep Alive ======
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()  # شغّل السيرفر ويب

# ====== البوت ======
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

user_chats = {}
CHAT_EXPIRE_SECONDS = 3600
REMINDER_SECONDS = 86400
forbidden_keywords = ["اختراق", "ديب ويب", "hacking", "porn", "اباحي", "crack"]

def is_safe_message(text: str) -> bool:
    return not any(word.lower() in text.lower() for word in forbidden_keywords)

async def send_reminders(app):
    while True:
        current_time = time.time()
        for user_id, data in user_chats.items():
            last = data["last_interaction"]
            if "reminder_sent" not in data and current_time - last > REMINDER_SECONDS:
                try:
                    chat_type = data.get("chat_type", "private")
                    if chat_type == "private":
                        await app.bot.send_message(chat_id=user_id, text="ها يمعود شنو نسيتني؟🦭")
                    else:
                        await app.bot.send_message(chat_id=user_id, text="ها يولد شنو نسيتوني؟🦭")
                    data["reminder_sent"] = True
                except Exception as e:
                    logger.error(f"Reminder failed for {user_id}: {e}")
        await asyncio.sleep(600)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("هلا! أنا بوت ذكاء اصطناعي مفيد. اسألني أي شي!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أوامر البوت:\n/start - البداية\n/help - المساعدة\n/about - معلومات عن البوت")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أنا بوت عربي، أجاوب على الأسئلة، أعطي نكت، وما أعطي محتوى غير قانوني.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_text = update.message.text
    chat_type = update.effective_chat.type

    if not is_safe_message(user_text):
        await update.message.reply_text("آسف، ما أقدر أجاوب على هذا السؤال 🚫")
        return

    if "مالك البوت" in user_text or "owner" in user_text:
        await update.message.reply_text("@x4hhh هو المالك مالتي")
        return

    if chat_type != "private":
        if f"@{context.bot.username}" not in user_text and not update.message.reply_to_message:
            return

    await update.message.chat.send_action(action=ChatAction.TYPING)

    if user_id not in user_chats:
        user_chats[user_id] = {
            "messages": [{"role": "system", "content": "أنت مساعد عربي مفيد، عفوي، يجاوب على كل الأسئلة، يرد باللهجات المختلفة، عند طلب نكتة يعطي نكتة جديدة كل مرة، لا تعطي محتوى غير قانوني أو إباحي."}],
            "last_interaction": time.time(),
            "chat_type": chat_type
        }

    user_chats[user_id]["last_interaction"] = time.time()
    user_chats[user_id]["chat_type"] = chat_type
    user_chats[user_id]["reminder_sent"] = False
    user_chats[user_id]["messages"].append({"role": "user", "content": user_text})

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=user_chats[user_id]["messages"],
            max_tokens=500,
            temperature=0.9
        )
        answer = response.choices[0].message['content']
        user_chats[user_id]["messages"].append({"role": "assistant", "content": answer})
        await update.message.reply_text(answer)
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("صار خطأ أثناء معالجة سؤالك 😔")

async def main():
    app_telegram = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("help", help_command))
    app_telegram.add_handler(CommandHandler("about", about_command))
    app_telegram.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app_telegram.job_queue.run_repeating(lambda _: asyncio.create_task(send_reminders(app_telegram)), interval=600, first=10)
    await app_telegram.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
