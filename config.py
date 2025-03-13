import os
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

# Основные настройки
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
PREMIUM_CHANNEL_ID = os.getenv("PREMIUM_CHANNEL_ID", "")  # ID приватного канала с подпиской
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
FREE_MESSAGES_LIMIT = int(os.getenv("FREE_MESSAGES_LIMIT", "3"))
SUBSCRIPTION_PRICES = {
    "1_week": float(os.getenv("PRICE_1_WEEK", "0.99")),
    "1_month": float(os.getenv("PRICE_1_MONTH", "4.99")),
    "3_month": float(os.getenv("PRICE_3_MONTH", "9.99")),
    "1_year": float(os.getenv("PRICE_1_YEAR", "29.99"))
}

# Настройки платежных систем
TRIBUTE_API_KEY = os.getenv("TRIBUTE_API_KEY", "")
TRIBUTE_SECRET_KEY = os.getenv("TRIBUTE_SECRET_KEY", "")
TRIBUTE_PROJECT_ID = os.getenv("TRIBUTE_PROJECT_ID", "")
TG_STARS_MULTIPLIER = float(os.getenv("TG_STARS_MULTIPLIER", "100"))  # 100 звезд за 1 доллар

# Настройки планировщика
DEFAULT_HOROSCOPE_TIME = os.getenv("DEFAULT_HOROSCOPE_TIME", "08:00")

# Пути к ephemeris
EPHE_PATH = os.getenv("EPHE_PATH", "ephemeris/")

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = os.getenv("LOG_DIR", "logs")

# Настройки административной панели
ADMIN_PORT = int(os.getenv("ADMIN_PORT", "8080"))
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID", "")  # ID администратора в Telegram для уведомлений

# Настройки отчетов об ошибках
ERROR_REPORT_THRESHOLD = int(os.getenv("ERROR_REPORT_THRESHOLD", "5"))  # Порог для уведомления о повторяющихся ошибках