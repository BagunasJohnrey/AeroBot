import logging
import requests
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

# Configuration - replace with your actual Telegram token
CONFIG = {
    "TELEGRAM_TOKEN": "YOUR_TELEGRAM_BOT_TOKEN"
}

# Setup Open-Meteo API client
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# Main Menu
def create_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌡️ Temperature", callback_data='temp')],
        [InlineKeyboardButton("🌧️ Precipitation", callback_data='precip')],
        [InlineKeyboardButton("☀️ UV Index", callback_data='uv')],
        [InlineKeyboardButton("💨 Wind Speed", callback_data='wind')]
    ])

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🌤️ Welcome to WeatherBot!\n\nGet real-time weather information easily.\nSelect what you want to know:",
        reply_markup=create_main_menu()
    )

async def handle_button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    selection = query.data
    context.user_data['weather_type'] = selection
    await query.message.reply_text("🌍 Please enter the city name:")

async def handle_message(update: Update, context: CallbackContext):
    city = update.message.text.strip()
    weather_type = context.user_data.get('weather_type')

    if not weather_type:
        await start(update, context)
        return

    response = await get_weather(city, weather_type)
    await update.message.reply_text(response, reply_markup=create_main_menu())

async def get_weather(city: str, weather_type: str):
    lat, lon = get_coordinates(city)
    if not lat:
        return f"❌ City not found: {city}"

    weather = fetch_weather(lat, lon)
    if not weather:
        return f"❌ Weather data unavailable for {city}"

    if weather_type == 'temp':
        return f"🌡️ Temperature in {city}: {weather['temp']:.2f}°C"
    elif weather_type == 'precip':
        return f"🌧️ Precipitation in {city}: {weather['precip']:.2f}mm"
    elif weather_type == 'uv':
        return f"☀️ UV Index in {city}: {weather['uv']:.2f} ({get_uv_level(weather['uv'])})"
    elif weather_type == 'wind':
        return f"💨 Wind Speed in {city}: {weather['wind']:.2f} km/h"
    else:
        return "❌ Invalid selection."

def get_coordinates(city: str):
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        response = requests_cache.CachedSession().get(url).json()
        if response.get('results'):
            result = response['results'][0]
            return result['latitude'], result['longitude']
        return None, None
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return None, None

def fetch_weather(lat: float, lon: float):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "precipitation", "uv_index", "wind_speed_10m"]
        }
        response = openmeteo.weather_api(url, params=params)[0]
        current = response.Current()
        return {
            "temp": current.Variables(0).Value(),
            "precip": current.Variables(1).Value(),
            "uv": current.Variables(2).Value(),
            "wind": current.Variables(3).Value()
        }
    except Exception as e:
        logger.error(f"Weather fetch error: {e}")
        return None

def get_uv_level(uv_index):
    uv_index = float(uv_index)
    if uv_index < 3: return "Low"
    elif uv_index < 6: return "Moderate"
    elif uv_index < 8: return "High"
    elif uv_index < 11: return "Very High"
    else: return "Extreme"

def main():
    app = Application.builder().token(CONFIG["TELEGRAM_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Starting WeatherBot...")
    app.run_polling()

if __name__ == "__main__":
    main()
