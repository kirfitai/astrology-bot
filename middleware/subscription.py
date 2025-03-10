from typing import Callable, Dict, Any, Awaitable
from datetime import datetime
import logging

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.event.bases import CancelHandler

from database import operations
from services.subscription_service import check_channel_subscription
from config import PREMIUM_CHANNEL_ID

logger = logging.getLogger(__name__)

class SubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки подписки пользователя и учета сообщений"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """
        Выполняет проверку подписки и ограничений для пользователя.
        
        За исключением команд /start, /help, /subscription, /reset 
        и кнопок подписки, проверяет:
        1. Наличие действующей подписки
        2. Наличие подписки на премиум-канал
        3. Наличие бесплатных сообщений
        """
        # Определяем User ID в зависимости от типа события
        if isinstance(event, Message):
            user_id = str(event.from_user.id)
            text = event.text
            message = event
        elif isinstance(event, CallbackQuery):
            user_id = str(event.from_user.id)
            text = event.data
            message = event.message
        else:
            # Пропускаем другие типы событий
            return await handler(event, data)
        
        # Проверяем, нужно ли пропустить проверку для этого сообщения/callback
        if self._should_skip_check(text):
            return await handler(event, data)
        
        # Получаем данные пользователя
        user = operations.get_user(user_id)
        if not user:
            # Если пользователя нет в базе, создаем его
            if isinstance(event, Message):
                username = event.from_user.username or ""
                first_name = event.from_user.first_name or ""
                last_name = event.from_user.last_name or ""
                operations.create_user(user_id, username, first_name, last_name)
            return await handler(event, data)
        
        # Проверяем подписку на премиум-канал
        bot = data.get("bot")
        has_channel_subscription = await check_channel_subscription(user_id, bot)
        
        # Если пользователь подписан на канал, обновляем его статус подписки
        if has_channel_subscription and user.get("subscription_type") == "free":
            operations.update_user_subscription(user_id, "channel_premium", 1)  # Обновляем на 1 месяц
            logger.info(f"Пользователь {user_id} получил премиум через подписку на канал")
        
        # Проверяем платную подписку напрямую
        if user.get("subscription_type") != "free":
            # Проверяем, не истекла ли подписка
            if user.get("subscription_end_date"):
                end_date = datetime.fromisoformat(user.get("subscription_end_date"))
                if end_date > datetime.now():
                    # Подписка активна, пропускаем
                    return await handler(event, data)
                # Подписка истекла, но пользователь может быть подписан на канал
                elif not has_channel_subscription:
                    # Обновляем статус подписки, если нет подписки на канал
                    operations.update_user_subscription(user_id, "free")
        
        # Если пользователь подписан на канал, пропускаем проверку лимита сообщений
        if has_channel_subscription:
            return await handler(event, data)
        
        # Если это не команда и не callback, и число бесплатных сообщений исчерпано
        if isinstance(event, Message) and not self._is_command(text) and user.get("free_messages_left", 0) <= 0:
            if not self._is_subscription_related(text):
                # Отправляем сообщение о превышении лимита
                channel_name = PREMIUM_CHANNEL_ID.replace("@", "")
                channel_link = f"https://t.me/{channel_name}"
                
                await message.answer(
                    "⚠️ Вы исчерпали лимит бесплатных сообщений.\n\n"
                    "Для продолжения общения с ботом приобретите подписку или "
                    "подпишитесь на наш премиум-канал!",
                    reply_markup=message.bot.types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [message.bot.types.InlineKeyboardButton(
                                text="💫 Подписаться на премиум-канал", 
                                url=channel_link
                            )],
                            [message.bot.types.InlineKeyboardButton(
                                text="💎 Узнать о премиум-подписке", 
                                callback_data="premium_info"
                            )]
                        ]
                    )
                )
                # Предотвращаем дальнейшую обработку
                raise CancelHandler()
        
        # Пропускаем сообщение дальше
        return await handler(event, data)
    
    def _should_skip_check(self, text: str) -> bool:
        """Проверяет, следует ли пропустить проверку для данного текста"""
        if not text:
            return True
        
        # Всегда пропускаем эти команды
        allowed_commands = ['/start', '/help', '/subscription', '/reset', '/menu']
        if any(text.startswith(cmd) for cmd in allowed_commands):
            return True
        
        # Пропускаем callback'и, связанные с подпиской
        if isinstance(text, str) and any(text.startswith(prefix) for prefix in ['subscribe:', 'payment:', 'premium_info']):
            return True
        
        return False
    
    def _is_command(self, text: str) -> bool:
        """Проверяет, является ли текст командой"""
        if not text:
            return False
        return text.startswith('/')
    
    def _is_subscription_related(self, text: str) -> bool:
        """Проверяет, связан ли текст с подпиской"""
        if not text:
            return False
        
        subscription_keywords = ['подписка', 'подписки', 'premium', 'премиум', 'оплата', 'платеж']
        return any(keyword in text.lower() for keyword in subscription_keywords)