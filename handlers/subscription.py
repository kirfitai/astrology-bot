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
    get_subscription_plans,
    get_payment_methods,
    get_back_button
)
from database import operations
from config import SUBSCRIPTION_PRICES, ADMIN_TELEGRAM_ID, PREMIUM_CHANNEL_ID
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
        
        await message.answer(
            "💰 Управление подпиской\n\n"
            f"У вас бесплатный план. Осталось сообщений: {messages_left}/3\n\n"
            "С Premium подпиской вы получите:\n"
            "• Безлимитное общение с ботом\n"
            "• Расширенный ежедневный гороскоп\n"
            "• Безлимитные проверки совместимости\n"
            "• Еженедельные и ежемесячные прогнозы\n"
            "• Расширенный анализ всех сфер жизни",
            reply_markup=get_subscription_menu(is_subscribed=False)
        )
    
    await state.set_state(SubscriptionStates.selecting_plan)

@handle_exception
async def subscription_action_handler(message: types.Message, state: FSMContext, **kwargs):
    """Обработчик выбора действия в меню подписки"""
    if await back_to_menu_handler(message, state):
        return
    
    user_id = str(message.from_user.id)
    user = operations.get_user(user_id)
    
    if message.text == "💎 Купить подписку":
        await message.answer(
            "Выберите план подписки:",
            reply_markup=get_subscription_plans()
        )
    
    elif message.text == "❓ Преимущества подписки":
        await message.answer(
            "💎 Преимущества Premium подписки:\n\n"
            "• Безлимитное общение с ботом — задавайте любые вопросы о вашей натальной карте и получайте "
            "подробные ответы без ограничений\n\n"
            "• Расширенный ежедневный гороскоп — получайте детальный гороскоп с анализом всех сфер жизни: "
            "любовь, карьера, здоровье, финансы и личностный рост\n\n"
            "• Безлимитные проверки совместимости — анализируйте совместимость с любым количеством людей "
            "и получайте глубокий анализ отношений\n\n"
            "• Еженедельные и ежемесячные прогнозы — узнавайте о важных периодах и возможностях заранее\n\n"
            "• Специальные транзиты планет — получайте уведомления о значимых астрологических событиях, "
            "которые могут повлиять на вашу жизнь\n\n"
            "• Приоритетная поддержка — ваши вопросы будут обрабатываться в первую очередь",
            reply_markup=get_subscription_menu(is_subscribed=False)
        )
    
    elif message.text == "📊 Информация о подписке":
        # Получаем информацию о подписке
        if user and user.get("subscription_type") != "free" and user.get("subscription_end_date"):
            end_date = datetime.fromisoformat(user.get("subscription_end_date"))
            days_left = (end_date - datetime.now()).days
            
            # Получаем историю транзакций
            transactions = operations.get_user_transactions(user_id)
            
            if transactions:
                last_transaction = transactions[0]
                payment_date = datetime.fromisoformat(last_transaction["created_at"]).strftime("%d.%m.%Y")
                amount = last_transaction["amount"]
                payment_method = last_transaction["payment_method"]
                
                transactions_text = (
                    f"Последний платеж: {payment_date}\n"
                    f"Сумма: ${amount}\n"
                    f"Способ оплаты: {payment_method}\n"
                )
            else:
                transactions_text = "История платежей недоступна."
            
            await message.answer(
                f"💎 Информация о вашей подписке:\n\n"
                f"Тип подписки: {user.get('subscription_type')}\n"
                f"Действует до: {end_date.strftime('%d.%m.%Y')}\n"
                f"Осталось дней: {days_left}\n\n"
                f"💳 История платежей:\n"
                f"{transactions_text}\n\n"
                f"Спасибо, что выбрали Premium!",
                reply_markup=get_subscription_menu(is_subscribed=True)
            )
        else:
            await message.answer(
                "У вас нет активной подписки.",
                reply_markup=get_subscription_menu(is_subscribed=False)
            )
    
    elif message.text == "🔄 Продлить подписку":
        await message.answer(
            "Выберите план для продления подписки:",
            reply_markup=get_subscription_plans()
        )

