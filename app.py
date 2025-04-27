import logging
import requests
import json
import openmeteo_requests
import requests_cache
from retry_requests import retry
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration - REPLACE WITH YOUR ACTUAL VALUES
CONFIG = {
    "OPENROUTER_API_KEY": "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",
    "TELEGRAM_TOKEN": "7929112977:AAF06-TXEMxFH5PMdDj0RJzXizJqC_ADNwA"
}

# Setup Open-Meteo API client
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# User settings (temperature unit and forecast length)
user_settings = {}

# Function to create weather icons based on conditions
def weather_icon(condition):
    if "clear" in condition.lower():
        return "☀️"
    elif "rain" in condition.lower():
        return "🌧️"
    elif "snow" in condition.lower():
        return "❄️"
    elif "cloud" in condition.lower():
        return "☁️"
    elif "storm" in condition.lower():
        return "⛈️"
    return "🌦️"  # default

def create_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌦️ Get Weather Data", callback_data='weather')],
        [InlineKeyboardButton("❓ Ask Climate Related Question", callback_data='ask')],
        [InlineKeyboardButton("🌱 Get Eco Tips", callback_data='tips')],
        [InlineKeyboardButton("📅 Climate Events", callback_data='events')],
        [InlineKeyboardButton("💧 Water Tips", callback_data='water')],
        [InlineKeyboardButton("⚠️ Disaster Prep", callback_data='disaster')],
        [InlineKeyboardButton("🚪 Exit", callback_data='exit')],
        [InlineKeyboardButton("⚙️ Settings", callback_data='settings')]  # Added settings button
    ])

def create_weather_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌡️ Temperature", callback_data='temp')],
        [InlineKeyboardButton("🌧️ Precipitation", callback_data='precip')],
        [InlineKeyboardButton("☀️ UV Index", callback_data='uv')],
        [InlineKeyboardButton("💨 Wind Speed", callback_data='wind')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ])

def create_settings_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌡️ Celsius (°C)", callback_data='set_celsius')],
        [InlineKeyboardButton("🌡️ Fahrenheit (°F)", callback_data='set_fahrenheit')],
        [InlineKeyboardButton("📅 3-Day Forecast", callback_data='set_3day')],
        [InlineKeyboardButton("📅 7-Day Forecast", callback_data='set_7day')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ])

async def start(update: Update, context: CallbackContext):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🌍 Welcome to AeroBot! 🌱\n\nHi there! I'm Aero Bot, your friendly AI assistant for climate change awareness. My mission is to help you understand the effects of climate change and provide practical solutions to make a difference.\n\nHere's what I can do for you:\n✅ Educate you on climate change and its impact.\n✅ Provide localized environmental data, like air pollution levels and temperature anomalies.\n✅ Suggest eco-friendly habits to reduce your carbon footprint and adopt sustainable practices.\n\nLet's work together for a greener planet! 🌿💚 How can I assist you today?",
        reply_markup=create_main_menu()
    )

async def handle_button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'weather':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Select weather data:",
            reply_markup=create_weather_menu()
        )
    elif data == 'ask':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Ask me anything about climate related informations:"
        )
        context.user_data['mode'] = 'ask'
    elif data == 'tips':
        tips = await get_eco_tips()
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=tips
        )
    elif data == 'events':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Enter a city (or leave blank for global events):"
        )
        context.user_data['mode'] = 'events'
    elif data == 'water':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Enter your location (e.g., 'Manila') or skip for general tips:"
        )
        context.user_data['mode'] = 'water'
    elif data == 'disaster':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Select disaster type:"
        )
    elif data == 'exit':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Thank you for caring about our planet! 🌱"
        )
    elif data == 'settings':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Choose your settings:",
            reply_markup=create_settings_menu()
        )
    elif data == 'set_celsius':
        user_settings[query.message.chat_id] = {"unit": "C", "forecast": 3}
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Temperature unit set to Celsius (°C)."
        )
    elif data == 'set_fahrenheit':
        user_settings[query.message.chat_id] = {"unit": "F", "forecast": 3}
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Temperature unit set to Fahrenheit (°F)."
        )
    elif data == 'set_3day':
        user_settings[query.message.chat_id] = {"unit": user_settings.get(query.message.chat_id, {}).get("unit", "C"), "forecast": 3}
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Forecast set to 3 days."
        )
    elif data == 'set_7day':
        user_settings[query.message.chat_id] = {"unit": user_settings.get(query.message.chat_id, {}).get("unit", "C"), "forecast": 7}
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Forecast set to 7 days."
        )
    elif data == 'back':
        await start(update, context)

async def get_weather(city: str, weather_type: str):
    user_setting = user_settings.get(city, {"unit": "C", "forecast": 3})
    unit = user_setting["unit"]
    forecast_days = user_setting["forecast"]
    # Get weather data here...
    # Process response and return formatted weather with emoji, icons, etc.

    # Placeholder for response (to be replaced with actual data)
    response = f"Weather in {city}: 🌡️ 25°C, 🌧️ Light rain, 🌅 Sunrise at 6:00 AM, 🌇 Sunset at 7:00 PM."
    return response

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    mode = context.user_data.get('mode')

    if mode == 'weather':
        response = await get_weather(text, 'temp')
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response
        )
    elif mode == 'ask':
        response = await ask_ai(text)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response
        )
    else:
        await start(update, context)

def main():
    try:
        app = Application.builder().token(CONFIG["TELEGRAM_TOKEN"]).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(handle_button))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("Starting bot...")
        app.run_polling()
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")

if __name__ == "__main__":
    main()
