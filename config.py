import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Основные настройки
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "adminparol")

# Настройки базы данных
DB_FILE = os.getenv("DB_FILE", "astrology_bot.db")

# Настройки OpenAI
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2000"))
COST_PER_1000_TOKENS = float(os.getenv("COST_PER_1000_TOKENS", "0.002"))

# Настройки диалога
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES", "10"))

# Настройки подписок
FREE_MESSAGES_LIMIT = int(os.getenv("FREE_MESSAGES_LIMIT", "10"))
SUBSCRIPTION_PRICES = {
    "1_month": float(os.getenv("PRICE_1_MONTH", "4.99")),
    "3_month": float(os.getenv("PRICE_3_MONTH", "9.99")),
    "1_year": float(os.getenv("PRICE_1_YEAR", "29.99"))
}

# Настройки планировщика
DEFAULT_HOROSCOPE_TIME = os.getenv("DEFAULT_HOROSCOPE_TIME", "08:00")

# Пути к ephemeris
EPHE_PATH = os.getenv("EPHE_PATH", "ephemeris/")

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Настройки административной панели
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8080"))