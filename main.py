import logging

from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from bot.handlers import start, help_command, search, view_watchlist, \
    remove_from_watchlist_handler, button, \
    trending_command
from config import TELEGRAM_BOT_TOKEN

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("watchlist", view_watchlist))
    application.add_handler(CommandHandler("remove", remove_from_watchlist_handler))
    application.add_handler(CommandHandler('trending', trending_command))
    application.add_handler(CallbackQueryHandler(button))
    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()