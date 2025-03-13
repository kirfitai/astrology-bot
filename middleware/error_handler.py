from typing import Callable, Dict, Any, Awaitable
import logging
import traceback

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.event.bases import CancelHandler

from utils.error_logger import log_error
from config import ADMIN_TELEGRAM_ID

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(BaseMiddleware):
    """Middleware для обработки исключений во время обработки сообщений"""
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        """Перехватывает исключения и логирует их"""
        try:
            # Пропускаем событие через обработчик
            return await handler(event, data)
        except CancelHandler:
            # Пропускаем CancelHandler, так как это не ошибка
            raise
        except Exception as e:
            # Получаем информацию о событии
            if isinstance(event, Message):
                user_id = event.from_user.id
                chat_id = event.chat.id
                content_type = event.content_type
                content = event.text if event.text else f"[{content_type}]"
                event_type = "message"
            elif isinstance(event, CallbackQuery):
                user_id = event.from_user.id
                chat_id = event.message.chat.id if event.message else None
                content = event.data
                event_type = "callback_query"
            else:
                user_id = "unknown"
                chat_id = "unknown"
                content = "unknown"
                event_type = type(event).__name__
            
            # Контекст ошибки
            context = {
                "user_id": user_id,
                "chat_id": chat_id,
                "event_type": event_type,
                "content": content
            }
            
            # Логируем ошибку
            error_info = log_error(e, context)
            
            # Отправляем сообщение пользователю
            try:
                if isinstance(event, Message):
                    await event.answer(
                        "❌ Произошла ошибка при обработке вашего запроса. "
                        "Пожалуйста, попробуйте позже или воспользуйтесь другой функцией."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer("❌ Произошла ошибка", show_alert=True)
                    if event.message:
                        await event.message.answer(
                            "❌ Произошла ошибка при обработке вашего запроса. "
                            "Пожалуйста, попробуйте позже или воспользуйтесь другой функцией."
                        )
            except Exception as msg_error:
                logger.error(f"Не удалось отправить сообщение об ошибке пользователю: {msg_error}")
            
            # Отправляем уведомление администратору, если критическая ошибка
            if ADMIN_TELEGRAM_ID and hasattr(e, '__traceback__'):
                try:
                    stack_trace = "".join(traceback.format_tb(e.__traceback__))
                    admin_notification = (
                        f"❗️ Ошибка в боте:\n"
                        f"Пользователь: {user_id}\n"
                        f"Тип события: {event_type}\n"
                        f"Контент: {content[:50]}...\n\n"
                        f"Ошибка: {type(e).__name__}: {str(e)}\n\n"
                        f"Стек вызовов:\n{stack_trace[:300]}..."
                    )
                    # Используем бота из data для отправки сообщения админу
                    bot = data.get("bot")
                    if bot:
                        await bot.send_message(ADMIN_TELEGRAM_ID, admin_notification)
                except Exception as admin_error:
                    logger.error(f"Не удалось отправить уведомление администратору: {admin_error}")
            
            # Прерываем дальнейшую обработку
            raise CancelHandler()