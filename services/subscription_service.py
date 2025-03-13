# services/subscription_service.py
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

async def check_channel_subscription(user_id, bot: Bot):
    """
    Проверяет, подписан ли пользователь на премиум-канал
    
    Args:
        user_id: ID пользователя в Telegram
        bot: Экземпляр бота
        
    Returns:
        bool: True, если пользователь подписан, иначе False
    """
    # Всегда возвращаем False, так как мы убираем проверку подписки на канал
    # и переходим на прямые платежи через Telegram Stars
    return False