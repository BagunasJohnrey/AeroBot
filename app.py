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

# OpenRouter API headers
OPENROUTER_HEADERS = {
    "Authorization": f"Bearer {CONFIG['OPENROUTER_API_KEY']}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://github.com/BagunasJohnrey/AeroBot",
    "X-Title": "AeroBot Climate Assistant"
}

# Setup Open-Meteo API client
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

def create_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌦️ Get Weather Data", callback_data='weather')],
        [InlineKeyboardButton("❓ Ask Climate Related Question", callback_data='ask')],
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
            text="Ask me anything about climate related information:"
        )
        context.user_data['mode'] = 'ask'
        context.user_data['previous_mode'] = 'ask'
    elif data == 'tips':
        tips = await get_eco_tips()
        context.user_data['previous_mode'] = 'tips'
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=tips,
            reply_markup=create_ask_again_menu('tips')
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
            text="Select disaster type:",
            reply_markup=create_disaster_menu()
        )
    elif data.startswith('prep_'):
        disaster_type = data.split('_')[1]
        guide = await get_disaster_prep(disaster_type)
        context.user_data['previous_mode'] = 'disaster'
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=guide,
            reply_markup=create_ask_again_menu('disaster')
        )
    elif data == 'exit':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Thank you for caring about our planet! 🌱"
        )
    elif data == 'back':
        await start(update, context)
    elif data in ['temp', 'precip', 'uv', 'wind']:
        context.user_data['weather_type'] = data
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="Which city?"
        )
        context.user_data['mode'] = 'weather'
        context.user_data['previous_mode'] = data

async def get_eco_tips():
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=OPENROUTER_HEADERS,
            json={
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You're an environmental expert. Provide 5 concise eco-friendly tips about reducing carbon footprint and sustainable living. Format as a numbered list with emojis."
                    },
                    {
                        "role": "user",
                        "content": "Give me eco tips"
                    }
                ],
                "max_tokens": 200
            }
        )
        response.raise_for_status()
        data = response.json()
        return "🌿 Eco Tips 🌿\n\n" + data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Failed to get eco tips: {str(e)}")
        logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return "⚠️ Couldn't fetch eco tips. Please try again later."

async def ask_ai(question: str):
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=OPENROUTER_HEADERS,
            json={
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You're a climate expert. Answer concisely in 2-3 sentences without emojis. Focus on SDG 13 (Climate Action)."
                    },
                    {
                        "role": "user",
                        "content": question
                    }
                ],
                "max_tokens": 150
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Failed to get AI response: {str(e)}")
        logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return "⚠️ Couldn't process your question. Please try again later."

async def get_climate_events(city: str = None):
    try:
        prompt = f"List 3 upcoming climate action events (e.g., cleanups, webinars) {f'in {city}' if city else 'globally'}. " \
                 "Include: Event name, date, location/link, and 1-sentence description. " \
                 "Format as a numbered list with bold titles."
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=OPENROUTER_HEADERS,
            json={
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [
                    {
                        "role": "system",
                        "content": prompt
                    }
                ],
                "max_tokens": 300
            }
        )
        response.raise_for_status()
        events = response.json()["choices"][0]["message"]["content"]
        return f"🌎 **Climate Events** 🌎\n\n{events}"
    except Exception as e:
        logger.error(f"Event fetch error: {str(e)}")
        logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return "⚠️ Couldn't fetch events. Try again later."

async def get_water_tips(region: str = None):
    try:
        prompt = "Give 5 concise water conservation tips" + \
                (f" for {region}." if region else " (general).") + \
                " Format as a numbered list with 💧 emoji."
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=OPENROUTER_HEADERS,
            json={
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [{"role": "system", "content": prompt}],
                "max_tokens": 200
            }
        )
        response.raise_for_status()
        tips = response.json()["choices"][0]["message"]["content"]
        return f"💧 **Water-Saving Tips** 💧\n\n{tips}"
    except Exception as e:
        logger.error(f"Water tips error: {str(e)}")
        logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return "⚠️ Failed to load tips. Please try later."

async def get_disaster_prep(disaster_type: str):
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=OPENROUTER_HEADERS,
            json={
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [
                    {
                        "role": "system",
                        "content": f"Provide a 3-step preparedness guide for {disaster_type} (e.g., hurricanes, wildfires). "
                                   "Include: 1) Pre-event preparation, 2) During-event actions, 3) Post-event recovery. "
                                   "Use 🔥/🌀/🌊/🌋 emojis where relevant. Keep each step under 2 sentences."
                    }
                ],
                "max_tokens": 250
            }
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return f"⚠️ **{disaster_type.capitalize()} Preparedness** ⚠️\n\n" + content
    except Exception as e:
        logger.error(f"Disaster prep error: {str(e)}")
        logger.error(f"Response: {response.text if 'response' in locals() else 'No response'}")
        return "⚠️ Couldn't fetch guide. Try again later."

async def get_full_location(city: str):
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=OPENROUTER_HEADERS,
            json={
                "model": "deepseek/deepseek-chat-v3-0324:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a location expert. Given a city name, respond ONLY with the complete location in format: 'City, Province/State, Country'. If unsure, return the input as is."
                    },
                    {
                        "role": "user",
                        "content": city
                    }
                ],
                "max_tokens": 50
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Failed to get location: {str(e)}")
        return city

async def get_weather(city: str, weather_type: str):
    full_location = await get_full_location(city)
    lat, lon = get_coordinates(full_location.split(',')[0].strip())
    
    if not lat:
        return f"Location not found: {full_location}"
    
    weather = fetch_weather(lat, lon)
    if not weather:
        return f"Weather data unavailable for {full_location}"
    
    # Format all values to 2 decimal places
    if weather_type == 'temp':
        return f"🌡️ Temperature in {full_location}: {weather['temp']:.2f}°C"
    elif weather_type == 'precip':
        return f"🌧️ Precipitation in {full_location}: {weather['precip']:.2f}mm"
    elif weather_type == 'uv':
        return f"☀️ UV Index in {full_location}: {weather['uv']:.2f} ({get_uv_level(weather['uv'])})"
    elif weather_type == 'wind':
        return f"💨 Wind Speed in {full_location}: {weather['wind']:.2f} km/h"

def get_uv_level(uv_index):
    uv_index = float(uv_index)
    if uv_index < 3: return "Low"
    elif uv_index < 6: return "Moderate"
    elif uv_index < 8: return "High"
    elif uv_index < 11: return "Very High"
    else: return "Extreme"

def get_coordinates(city: str):
    try:
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        response = requests_cache.CachedSession().get(url).json()
        if response.get('results'):
            return response['results'][0]['latitude'], response['results'][0]['longitude']
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
            reply_markup=create_ask_again_menu(weather_type)
        )
    elif mode == 'ask':
        response = await ask_ai(text)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=response,
            reply_markup=create_ask_again_menu('ask')
        )
    elif mode == 'events':
        events = await get_climate_events(text if text else None)
        await update.message.reply_text(
            events,
            reply_markup=create_ask_again_menu('events')
        )
    elif mode == 'water':
        tips = await get_water_tips(text if text else None)
        await update.message.reply_text(
            tips,
            reply_markup=create_ask_again_menu('water')
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