@handle_exception
async def subscription_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs):
    """Обработчик выбора плана подписки через inline кнопки"""
    action, plan = callback.data.split(":")
    
    if action == "subscribe":
        # Получаем информацию о выбранном плане
        price = SUBSCRIPTION_PRICES.get(plan, 0)
        months = 1
        if plan == "3_month":
            months = 3
        elif plan == "1_year":
            months = 12
        
        plan_text = {
            "1_month": "1 месяц",
            "3_month": "3 месяца",
            "1_year": "1 год"
        }.get(plan, plan)
        
        await callback.answer()
        
        # Сохраняем выбранный план в состоянии
        await state.update_data(
            subscription_plan=plan,
            subscription_price=price,
            subscription_months=months
        )
        
        # Предлагаем оплату звездами как единственный метод
        stars_amount = int(price * 100) # Например, 499 звезд за $4.99
        await callback.message.answer(
            f"⭐️ Для активации подписки '{plan_text}' необходимо отправить {stars_amount} звезд.\n\n"
            f"Нажмите кнопку ниже, чтобы перейти к оплате:",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text=f"Оплатить {stars_amount} ⭐️", callback_data=f"start_stars_payment:{plan}:{stars_amount}")],
                    [types.InlineKeyboardButton(text="Отменить", callback_data="cancel_payment")]
                ]
            )
        )
        
        await state.set_state(SubscriptionStates.selecting_payment_method)

@handle_exception
async def start_stars_payment_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs):
    """Обработчик начала платежа звездами"""
    _, plan, stars_amount = callback.data.split(":")
    stars_amount = int(stars_amount)
    user_id = str(callback.from_user.id)
    
    await callback.answer()
    
    data = await state.get_data()
    
    # Создаем транзакцию в БД
    transaction_id = operations.add_subscription_transaction(
        user_id,
        plan,
        SUBSCRIPTION_PRICES.get(plan, 0),
        "pending",
        "telegram_stars",
        data.get("subscription_months", 1)
    )
    
    # Сохраняем ID транзакции в состоянии
    await state.update_data(
        transaction_id=transaction_id,
        stars_amount=stars_amount
    )
    
    # Создаем ссылку на оплату
    purpose = f"Подписка на {plan} астрологических прогнозов"
    payment_result = await telegram_stars_payment.create_stars_invoice(
        callback.bot,
        int(user_id),
        stars_amount,
        purpose
    )
    
    if payment_result.get("success"):
        invoice_id = payment_result.get("invoice_id")
        payment_url = payment_result.get("payment_url")
        
        # Обновляем транзакцию с ID инвойса
        operations.update_transaction_status(
            transaction_id, 
            "pending", 
            {"invoice_id": invoice_id}
        )
        
        await callback.message.answer(
            "💫 Для оплаты подписки перейдите по ссылке ниже и отправьте звезды.\n\n"
            "После успешной оплаты нажмите кнопку «Я оплатил».",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="Перейти к оплате", url=payment_url)],
                    [types.InlineKeyboardButton(text="Я оплатил", callback_data="check_stars_payment")],
                    [types.InlineKeyboardButton(text="Отменить", callback_data="cancel_payment")]
                ]
            )
        )
        
        await state.set_state(SubscriptionStates.processing_payment)
    else:
        error = payment_result.get("error", "Неизвестная ошибка")
        logger.error(f"Ошибка создания платежа звездами: {error}")
        
        await callback.message.answer(
            f"❌ Не удалось создать платеж: {error}\n\nПожалуйста, попробуйте позже.",
            reply_markup=get_main_menu()
        )
        
        # Отменяем транзакцию
        operations.update_transaction_status(transaction_id, "failed", {"error": error})
        await state.clear()

@handle_exception
async def check_stars_payment_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs):
    """Обработчик проверки оплаты звездами"""
    await callback.answer("Проверяем статус платежа...")
    
    user_id = str(callback.from_user.id)
    data = await state.get_data()
    transaction_id = data.get("transaction_id")
    stars_amount = data.get("stars_amount")
    plan = data.get("subscription_plan")
    
    if not all([transaction_id, stars_amount, plan]):
        await callback.message.answer(
            "❌ Не удалось найти данные о вашем платеже. Попробуйте начать заново.",
            reply_markup=get_main_menu()
        )
        await state.clear()
        return
    
    # Здесь в реальной системе должна быть проверка через API Telegram
    # или через вебхук, но для демонстрации просто имитируем проверку
    
    # В реальном проекте Telegram отправляет уведомление через pre_checkout_query
    # и successful_payment, которые нужно обрабатывать
    
    # Для тестирования просто подтверждаем платеж
    payment_result = await telegram_stars_payment.process_stars_transfer(
        user_id,
        plan,
        stars_amount,
        transaction_id
    )
    
    if payment_result.get("success"):
        await callback.message.answer(
            "✅ Оплата успешно подтверждена! Ваша подписка активирована.\n\n"
            "Спасибо за поддержку нашего бота. Теперь вам доступны все премиум-функции!",
            reply_markup=get_main_menu()
        )
        await state.set_state(NatalChartStates.dialog_active)
    else:
        error = payment_result.get("error", "Не удалось подтвердить платеж")
        
        await callback.message.answer(
            f"⚠️ {error}\n\nЕсли вы уверены, что оплата прошла успешно, свяжитесь с администратором.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="Проверить еще раз", callback_data="check_stars_payment")],
                    [types.InlineKeyboardButton(text="Отменить платеж", callback_data="cancel_payment")]
                ]
            )
        )

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
    
    # Получаем имя канала для ссылки
    channel_name = PREMIUM_CHANNEL_ID.replace("@", "")
    channel_link = f"https://t.me/{channel_name}" if channel_name else "#"
    
    premium_info = (
        "💎 Премиум-возможности для вас!\n\n"
        "Вы можете получить доступ к премиум-функциям двумя способами:\n\n"
        "1️⃣ Подписаться на наш премиум-канал - получайте астрологические прогнозы и премиум-доступ к боту:\n"
        f"• Новости и прогнозы\n"
        f"• Эксклюзивный контент\n"
        f"• Полный доступ к функциям бота\n\n"
        "2️⃣ Оформить прямую подписку на бота, оплатив звездами Telegram:\n"
        "• Подробный ежедневный гороскоп\n"
        "• Неограниченное количество проверок совместимости\n"
        "• Безлимитное общение с астрологическим ассистентом\n"
        "• Еженедельные и ежемесячные прогнозы\n"
        "• Специальные аспекты планет и их влияние на вас\n\n"
        "Стоимость прямой подписки:\n"
        "1 месяц — $4.99 (499 звезд)\n"
        "3 месяца — $9.99 (999 звезд)\n"
        "1 год — $29.99 (2999 звезд)"
    )
    
    await callback.message.answer(
        premium_info,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="💫 Подписаться на премиум-канал", url=channel_link)],
                [types.InlineKeyboardButton(text="⭐️ Оформить подписку на бота", callback_data="subscribe_menu")]
            ]
        )
    )

