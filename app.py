import logging
import requests
import requests_cache
import openmeteo_requests
from retry_requests import retry
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, CallbackContext

# ----------------- CONFIGURATION -----------------

CONFIG = {
    "OPENROUTER_API_KEY": "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",
    "TELEGRAM_TOKEN": "7929112977:AAF06-TXEMxFH5PMdDj0RJzXizJqC_ADNwA"
}

# ----------------- LOGGING -----------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----------------- SETUP -----------------

cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

# ----------------- UI COMPONENTS -----------------

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌦️ Weather Data", callback_data='weather')],
        [InlineKeyboardButton("❓ Climate Q&A", callback_data='ask')],
        [InlineKeyboardButton("🌱 Eco Tips", callback_data='tips')],
        [InlineKeyboardButton("📅 Climate Events", callback_data='events')],
        [InlineKeyboardButton("💧 Water Tips", callback_data='water')],
        [InlineKeyboardButton("⚠️ Disaster Prep", callback_data='disaster')],
        [InlineKeyboardButton("🚪 Exit", callback_data='exit')]
    ])

def weather_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌡️ Temperature", callback_data='temp')],
        [InlineKeyboardButton("🌧️ Precipitation", callback_data='precip')],
        [InlineKeyboardButton("☀️ UV Index", callback_data='uv')],
        [InlineKeyboardButton("💨 Wind Speed", callback_data='wind')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ])

def disaster_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔥 Wildfires", callback_data='prep_wildfire')],
        [InlineKeyboardButton("🌀 Hurricanes", callback_data='prep_hurricane')],
        [InlineKeyboardButton("🌊 Floods", callback_data='prep_flood')],
        [InlineKeyboardButton("🌋 Earthquakes", callback_data='prep_earthquake')],
        [InlineKeyboardButton("🔙 Back", callback_data='back')]
    ])

def ask_again_menu(mode):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Ask Again", callback_data=mode)],
        [InlineKeyboardButton("🏠 Main Menu", callback_data='back')]
    ])

# ----------------- API HELPERS -----------------

async def ai_request(system_prompt: str, user_content: str, max_tokens: int = 300):
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {CONFIG['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                "max_tokens": max_tokens
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI Request Error: {e}")
        return "⚠️ Couldn't process your request. Try again later."

# ----------------- FEATURE FUNCTIONS -----------------

async def get_eco_tips():
    return "🌿 Eco Tips 🌿\n\n" + await ai_request(
        "You're an environmental expert. Provide 5 eco-friendly tips about sustainable living, in a numbered list with emojis.",
        "Give eco tips",
        200
    )

async def ask_ai(question: str):
    return await ai_request(
        "You are a climate expert. Answer concisely in 2-3 sentences without emojis. Focus on SDG 13 (Climate Action).",
        question,
        150
    )

async def get_climate_events(city: str = None):
    prompt = f"List 3 upcoming climate action events {f'in {city}' if city else 'globally'}. " \
             "Include: Event name, date, location/link, 1-sentence description. Use numbered list, bold event names."
    return "🌎 **Climate Events** 🌎\n\n" + await ai_request(prompt, "", 300)

async def get_water_tips(region: str = None):
    prompt = f"Give 5 water conservation tips for {region if region else 'general'} users, as a numbered list with 💧 emojis."
    return "💧 **Water-Saving Tips** 💧\n\n" + await ai_request(prompt, "", 200)

async def get_disaster_prep(disaster_type: str):
    prompt = f"Create a 3-step guide for {disaster_type} preparedness. " \
             "Use 🔥/🌀/🌊/🌋 emojis. Keep steps short (max 2 sentences each)."
    return f"⚠️ **{disaster_type.capitalize()} Preparedness** ⚠️\n\n" + await ai_request(prompt, "", 250)

async def get_full_location(city: str):
    prompt = "Given a city name, reply ONLY with 'City, Province/State, Country'. If unsure, repeat the input."
    return await ai_request(prompt, city, 50)

async def get_weather(city: str, weather_type: str):
    location = await get_full_location(city)
    lat, lon = get_coordinates(location.split(',')[0].strip())
    
    if not lat:
        return f"❌ Location not found: {location}"

    weather = fetch_weather(lat, lon)
    if not weather:
        return f"❌ Weather data unavailable for {location}"

    formats = {
        "temp": f"🌡️ Temperature in {location}: {weather['temp']:.2f}°C",
        "precip": f"🌧️ Precipitation in {location}: {weather['precip']:.2f} mm",
        "uv": f"☀️ UV Index in {location}: {weather['uv']:.2f} ({get_uv_level(weather['uv'])})",
        "wind": f"💨 Wind Speed in {location}: {weather['wind']:.2f} km/h"
    }
    return formats.get(weather_type, "Invalid weather type.")

def get_uv_level(uv_index):
    uv = float(uv_index)
    if uv < 3: return "Low"
    if uv < 6: return "Moderate"
    if uv < 8: return "High"
    if uv < 11: return "Very High"
    return "Extreme"

def get_coordinates(city: str):
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        resp = requests_cache.CachedSession().get(url).json()
        if results := resp.get('results'):
            return results[0]['latitude'], results[0]['longitude']
    except Exception as e:
        logger.error(f"Coordinate Error: {e}")
    return None, None

def fetch_weather(lat: float, lon: float):
    try:
        resp = openmeteo.weather_api(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "current": ["temperature_2m", "precipitation", "uv_index", "wind_speed_10m"]}
        )[0]
        curr = resp.Current()
        return {
            "temp": curr.Variables(0).Value(),
            "precip": curr.Variables(1).Value(),
            "uv": curr.Variables(2).Value(),
            "wind": curr.Variables(3).Value()
        }
    except Exception as e:
        logger.error(f"Weather Fetch Error: {e}")
        return None

# ----------------- HANDLERS -----------------

async def start(update: Update, context: CallbackContext):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🌍 Welcome to AeroBot! Let's build a greener future together! 🌿💚",
        reply_markup=main_menu()
    )

