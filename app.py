# AeroBot - Climate Awareness Telegram Bot

import logging
import requests
import json
import openmeteo_requests
import requests_cache
from retry_requests import retry
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration ---
CONFIG = {
    "OPENROUTER_API_KEY": "sk-or-v1-f188312ce0cdc28906ee5deb89004b1b0345b5657ec18a2f9666f684a289f64esk-or-v1-1b95557fab541e3aee5b8c7f6f739a5bbc85015257b120a9aa4948895f83428a",
    "TELEGRAM_TOKEN": "7929112977:AAF06-TXEMxFH5PMdDj0RJzXizJqC_ADNwA"
}

# --- Open-Meteo Setup ---
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# --- Menus ---
def create_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌦️ Get Weather Data", callback_data='weather')],
        [InlineKeyboardButton("❓ Ask Climate Question", callback_data='ask')],
        [InlineKeyboardButton("🌱 Get Eco Tips", callback_data='tips')],
        [InlineKeyboardButton("📅 Climate Events", callback_data='events')],
        [InlineKeyboardButton("💧 Water Tips", callback_data='water')],
        [InlineKeyboardButton("⚠️ Disaster Prep", callback_data='disaster')],
        [InlineKeyboardButton("🚪 Exit", callback_data='exit')]
    ])

def create_weather_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌡️ Temperature", callback_data='temp')],
        [InlineKeyboardButton("🌧️ Precipitation", callback_data='precip')],
        [InlineKeyboardButton("☀️ UV Index", callback_data='uv')],
        [InlineKeyboardButton("💨 Wind Speed", callback_data='wind')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ])

def create_disaster_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Wildfires", callback_data='prep_wildfire')],
        [InlineKeyboardButton("🌀 Hurricanes", callback_data='prep_hurricane')],
        [InlineKeyboardButton("🌊 Floods", callback_data='prep_flood')],
        [InlineKeyboardButton("🌋 Earthquakes", callback_data='prep_earthquake')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ])

def create_ask_again_menu(previous_mode):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Ask Again", callback_data=previous_mode)],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back')]
    ])

# --- Start ---
async def start(update: Update, context: CallbackContext):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            "🌍 Welcome to AeroBot! 🌱\n\n"
            "Hi there! I'm AeroBot, your friendly AI assistant for climate awareness.\n\n"
            "✅ Educate you about climate change\n"
            "✅ Provide localized weather info\n"
            "✅ Suggest eco-friendly habits\n\n"
            "Let's make a greener planet together! 🌿💚"
        ),
        reply_markup=create_main_menu()
    )

# --- Button Handler ---
async def handle_button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'weather':
        await query.message.reply_text("Select weather data:", reply_markup=create_weather_menu())
    elif data == 'ask':
        context.user_data['mode'] = 'ask'
        await query.message.reply_text("❓ Ask your climate-related question:")
    elif data == 'tips':
        tips = await get_eco_tips()
        context.user_data['previous_mode'] = 'tips'
        await query.message.reply_text(tips, reply_markup=create_ask_again_menu('tips'))
    elif data == 'events':
        context.user_data['mode'] = 'events'
        await query.message.reply_text("📍 Enter a city (or leave blank for global events):")
    elif data == 'water':
        context.user_data['mode'] = 'water'
        await query.message.reply_text("💧 Enter your location (or skip for general tips):")
    elif data == 'disaster':
        await query.message.reply_text("⚠️ Choose a disaster:", reply_markup=create_disaster_menu())
    elif data.startswith('prep_'):
        disaster = data.split('_')[1]
        guide = await get_disaster_prep(disaster)
        context.user_data['previous_mode'] = 'disaster'
        await query.message.reply_text(guide, reply_markup=create_ask_again_menu('disaster'))
    elif data == 'exit':
        await query.message.reply_text("Thanks for caring for Earth! 🌍🌱")
    elif data == 'back':
        await start(update, context)
    elif data in ['temp', 'precip', 'uv', 'wind']:
        context.user_data['mode'] = 'weather'
        context.user_data['weather_type'] = data
        await query.message.reply_text("🏙️ Which city?")

# --- Message Handler ---
async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    mode = context.user_data.get('mode')

    if mode == 'weather':
        weather_type = context.user_data.get('weather_type')
        response = await get_weather(text, weather_type)
        await update.message.reply_text(response, reply_markup=create_ask_again_menu(weather_type))
    elif mode == 'ask':
        answer = await ask_ai(text)
        await update.message.reply_text(answer, reply_markup=create_ask_again_menu('ask'))
    elif mode == 'events':
        events = await get_climate_events(text if text else None)
        await update.message.reply_text(events, reply_markup=create_ask_again_menu('events'))
    elif mode == 'water':
        tips = await get_water_tips(text if text else None)
        await update.message.reply_text(tips, reply_markup=create_ask_again_menu('water'))
    else:
        await start(update, context)

