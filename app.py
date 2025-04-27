import logging
import requests
import openmeteo_requests
import requests_cache
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
from openai import OpenAI

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "OPENROUTER_API_KEY": "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",
    "TELEGRAM_TOKEN": "7712985692:AAF7aAks7-jdKsJFMcg2AONaFHwyAAPhrzE"
}

# Setup Open-Meteo API client with cache
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
openmeteo = openmeteo_requests.Client(session=cache_session)

# Create OpenAI client for AI functionality
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=CONFIG["OPENROUTER_API_KEY"]
)

# Eco tips database
ECO_TIPS = [
    "💧 Fix leaky faucets - a dripping tap can waste 15 liters of water a day!",
    "🌱 Plant native species - they require less water and maintenance.",
    "♻️ Use reusable bags when shopping to reduce plastic waste.",
    "🚲 Walk or bike for short trips instead of driving to reduce emissions.",
    "🌞 Use natural light during the day to save electricity.",
    "🥕 Reduce food waste by planning meals and storing food properly.",
    "🚿 Take shorter showers - cutting just 1 minute can save ~10 liters of water.",
    "🌳 Plant trees - they absorb CO2 and provide shade to reduce cooling needs.",
    "🛒 Buy local produce to reduce transportation emissions.",
    "🔌 Unplug electronics when not in use to prevent 'phantom' energy drain."
]

WATER_CONSERVATION_TIPS = [
    "🚰 Install low-flow showerheads and faucet aerators to reduce water use by 30%.",
    "🍽️ Only run dishwashers and washing machines with full loads.",
    "🚗 Wash your car with a bucket instead of a hose to save water.",
    "🚽 Consider installing a dual-flush toilet to reduce water usage.",
    "🌧️ Collect rainwater for watering plants and gardens.",
    "🚿 Turn off the tap while brushing your teeth or shaving.",
    "🌱 Water plants early in the morning or late in the evening to reduce evaporation.",
    "❄️ Defrost food in the refrigerator instead of running water over it.",
    "🚜 Use mulch in gardens to retain soil moisture and reduce watering needs.",
    "💦 Reuse pasta or vegetable cooking water to water plants (after cooling)."
]

DISASTER_TIPS = {
    "typhoon": [
        "🌀 Secure loose outdoor items that could become projectiles in high winds.",
        "🏠 Know your evacuation routes and nearest shelters.",
        "📱 Keep devices charged and have backup power sources ready.",
        "💧 Store at least 3 days' worth of water (4 liters per person per day).",
        "🛒 Stock up on non-perishable food and essential medications.",
        "🪟 Board up windows or use storm shutters if available.",
        "📻 Keep a battery-powered radio for weather updates.",
        "🚗 Fill your gas tank in case evacuation is necessary.",
        "💵 Have some cash on hand as ATMs may not work during power outages.",
        "🧳 Prepare an emergency kit with first aid supplies, flashlight, and important documents."
    ],
    "earthquake": [
        "🛌 Practice 'Drop, Cover, and Hold On' - the safest action during quakes.",
        "📚 Secure heavy furniture and appliances to walls.",
        "🔦 Keep flashlights and shoes near your bed (broken glass is common).",
        "🧯 Know how to turn off gas, water, and electricity in your home.",
        "🏠 Identify safe spots in each room (under sturdy tables, against interior walls).",
        "🚪 Keep hallways and exits clear of obstructions.",
        "📱 Designate an out-of-area contact for family communications.",
        "🛒 Maintain emergency supplies for at least 3 days.",
        "🚫 Avoid doorways - they're no stronger than other parts of modern houses.",
        "🏢 After shaking stops, check for gas leaks and structural damage before re-entering buildings."
    ],
    "flood": [
        "🏠 Know if your property is in a flood-prone area.",
        "🛒 Keep sandbags and plastic sheeting for emergency flood protection.",
        "🚗 Never drive through floodwaters - just 15cm can sweep away a car.",
        "🔌 Turn off electricity at the main switch if flooding is imminent.",
        "📈 Move valuables and important documents to higher levels.",
        "💧 Disconnect electrical appliances and don't touch them if wet.",
        "🚣 Have an evacuation plan that doesn't rely on roads that may flood.",
        "🌧️ Stay informed about local weather and flood warnings.",
        "🚫 Avoid walking through floodwaters - they may be contaminated or hide dangers.",
        "🏘️ After a flood, clean and disinfect everything that got wet to prevent mold."
    ],
    "wildfire": [
        "🔥 Create a 30-foot defensible space around your home by clearing flammable vegetation.",
        "🚪 Use fire-resistant materials for roofing and exterior walls.",
        "🚗 Keep your car fueled and facing outward for quick evacuation.",
        "🧯 Have fire extinguishers and know how to use them.",
        "🛒 Prepare a 'go bag' with essentials (meds, documents, N95 masks).",
        "🌬️ Be aware of weather conditions - hot, dry, and windy increases fire risk.",
        "🚫 Avoid activities that could spark fires during high-risk periods.",
        "📱 Sign up for local emergency alerts.",
        "🏠 Close all windows, vents, and doors if wildfire approaches.",
        "🚪 Know multiple evacuation routes as roads may become blocked."
    ]
}

