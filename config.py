import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TMDB_API_KEY = os.getenv('TMDB_API_KEY')

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./movie_bot.db')

# Scheduler configuration
WEEKLY_UPDATE_DAY = 'monday'
WEEKLY_UPDATE_TIME = '09:00'