# --- External API Functions ---
async def ask_ai(question: str):
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {CONFIG['OPENROUTER_API_KEY']}"},
            json={
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [
                    {"role": "system", "content": "You're a climate expert. Answer in 2-3 sentences, no emojis."},
                    {"role": "user", "content": question}
                ]
            }
        )
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Error: {e}")
        return "⚠️ Couldn't process the question. Try later."

async def get_eco_tips():
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {CONFIG['OPENROUTER_API_KEY']}"},
            json={
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [{"role": "system", "content": "Give 5 eco-tips with emojis."}]
            }
        )
        return "🌱 Eco Tips 🌱\n\n" + response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Tips Error: {e}")
        return "⚠️ Couldn't fetch tips."

async def get_climate_events(city: str = None):
    try:
        system_prompt = (
            f"List 3 upcoming climate events {'in ' + city if city else 'globally'}. "
            "Each: event name, date, location/link, 1-line description. Bold titles."
        )
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {CONFIG['OPENROUTER_API_KEY']}"},
            json={"model": "deepseek/deepseek-chat-v3-0324:free", "messages": [{"role": "system", "content": system_prompt}]}
        )
        return "📅 Climate Events 📅\n\n" + response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Events Error: {e}")
        return "⚠️ Couldn't load events."

async def get_water_tips(region: str = None):
    try:
        prompt = f"Give 5 water-saving tips {'for ' + region if region else 'globally'} with 💧 emojis."
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {CONFIG['OPENROUTER_API_KEY']}"},
            json={"model": "deepseek/deepseek-chat-v3-0324:free", "messages": [{"role": "system", "content": prompt}]}
        )
        return "💧 Water Conservation Tips 💧\n\n" + response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Water Tips Error: {e}")
        return "⚠️ Couldn't fetch tips."

async def get_disaster_prep(disaster: str):
    try:
        prompt = f"Give 3-step guide for {disaster} disaster preparation (pre, during, post) using emojis."
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {CONFIG['OPENROUTER_API_KEY']}"},
            json={"model": "deepseek/deepseek-chat-v3-0324:free", "messages": [{"role": "system", "content": prompt}]}
        )
        return f"⚠️ {disaster.capitalize()} Preparedness ⚠️\n\n" + response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Disaster Prep Error: {e}")
        return "⚠️ Couldn't load guide."

async def get_weather(city: str, weather_type: str):
    full_location = await get_full_location(city)
    lat, lon = get_coordinates(full_location.split(',')[0].strip())

    if not lat:
        return f"⚠️ Location not found: {city}"

    weather = fetch_weather(lat, lon)
    if not weather:
        return f"⚠️ Weather unavailable for {full_location}"

    if weather_type == 'temp':
        return f"🌡️ Temperature: {weather['temp']:.2f}°C at {full_location}"
    elif weather_type == 'precip':
        return f"🌧️ Precipitation: {weather['precip']:.2f}mm at {full_location}"
    elif weather_type == 'uv':
        return f"☀️ UV Index: {weather['uv']:.2f} ({get_uv_level(weather['uv'])}) at {full_location}"
    elif weather_type == 'wind':
        return f"💨 Wind Speed: {weather['wind']:.2f} km/h at {full_location}"

async def get_full_location(city: str):
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {CONFIG['OPENROUTER_API_KEY']}"},
            json={"model": "deepseek/deepseek-chat-v3-0324:free", "messages": [{"role": "system", "content": "Full location of " + city}]}
        )
        return response.json()["choices"][0]["message"]["content"]
    except:
        return city

def get_coordinates(city: str):
    try:
        response = requests_cache.CachedSession().get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        ).json()
        if response.get('results'):
            return response['results'][0]['latitude'], response['results'][0]['longitude']
    except Exception as e:
        logger.error(f"Geo Error: {e}")
    return None, None

def fetch_weather(lat: float, lon: float):
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": ["temperature_2m", "precipitation", "uv_index", "wind_speed_10m"]
        }
        weather = openmeteo.weather_api("https://api.open-meteo.com/v1/forecast", params=params)[0]
        current = weather.Current()
        return {
            "temp": current.Variables(0).Value(),
            "precip": current.Variables(1).Value(),
            "uv": current.Variables(2).Value(),
            "wind": current.Variables(3).Value()
        }
    except Exception as e:
        logger.error(f"Weather Error: {e}")
        return None

def get_uv_level(uv_index):
    if uv_index < 3: return "Low"
    elif uv_index < 6: return "Moderate"
    elif uv_index < 8: return "High"
    elif uv_index < 11: return "Very High"
    return "Extreme"

# --- Main ---
def main():
    try:
        app = Application.builder().token(CONFIG['TELEGRAM_TOKEN']).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(handle_button))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        logger.info("🚀 Bot started!")
        app.run_polling()
    except Exception as e:
        logger.error(f"Startup Error: {e}")

if __name__ == "__main__":
    main()
