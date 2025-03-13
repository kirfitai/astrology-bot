from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import logging
import json

from utils.error_logger import handle_exception
from states.user_states import SubscriptionStates, NatalChartStates
from utils.keyboards import (
    get_main_menu,
    get_subscription_menu,
    get_back_button
)
from database import operations
from config import SUBSCRIPTION_PRICES, ADMIN_TELEGRAM_ID, TG_STARS_MULTIPLIER
from services.payment_service import create_payment, telegram_stars_payment
from utils.error_logger import handle_exception, log_error
from handlers.start import back_to_menu_handler

logger = logging.getLogger(__name__)

@handle_exception
async def subscription_command(message: types.Message, state: FSMContext, **kwargs):
    """Обработчик команды /subscription и нажатия на кнопку подписки"""
    user_id = str(message.from_user.id)
    user = operations.get_user(user_id)
    
    # Проверяем, есть ли у пользователя действующая подписка
    has_subscription = False
    subscription_end = None
    
    if user and user.get("subscription_type") != "free" and user.get("subscription_end_date"):
        end_date = datetime.fromisoformat(user.get("subscription_end_date"))
        if end_date > datetime.now():
            has_subscription = True
            subscription_end = end_date
    
    # Проверяем, есть ли у пользователя незавершенный платеж
    has_pending_payment = operations.check_user_has_active_payment(user_id)
    
    if has_pending_payment:
        await message.answer(
            "⚠️ У вас есть незавершенный процесс оплаты. Пожалуйста, завершите его или отмените.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="❌ Отменить платеж", callback_data="cancel_payment")]
                ]
            )
        )
        return
    
    if has_subscription:
        # У пользователя есть действующая подписка
        days_left = (subscription_end - datetime.now()).days
        
        await message.answer(
            f"💎 Ваша подписка: {user.get('subscription_type')}\n\n"
            f"Действует до: {subscription_end.strftime('%d.%m.%Y')}\n"
            f"Осталось дней: {days_left}\n\n"
            "Спасибо, что выбрали премиум-возможности нашего бота!",
            reply_markup=get_subscription_menu(is_subscribed=True)
        )
    else:
        # У пользователя нет подписки
        messages_left = user.get("free_messages_left", 0) if user else 0
        
        # Создаем инлайн-клавиатуру с вариантами подписки
        # Сразу показываем все варианты подписки с ценами в звездах
        await message.answer(
            "💎 Premium подписка\n\n"
            f"У вас бесплатный план. Осталось сообщений: {messages_left}/3\n\n"
            "С Premium подпиской вы получите:\n"
            "• Безлимитное общение с ботом\n"
            "• Расширенный ежедневный гороскоп с детальным анализом всех сфер жизни\n"
            "• Безлимитные проверки совместимости с любым количеством людей\n"
            "• Еженедельные и ежемесячные прогнозы\n"
            "• Специальные аспекты планет и их влияние на вашу жизнь\n"
            "• Приоритетную поддержку\n\n"
            "Выберите план подписки:",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="✨ 1 неделя - 90 ⭐️", callback_data="direct_payment:1_week:90")],
                    [types.InlineKeyboardButton(text="✨ 1 месяц - 499 ⭐️", callback_data="direct_payment:1_month:499")],
                    [types.InlineKeyboardButton(text="✨ 1 год - 2999 ⭐️", callback_data="direct_payment:1_year:2999")],
                    [types.InlineKeyboardButton(text="Отмена", callback_data="cancel_payment")]
                ]
            )
        )
    
    await state.set_state(SubscriptionStates.selecting_plan)

@handle_exception
async def direct_payment_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs):
    """Обработчик прямого выбора плана и суммы подписки"""
    _, plan, stars_amount = callback.data.split(":")
    stars_amount = int(stars_amount)
    user_id = str(callback.from_user.id)
    
    await callback.answer()
    
    # Определяем продолжительность подписки в месяцах
    months = 1
    if plan == "3_month":
        months = 3
    elif plan == "1_year":
        months = 12
    
    # Сохраняем данные о выбранном плане
    await state.update_data(
        subscription_plan=plan,
        subscription_price=SUBSCRIPTION_PRICES.get(plan, 0),
        subscription_months=months,
        stars_amount=stars_amount
    )
    
    # Создаем транзакцию в БД
    transaction_id = operations.add_subscription_transaction(
        user_id,
        plan,
        SUBSCRIPTION_PRICES.get(plan, 0),
        "pending",
        "telegram_stars",
        months
    )
    
    # Сохраняем ID транзакции в состоянии
    await state.update_data(transaction_id=transaction_id)
    
    # Создаем и отправляем инвойс
    from aiogram.types import LabeledPrice
    
    # Определяем название плана для отображения
    plan_text = {
        "1_week": "1 неделю",
        "1_month": "1 месяц",
        "3_month": "3 месяца",
        "1_year": "1 год"
    }.get(plan, plan)
    
    # Подготавливаем данные для счета
    title = f"Подписка на {plan_text}"
    description = f"Подписка на астрологического бота на {plan_text}"
    payload = f"sub_{plan}_{transaction_id}"
    provider_token = ""  # Для Telegram Stars оставляем пустым
    currency = "XTR"    # XTR - это валюта Telegram Stars
    prices = [LabeledPrice(label="Подписка", amount=stars_amount)]
    
    try:
        # Отправляем инвойс напрямую
        await callback.message.answer_invoice(
            title=title,
            description=description,
            payload=payload,
            provider_token=provider_token,
            currency=currency,
            prices=prices,
            start_parameter=f"sub_{plan}"
        )
        
        # Обновляем транзакцию с ID инвойса
        operations.update_transaction_status(
            transaction_id, 
            "pending", 
            {"invoice_id": payload}
        )
        
        await state.set_state(SubscriptionStates.processing_payment)
    except Exception as e:
        logger.error(f"Ошибка при создании платежа звездами: {e}")
        
        await callback.message.answer(
            f"❌ Не удалось создать платеж: {e}\n\nПожалуйста, попробуйте позже.",
            reply_markup=get_main_menu()
        )
        
        # Отменяем транзакцию
        operations.update_transaction_status(transaction_id, "failed", {"error": str(e)})
        await state.clear()