PAST_CLIMATE_EVENTS = [
    "🌋 1815: Mount Tambora eruption caused the 'Year Without a Summer' with global temperature drops.",
    "❄️ 1600-1850: Little Ice Age brought colder temperatures to Europe and North America.",
    "🔥 1930s: Dust Bowl in the US caused by drought and poor farming practices.",
    "🌀 1970: Bhola Cyclone killed ~500,000 in Bangladesh (deadliest tropical cyclone).",
    "🌊 2004: Indian Ocean tsunami killed ~230,000 people across 14 countries.",
    "🌪️ 2005: Hurricane Katrina caused $125 billion in damage in the US.",
    "🔥 2019-2020: Australian bushfires burned ~18 million hectares.",
    "🌡️ 2016: Hottest year on record globally at the time (since surpassed).",
    "🏔️ 2023: Glacier melt reached record levels in the Alps.",
    "🌧️ 2022: Pakistan floods submerged 1/3 of the country, affecting 33 million people."
]

# Weather functions (as provided)
async def get_temperature(city: str):
    full_location = await get_full_location(city)
    lat, lon = get_coordinates(full_location.split(',')[0].strip())

    if not lat:
        return f"Location not found: {full_location}"

    weather = fetch_weather(lat, lon)

    if not weather:
        return f"Weather data unavailable for {full_location}"

    return f"🌡️ Temperature in {full_location}: {weather['temp']:.2f}°C"

async def get_uv_index(city: str):
    full_location = await get_full_location(city)
    lat, lon = get_coordinates(full_location.split(',')[0].strip())

    if not lat:
        return f"Location not found: {full_location}"

    weather = fetch_weather(lat, lon)

    if not weather:
        return f"Weather data unavailable for {full_location}"

    return f"☀️ UV Index in {full_location}: {weather['uv']:.2f} ({get_uv_level(weather['uv'])})"

async def get_full_location(city: str):
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {CONFIG['OPENROUTER_API_KEY']}",
                "Content-Type": "application/json"
            },
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
        logger.error(f"Failed to get location: {e}")
        return city

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
        logger.error(f"Weather fetch error: {e}")
        return None

def get_uv_level(uv_index):
    if uv_index < 3:
        return "Low"
    elif uv_index < 6:
        return "Moderate"
    elif uv_index < 8:
        return "High"
    elif uv_index < 11:
        return "Very High"
    else:
        return "Extreme"

# AI-related functions
async def ai_chat(question: str) -> str:
    try:
        # Sending a request to OpenRouter's API to get a chat completion response
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional
                "X-Title": "<YOUR_SITE_NAME>",      # Optional
            },
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=[
                {
                    "role": "user",
                    "content": question
                }
            ]
        )

        # Extract and return the response
        response_message = completion.choices[0].message.content
        return response_message
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        return "Sorry, I'm having trouble processing your request right now."

# Telegram bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply(f"Hi {user.first_name}, I am AeroBot. I can help with climate awareness, weather updates, and more!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "I can assist you with:\n"
        "- Weather updates 🌡️\n"
        "- Climate change awareness 🌍\n"
        "- Eco-friendly tips ♻️\n"
        "- Disaster preparedness ⚠️"
    )
    await update.message.reply(help_text)

async def eco_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tip = random.choice(ECO_TIPS)
    await update.message.reply(tip)

async def water_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tip = random.choice(WATER_CONSERVATION_TIPS)
    await update.message.reply(tip)

async def disaster_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    event = context.args[0] if context.args else "earthquake"
    if event not in DISASTER_TIPS:
        await update.message.reply("Invalid event type. Choose from: typhoon, earthquake, flood, wildfire.")
    else:
        tip = random.choice(DISASTER_TIPS[event])
        await update.message.reply(tip)

# Running the bot
if __name__ == "__main__":
    application = Application.builder().token(CONFIG["TELEGRAM_TOKEN"]).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("eco_tips", eco_tips))
    application.add_handler(CommandHandler("water_tips", water_tips))
    application.add_handler(CommandHandler("disaster_tips", disaster_tips))

    application.run_polling()
