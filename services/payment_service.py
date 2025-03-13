from aiogram import Bot
import logging
import json
import uuid
import time
import random
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
    async def create_stars_invoice(bot: Bot, user_id: int, stars_amount: int, purpose: str):
        """
        Создает инвойс для оплаты звездами
        
        Args:
            bot: Экземпляр бота
            user_id: ID пользователя
            stars_amount: Количество звезд
            purpose: Назначение платежа
            
        Returns:
            dict: Результат создания инвойса
        """
        try:
            # Генерируем уникальный ID для счета
            invoice_id = f"inv_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # Создаем и отправляем инвойс
            from aiogram.types import LabeledPrice
            
            # Подготавливаем данные для счета
            title = f"Подписка на {purpose}"
            description = f"Оплата {stars_amount} звезд за подписку на астрологического бота"
            payload = f"sub_{purpose}_{invoice_id}"
            provider_token = ""  # Для Telegram Stars оставляем пустым
            currency = "XTR"    # XTR - это валюта Telegram Stars
            prices = [LabeledPrice(label="Подписка", amount=stars_amount)]
            
            # Отправляем счет
            try:
                await bot.send_invoice(
                    chat_id=user_id,
                    title=title,
                    description=description,
                    payload=payload,
                    provider_token=provider_token,
                    currency=currency,
                    prices=prices
                )
                
                return {
                    "success": True,
                    "invoice_id": invoice_id,
                    "payment_url": None  # URL не требуется, так как счет отправляется напрямую
                }
            except Exception as e:
                logger.error(f"Error sending invoice: {e}")
                return {"success": False, "error": str(e)}
            
        except Exception as e:
            logger.error(f"Error creating stars invoice: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def process_stars_transfer(user_id, plan, stars_amount, transaction_id=None):
        """
        Обрабатывает перевод звезд
        
        Args:
            user_id: ID пользователя
            plan: Тип подписки
            stars_amount: Количество звезд
            transaction_id: ID транзакции
            
        Returns:
            dict: Результат обработки перевода
        """
        try:
            # В реальном сценарии здесь должна быть проверка статуса платежа через API Telegram
            # Для демонстрации просто имитируем успешную обработку
            
            # Определяем длительность подписки в месяцах
            months = 1
            if plan == "3_month":
                months = 3
            elif plan == "1_year":
                months = 12
                
            # Обновляем статус транзакции, если ID указан
            if transaction_id:
                success = operations.update_transaction_status(transaction_id, "completed")
                
                if success:
                    # Активируем подписку пользователю
                    operations.update_user_subscription(user_id, plan, months)
                    
                    return {
                        "success": True,
                        "message": f"Подписка {plan} активирована на {months} месяц(ев)"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to update transaction status"
                    }
            else:
                # Если ID транзакции не указан, создаем новую транзакцию
                price = SUBSCRIPTION_PRICES.get(plan, 0)
                transaction_id = operations.add_subscription_transaction(
                    user_id,
                    plan,
                    price,
                    "completed",
                    "telegram_stars",
                    months
                )
                
                return {
                    "success": True,
                    "transaction_id": transaction_id,
                    "message": f"Подписка {plan} активирована на {months} месяц(ев)"
                }
                
        except Exception as e:
            logger.error(f"Error processing stars transfer: {e}")
            return {"success": False, "error": str(e)}

# Создаем экземпляр класса для импорта
telegram_stars_payment = TelegramStarsPayment()