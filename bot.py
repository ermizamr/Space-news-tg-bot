import logging
import sqlite3
import requests
from datetime import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, CallbackContext, JobQueue
)

# === CONFIGURATION ===
BOT_TOKEN = "YOUR_BOT_TOKEN"
DB_PATH = "users.db"
NEWS_API = "https://api.spaceflightnewsapi.net/v4/articles/?limit=1"

# === DATABASE SETUP ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )
    """)
    conn.commit()
    conn.close()

# === HANDLERS ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
                   (user.id, user.username))
    conn.commit()
    conn.close()

    keyboard = [[
        InlineKeyboardButton("📰 Latest News", callback_data="news"),
        InlineKeyboardButton("ℹ️ About", callback_data="about")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 Welcome, {user.first_name}! I’ll keep you updated with space news.",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "news":
        article = get_latest_news()
        await query.edit_message_text(f"🛰️ *{article['title']}*\n{article['summary']}\n\n🔗 [Read more]({article['url']})",
                                       parse_mode='Markdown')
    elif query.data == "about":
        await query.edit_message_text("🌌 I’m a bot that brings you daily space news! Made with ❤️ by Ermo.")

# === NEWS FETCH ===
def get_latest_news():
    try:
        res = requests.get(NEWS_API)
        data = res.json()
        article = data['results'][0]
        return article
    except:
        return {"title": "Error", "summary": "Could not fetch news.", "url": ""}

# === DAILY JOB ===
async def daily_news_job(context: CallbackContext):
    article = get_latest_news()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    user_ids = cursor.fetchall()
    conn.close()

    for (user_id,) in user_ids:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"🌠 Daily Space News:\n*{article['title']}*\n{article['summary']}\n\n🔗 [Read more]({article['url']})",
                parse_mode='Markdown'
            )
        except:
            continue

# === MAIN ===
async def main():
    init_db()
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Schedule daily job at 9:00 AM
    app.job_queue.run_daily(daily_news_job, time(hour=9, minute=0))

    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
