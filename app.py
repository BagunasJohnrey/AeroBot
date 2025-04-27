import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from openai import OpenAI

# Initialize OpenRouter API client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to interact with OpenRouter API
def get_openrouter_response(user_message: str) -> str:
    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "<YOUR_SITE_URL>",  # Optional, replace with your site URL
                "X-Title": "<YOUR_SITE_NAME>",  # Optional, replace with your site title
            },
            extra_body={},
            model="deepseek/deepseek-chat-v3-0324:free",
            messages=[{"role": "user", "content": user_message}]
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling OpenRouter API: {e}")
        return "Sorry, I couldn't get a response from the server."

# Command to start the bot
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hello! I am your chatbot. Ask me anything.")

# Function to handle user messages
def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    response = get_openrouter_response(user_message)
    update.message.reply_text(response)

# Main function to start the bot
def main() -> None:
    # Replace with your Telegram bot token
    telegram_token = "7929112977:AAF06-TXEMxFH5PMdDj0RJzXizJqC_ADNwA"
    
    updater = Updater(telegram_token)

    dispatcher = updater.dispatcher

    # Register command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Start the bot
    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()