# Обработчики предпроверки платежа и успешного платежа
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    """Обработчик предварительной проверки платежа"""
    try:
        # Получаем данные платежа
        payload = pre_checkout_query.invoice_payload
        
        # В payload должен быть ID транзакции или другой идентификатор
        # Проверяем, существует ли такая транзакция в базе
        # ... логика проверки транзакции ...
        
        # Если все в порядке, подтверждаем платеж
        await pre_checkout_query.answer(ok=True)
        logger.info(f"Pre-checkout query approved: {payload}")
    except Exception as e:
        # В случае ошибки отклоняем платеж
        await pre_checkout_query.answer(
            ok=False,
            error_message="Произошла ошибка при обработке платежа. Пожалуйста, попробуйте позже."
        )
        logger.error(f"Error in pre_checkout: {e}")

async def process_successful_payment(message: types.Message):
    """Обработчик успешного платежа"""
    try:
        # Получаем данные о платеже
        payment_info = message.successful_payment
        payload = payment_info.invoice_payload
        total_amount = payment_info.total_amount
        currency = payment_info.currency
        
        user_id = str(message.from_user.id)
        
        logger.info(f"Successful payment from user {user_id}: {payload}, {total_amount} {currency}")
        
        # Находим транзакцию в БД
        # ... логика поиска транзакции по payload ...
        
        # Активируем подписку пользователя
        # В реальном проекте здесь нужно определить план подписки из payload
        # и использовать соответствующие параметры
        
        plan = "1_month"  # Например, определяем из payload
        stars_amount = total_amount
        
        # Активируем подписку
        result = await telegram_stars_payment.process_stars_transfer(user_id, plan, stars_amount)
        
        if result.get("success"):
            # Отправляем сообщение пользователю
            await message.answer(
                "✅ Оплата успешно получена! Ваша подписка активирована.\n\n"
                "Спасибо за поддержку нашего бота. Теперь вам доступны все премиум-функции!",
                reply_markup=get_main_menu()
            )
        else:
            logger.error(f"Failed to process successful payment: {result.get('error')}")
            
            # Отправляем сообщение пользователю
            await message.answer(
                "⚠️ Оплата получена, но возникла ошибка при активации подписки.\n\n"
                "Пожалуйста, свяжитесь с администратором.",
                reply_markup=get_main_menu()
            )
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
    
    # Обработчик выбора действия в меню подписки
    dp.message.register(
        subscription_action_handler,
        SubscriptionStates.selecting_plan,
        F.text.in_([
            "💎 Купить подписку",
            "❓ Преимущества подписки",
            "📊 Информация о подписке",
            "🔄 Продлить подписку"
        ])
    )
    
    # Обработчик выбора плана подписки
    dp.callback_query.register(
        subscription_callback,
        lambda c: c.data.startswith("subscribe:")
    )
    
    # Обработчик начала платежа звездами
    dp.callback_query.register(
        start_stars_payment_callback,
        lambda c: c.data.startswith("start_stars_payment:")
    )
    
    # Обработчик проверки платежа звездами
    dp.callback_query.register(
        check_stars_payment_callback,
        lambda c: c.data == "check_stars_payment"
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