async def handle_button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == 'weather':
        await query.edit_message_text("Select weather info:", reply_markup=weather_menu())
    elif data == 'ask':
        await query.edit_message_text("Ask your climate question:")
        context.user_data['mode'] = 'ask'
    elif data == 'tips':
        tips = await get_eco_tips()
        await query.edit_message_text(tips, reply_markup=ask_again_menu('tips'))
    elif data == 'events':
        await query.edit_message_text("Enter a city for local events (or leave blank):")
        context.user_data['mode'] = 'events'
    elif data == 'water':
        await query.edit_message_text("Enter your region (or skip for general tips):")
        context.user_data['mode'] = 'water'
    elif data == 'disaster':
        await query.edit_message_text("Select disaster type:", reply_markup=disaster_menu())
    elif data.startswith('prep_'):
        guide = await get_disaster_prep(data.split('_')[1])
        await query.edit_message_text(guide, reply_markup=ask_again_menu('disaster'))
    elif data == 'exit':
        await query.edit_message_text("🌱 Thanks for caring about Earth! Goodbye!")
    elif data == 'back':
        await start(update, context)
    elif data in ['temp', 'precip', 'uv', 'wind']:
        context.user_data['weather_type'] = data
        await query.edit_message_text("Which city?")
        context.user_data['mode'] = 'weather'

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    mode = context.user_data.get('mode')

    if mode == 'weather':
        weather_type = context.user_data.get('weather_type')
        result = await get_weather(text, weather_type)
    elif mode == 'ask':
        result = await ask_ai(text)
    elif mode == 'events':
        result = await get_climate_events(text if text else None)
    elif mode == 'water':
        result = await get_water_tips(text if text else None)
    else:
        await start(update, context)
        return

    await update.message.reply_text(result, reply_markup=ask_again_menu(mode))

# ----------------- MAIN -----------------

def main():
    try:
        app = Application.builder().token(CONFIG["TELEGRAM_TOKEN"]).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(handle_button))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("Bot started successfully.")
        app.run_polling()
    except Exception as e:
        logger.error(f"Bot failed: {e}")

if __name__ == "__main__":
    main()
