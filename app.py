import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

# -------------- CONFIG --------------

CONFIG = {
    "OPENROUTER_API_KEY": "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",
    "TELEGRAM_TOKEN": "7929112977:AAF06-TXEMxFH5PMdDj0RJzXizJqC_ADNwA"
}

# -------------- LOGGING --------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -------------- UI --------------

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌦️ Weather Data", callback_data='weather')],
        [InlineKeyboardButton("❓ Climate Q&A", callback_data='ask')],
        [InlineKeyboardButton("🌱 Eco Tips", callback_data='tips')],
        [InlineKeyboardButton("Exit", callback_data='exit')]
    ])

def weather_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌡️ Temperature", callback_data='temp')],
        [InlineKeyboardButton("🌧️ Rain", callback_data='rain')],
        [InlineKeyboardButton("Back", callback_data='back')]
    ])

# -------------- HELPERS --------------

def geocode_city(city_name):
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={city_name}&format=json&limit=1"
        resp = requests.get(url, headers={"User-Agent": "TelegramBot"})
        data = resp.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
        return None, None
    except Exception as e:
        logger.error(f"Geocode Error: {e}")
        return None, None


def fetch_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        resp = requests.get(url)
        data = resp.json()
        current = data.get('current_weather')
        return current if current else None
    except Exception as e:
        logger.error(f"Weather Fetch Error: {e}")
        return None


def ask_ai(question):
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        payload = {
            "model": "openai/gpt-3.5-turbo",
            "messages": [
                {"role": "system", "content": "You are a helpful expert on climate and environment."},
                {"role": "user", "content": question}
            ],
            "max_tokens": 300
        }
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        resp = requests.post(url, headers=headers, json=payload)
        if resp.ok:
            return resp.json()['choices'][0]['message']['content']
        return "AI failed to respond."
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "AI request failed."

# -------------- HANDLERS --------------

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🌍 Welcome to AeroBot!", reply_markup=main_menu()
    )


async def handle_button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'weather':
        await query.edit_message_text("Select Weather Info:", reply_markup=weather_menu())
    elif data == 'ask':
        await query.edit_message_text("Type your climate question:")
        context.user_data['mode'] = 'ask'
    elif data == 'tips':
        tips = await context.application.run_in_executor(None, ask_ai, "Give me 5 eco-friendly daily tips.")
        await query.edit_message_text(tips, reply_markup=main_menu())
    elif data == 'exit':
        await query.edit_message_text("🌟 Goodbye! Stay green!")
    elif data in ['temp', 'rain']:
        context.user_data['weather_type'] = data
        context.user_data['mode'] = 'weather'
        await query.edit_message_text("Enter your city:")
    elif data == 'back':
        await start(update, context)


async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    mode = context.user_data.get('mode')

    if mode == 'weather':
        lat, lon = geocode_city(text)
        if not lat:
            await update.message.reply_text("City not found.", reply_markup=main_menu())
            return
        weather = fetch_weather(lat, lon)
        if not weather:
            await update.message.reply_text("Weather unavailable.", reply_markup=main_menu())
            return

        if context.user_data['weather_type'] == 'temp':
            msg = f"🌡️ Temperature in {text}: {weather['temperature']}°C"
        else:
            msg = f"🌧️ Rainfall chance: {weather['precipitation']}%"

        await update.message.reply_text(msg, reply_markup=main_menu())

    elif mode == 'ask':
        answer = await context.application.run_in_executor(None, ask_ai, text)
        await update.message.reply_text(answer, reply_markup=main_menu())
    else:
        await start(update, context)

# -------------- MAIN --------------

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot started...")
    app.run_polling()

if __name__ == '__main__':
    main()
