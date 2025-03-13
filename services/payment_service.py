from aiogram import Bot
import logging
import json
import uuid
from datetime import datetime, timedelta
from database import operations
from config import SUBSCRIPTION_PRICES, TG_STARS_MULTIPLIER
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

async def create_payment(user_id, plan, payment_method, bot=None):
    """
    Создает платеж для подписки
    
    Args:
        user_id: ID пользователя
        plan: План подписки (например, '1_month', '3_month', '1_year')
        payment_method: Метод оплаты ('tribute' или 'telegram_stars')
        bot: Экземпляр бота (для методов оплаты, требующих взаимодействия с API Telegram)
        
    Returns:
        dict: Результат создания платежа
    """
    try:
        # Получаем цену выбранного плана
        price = SUBSCRIPTION_PRICES.get(plan, 0)
        if not price:
            return {"success": False, "error": "Invalid subscription plan"}
            
        # Определяем продолжительность подписки в месяцах
        months = 1
        if plan == "3_month":
            months = 3
        elif plan == "1_year":
            months = 12
            
        if payment_method == "telegram_stars":
            # Вычисляем количество звезд на основе цены
            stars_amount = int(price * TG_STARS_MULTIPLIER)
            
            # Создаем запись о транзакции в базе данных со статусом "pending"
            transaction_id = operations.add_subscription_transaction(
                user_id,
                plan,
                price,
                "pending",
                "telegram_stars",
                months
            )
            
            return {
                "success": True,
                "payment_method": "telegram_stars",
                "stars_amount": stars_amount,
                "transaction_id": transaction_id
            }
            
        elif payment_method == "tribute":
            # Логика для платежной системы Tribute
            # ...
            return {"success": False, "error": "Payment method not implemented"}
            
        else:
            return {"success": False, "error": "Invalid payment method"}
            
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        return {"success": False, "error": str(e)}


class TelegramStarsPayment:
    """Класс для работы с платежами через Telegram Stars"""
    
    @staticmethod
    async def create_stars_payment_options(bot: Bot, chat_id: int, plan: str, stars_amount: int):
        """
        Отправляет пользователю кнопки для выбора периода подписки
        
        Args:
            bot: Экземпляр бота
            chat_id: ID чата пользователя
            plan: Тип подписки (например, "1_month")
            stars_amount: Количество звезд
            
        Returns:
            dict: Результат отправки сообщения
        """
        try:
            # Форматируем название плана для отображения
            plan_display = {
                "1_week": "1 Week...",
                "1_month": "1 Month...",
                "3_month": "3 Months...",
                "1_year": "1 Year..."
            }.get(plan, plan)
            
            # Отправляем сообщение с кнопками для подтверждения оплаты
            message = await bot.send_message(
                chat_id=chat_id,
                text=f"Для активации подписки необходимо отправить {stars_amount} звёзд.\nНажмите кнопку ниже, чтобы подтвердить:",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text=f"✨ {plan_display} - {stars_amount} ⭐️",
                                callback_data=f"confirm_stars:{plan}:{stars_amount}"
                            )
                        ],
                        [
                            types.InlineKeyboardButton(
                                text="Отмена",
                                callback_data="cancel_payment"
                            )
                        ]
                    ]
                )
            )
            
            return {
                "success": True,
                "message_id": message.message_id
            }
            
        except Exception as e:
            logger.error(f"Error creating stars payment options: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def send_payment_confirmation(bot: Bot, chat_id: int, plan: str, stars_amount: int):
        """
        Отправляет пользователю запрос на подтверждение оплаты звездами
        
        Args:
            bot: Экземпляр бота
            chat_id: ID чата пользователя
            plan: Тип подписки
            stars_amount: Количество звезд
            
        Returns:
            dict: Результат отправки сообщения
        """
        try:
            # Форматируем название плана для отображения
            plan_display_name = {
                "1_week": "Week of Premium!",
                "1_month": "Month of Premium!",
                "3_month": "3 Months of Premium!",
                "1_year": "Year of Premium!"
            }.get(plan, plan)
            
            # Отправляем подтверждение оплаты, используя формат как у бота Stellium
            message = await bot.send_message(
                chat_id=chat_id,
                text=f"{plan_display_name}\nThank you! This keeps our service shining.\nConfirm to send!",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            types.InlineKeyboardButton(
                                text=f"{stars_amount} ⭐️", 
                                pay=True
                            )
                        ]
                    ]
                )
            )
            
            # При успешной отправке сообщения
            return {
                "success": True,
                "message_id": message.message_id
            }
        
        except Exception as e:
            logger.error(f"Error sending payment confirmation: {e}")
            return {"success": False, "error": str(e)}