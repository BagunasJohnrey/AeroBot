import logging
import requests
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
    "TELEGRAM_TOKEN": "7929112977:AAF06-TXEMxFH5PMdDj0RJzXizJqC_ADNwA"
}

# Setup Open-Meteo API client
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)

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
        text="🌍 Welcome to WeatherBot! 🌱\n\nHi there! I can provide you with weather information such as temperature and UV index. How can I assist you today?",
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
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Please enter a city to get the temperature:"
        )
        context.user_data['mode'] = 'temp'
    elif data == 'uv':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Please enter a city to get the UV index:"
        )
        context.user_data['mode'] = 'uv'
    elif data == 'exit':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Thank you for using WeatherBot! 🌱"
        )
    elif data == 'back':
        await start(update, context)

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    mode = context.user_data.get('mode')

    if mode == 'temp':
        response = await get_weather(text, 'temp')
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response,
            reply_markup=create_weather_menu()
        )
    elif mode == 'uv':
        response = await get_weather(text, 'uv')
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response,
            reply_markup=create_weather_menu()
        )
    else:
        await start(update, context)

async def get_weather(city: str, weather_type: str):
    lat, lon = await get_coordinates(city)
   
    if not lat:
        return f"Location not found: {city}"
   
    weather = await fetch_weather(lat, lon)
    if not weather:
        return f"Weather data unavailable for {city}"
   
    # Format the response based on the requested weather type
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
        response = requests_cache.CachedSession().get(url, params=params).json()
        if response.get("current"):
            current = response["current"]
            return {
                "temp": current["temperature_2m"],
                "uv": current["uv_index"]
            }
        return None
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return None

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