@handle_exception
async def cancel_payment_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs):
    """Обработчик отмены платежа"""
    await callback.answer("Отменяем платеж...")
    
    user_id = str(callback.from_user.id)
    data = await state.get_data()
    transaction_id = data.get("transaction_id")
    
    if transaction_id:
        operations.update_transaction_status(transaction_id, "cancelled")
    else:
        operations.cancel_pending_transactions(user_id)
    
    await callback.message.answer(
        "❌ Платеж отменен. Вы можете попробовать снова в любое время.",
        reply_markup=get_main_menu()
    )
    
    await state.clear()

@handle_exception
async def premium_info_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs):
    """Обработчик нажатия на кнопку информации о премиум-подписке"""
    await callback.answer()
    
    # Перенаправляем пользователя сразу на выбор подписки
    await subscription_command(callback.message, state, **kwargs)

# Обработчики предпроверки платежа и успешного платежа
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    """Обработчик предварительной проверки платежа"""
    try:
        # Получаем данные платежа
        payload = pre_checkout_query.invoice_payload
        
        # Всегда подтверждаем платеж для демонстрации
        await pre_checkout_query.answer(ok=True)
        logger.info(f"Pre-checkout query approved: {payload}")
    except Exception as e:
        # В случае ошибки отклоняем платеж
        await pre_checkout_query.answer(
            ok=False,
            error_message="Произошла ошибка при обработке платежа. Пожалуйста, попробуйте позже."
        )
        logger.error(f"Error in pre_checkout: {e}")

async def process_successful_payment(message: types.Message, state: FSMContext):
    """Обработчик успешного платежа"""
    try:
        # Получаем данные о платеже
        payment_info = message.successful_payment
        payload = payment_info.invoice_payload
        total_amount = payment_info.total_amount
        currency = payment_info.currency
        
        user_id = str(message.from_user.id)
        
        logger.info(f"Successful payment from user {user_id}: {payload}, {total_amount} {currency}")
        
        # Парсим payload для получения плана подписки и ID транзакции
        if "_" in payload:
            parts = payload.split("_")
            if len(parts) >= 3:
                plan = parts[1]
                transaction_id = parts[2]
                
                # Активируем подписку
                result = await telegram_stars_payment.process_stars_transfer(user_id, plan, total_amount, transaction_id)
                
                if result.get("success"):
                    # Отправляем сообщение пользователю
                    await message.answer(
                        "✅ Оплата успешно получена! Ваша подписка активирована.\n\n"
                        "Спасибо за поддержку нашего бота. Теперь вам доступны все премиум-функции!",
                        reply_markup=get_main_menu()
                    )
                    
                    # Переходим в режим диалога
                    await state.set_state(NatalChartStates.dialog_active)
                else:
                    logger.error(f"Failed to process successful payment: {result.get('error')}")
                    
                    # Отправляем сообщение пользователю
                    await message.answer(
                        "⚠️ Оплата получена, но возникла ошибка при активации подписки.\n\n"
                        "Пожалуйста, свяжитесь с администратором.",
                        reply_markup=get_main_menu()
                    )
            else:
                logger.error(f"Invalid payload format: {payload}")
        else:
            logger.warning(f"Unknown payload format: {payload}")
            
            # Активируем подписку по умолчанию
            operations.update_user_subscription(user_id, "1_month", 1)
            
            await message.answer(
                "✅ Оплата успешно получена! Ваша подписка активирована.\n\n"
                "Спасибо за поддержку нашего бота. Теперь вам доступны все премиум-функции!",
                reply_markup=get_main_menu()
            )
            
            # Переходим в режим диалога
            await state.set_state(NatalChartStates.dialog_active)
    except Exception as e:
        logger.error(f"Error processing successful payment: {e}")
        
        # Отправляем сообщение пользователю
        await message.answer(
            "⚠️ Произошла ошибка при обработке платежа.\n\n"
            "Пожалуйста, свяжитесь с администратором.",
            reply_markup=get_main_menu()
        )

def register_handlers(dp: Dispatcher):
    """Регистрирует обработчики для работы с подписками"""
    # Команда /subscription и кнопка меню
    dp.message.register(subscription_command, Command("subscription"))
    dp.message.register(subscription_command, F.text == "💰 Подписка")
    
    # Обработчик прямого выбора плана и суммы подписки
    dp.callback_query.register(
        direct_payment_callback,
        lambda c: c.data.startswith("direct_payment:")
    )
    
    # Обработчик отмены платежа
    dp.callback_query.register(
        cancel_payment_callback,
        lambda c: c.data == "cancel_payment"
    )
    
    # Обработчик запроса информации о премиум-подписке
    dp.callback_query.register(
        premium_info_callback,
        lambda c: c.data == "premium_info"
    )
    
    # Обработчик перехода в меню подписки
    dp.callback_query.register(
        lambda c, state: subscription_command(c.message, state, **kwargs),
        lambda c: c.data == "subscribe_menu"
    )
    
    # Регистрация обработчиков платежей
    dp.pre_checkout_query.register(process_pre_checkout)
    dp.message.register(process_successful_payment, F.successful_payment)