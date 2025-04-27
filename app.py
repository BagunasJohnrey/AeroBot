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

def create_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌦️ Get Weather Data", callback_data='weather')],
        [InlineKeyboardButton("🚪 Exit", callback_data='exit')]
    ])

def create_weather_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌡️ Temperature", callback_data='temp')],
        [InlineKeyboardButton("☀️ UV Index", callback_data='uv')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ])

async def start(update: Update, context: CallbackContext):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text = "🌍 Welcome to AeroBot! 🌱\n\nHi there! I'm Aero Bot, your friendly AI assistant for weather-related information. Let's get started!",
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
    elif data == 'temp':
        context.user_data['weather_type'] = 'temp'
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Which city?"
        )
    elif data == 'uv':
        context.user_data['weather_type'] = 'uv'
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Which city?"
        )
    elif data == 'exit':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Thank you for using AeroBot!"
        )
    elif data == 'back':
        await start(update, context)

async def get_weather(city: str, weather_type: str):
    lat, lon = await get_coordinates(city)
    if not lat:
        return f"Location not found: {city}"
    
    weather = await fetch_weather(lat, lon)
    if not weather:
        return f"Weather data unavailable for {city}"

    # Format all values to 2 decimal places
    if weather_type == 'temp':
        return f"🌡️ Temperature in {city}: {weather['temp']:.2f}°C"
    elif weather_type == 'uv':
        return f"☀️ UV Index in {city}: {weather['uv']:.2f} ({get_uv_level(weather['uv'])})"

def get_uv_level(uv_index):
    uv_index = float(uv_index)
    if uv_index < 3: return "Low"
    elif uv_index < 6: return "Moderate"
    elif uv_index < 8: return "High"
    elif uv_index < 11: return "Very High"
    else: return "Extreme"

async def get_coordinates(city: str):
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        response = requests_cache.CachedSession().get(url).json()
        if response.get('results'):
            return response['results'][0]['latitude'], response['results'][0]['longitude']
        return None, None
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return None, None

async def fetch_weather(lat: float, lon: float):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "uv_index"]
        }
        response = openmeteo.weather_api(url, params=params)[0]
        current = response.Current()
        return {
            "temp": current.Variables(0).Value(),
            "uv": current.Variables(1).Value(),
        }
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return None

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    mode = context.user_data.get('mode')

    if mode == 'weather':
        weather_type = context.user_data.get('weather_type')
        response = await get_weather(text, weather_type)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response,
            reply_markup=create_weather_menu()
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
