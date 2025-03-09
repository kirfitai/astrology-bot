# services/subscription_service.py
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from config import PREMIUM_CHANNEL_ID

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
    try:
        if not PREMIUM_CHANNEL_ID:
            logger.warning("PREMIUM_CHANNEL_ID не настроен в config.py")
            return False
            
        chat_member = await bot.get_chat_member(PREMIUM_CHANNEL_ID, user_id)
        
        # Проверяем статус пользователя в канале
        if chat_member.status in ['member', 'administrator', 'creator']:
            logger.info(f"Пользователь {user_id} имеет премиум-подписку через канал")
            return True
        
        logger.info(f"Пользователь {user_id} не подписан на премиум-канал (статус: {chat_member.status})")
        return False
        
    except TelegramAPIError as e:
        if "user not found" in str(e).lower():
            logger.info(f"Пользователь {user_id} не найден в премиум-канале")
        else:
            logger.error(f"Ошибка при проверке подписки на канал для пользователя {user_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка при проверке подписки: {e}")
        return False