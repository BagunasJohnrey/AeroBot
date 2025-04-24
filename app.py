import os
import logging
import aiohttp
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "**Welcome to AeroBot!**\n\n"
        "I can help you with:\n"
        "• Climate change Q&A → /ask\n"
        "• Weather forecast → /weather\n"
        "• Eco-friendly tips → /tips\n"
        "• Disaster preparedness → /prepare\n"
        "• Climate events → /events\n\n"
        "Type a command to get started!",
        parse_mode=ParseMode.MARKDOWN
    )

# Ask Command (OpenRouter AI)
async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Please ask a question after /ask.")
        return

    question = " ".join(context.args)
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "openai/gpt-3.5-turbo",
                "messages": [{"role": "user", "content": question}]
            }
            async with session.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload) as response:
                result = await response.json()
                answer = result['choices'][0]['message']['content']
                await update.message.reply_text(answer)

    except Exception as e:
        logging.error(f"Error in /ask: {e}")
        await update.message.reply_text("Something went wrong. Please try again later.")

# Weather Command (Open-Meteo API)
async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        # Manila Coordinates
        lat, lon = 14.5995, 120.9842
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                current = data['current_weather']
                temp = current['temperature']
                wind = current['windspeed']
                desc = f"Temperature: {temp}°C\nWind Speed: {wind} km/h"

                await update.message.reply_text(f"**Current Weather in Manila**:\n{desc}", parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logging.error(f"Error in /weather: {e}")
        await update.message.reply_text("Unable to fetch weather data at the moment.")

# Placeholder Commands
async def tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Eco Tip: Use reusable bags and bottles to reduce plastic waste.")

async def prepare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Disaster Prep Tip: Always have a go-bag ready with essentials like water, flashlight, and medicine.")

async def events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Upcoming Event: Earth Day Celebration on April 22! Join local clean-up drives or plant trees.")

# Main
if __name__ == "__main__":
    if not BOT_TOKEN or not OPENROUTER_API_KEY:
        raise Exception("Missing environment variables.")

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("weather", weather))
    app.add_handler(CommandHandler("tips", tips))
    app.add_handler(CommandHandler("prepare", prepare))
    app.add_handler(CommandHandler("events", events))

    logging.info("AeroBot is running...")
    app.run_polling()
