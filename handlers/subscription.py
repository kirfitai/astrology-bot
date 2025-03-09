from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import logging

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
from config import SUBSCRIPTION_PRICES, ADMIN_TELEGRAM_ID
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
        
        # Предлагаем выбрать способ оплаты
        await callback.message.answer(
            f"📱 Выберите способ оплаты для подписки '{plan_text}' (${price}):",
            reply_markup=get_payment_methods()
        )
        
        await state.set_state(SubscriptionStates.selecting_payment_method)

@handle_exception
async def payment_method_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs):
    """Обработчик выбора способа оплаты"""
    action, method = callback.data.split(":")
    
    if action == "payment_method":
        await callback.answer()
        
        data = await state.get_data()
        plan = data.get("subscription_plan")
        price = data.get("subscription_price", 0)
        
        if not plan or not price:
            await callback.message.answer(
                "❌ Ошибка при обработке запроса. Пожалуйста, попробуйте снова.",
                reply_markup=get_main_menu()
            )
            await state.clear()
            return
        
        user_id = str(callback.from_user.id)
        
        # Отменяем любые предыдущие незавершенные платежи
        operations.cancel_pending_transactions(user_id)
        
        if method == "tribute":
            # Создаем платеж через Tribute
            payment_result = await create_payment(user_id, plan, "tribute")
            
            if payment_result.get("success"):
                payment_url = payment_result.get("payment_url")
                
                await callback.message.answer(
                    "💳 Перейдите по ссылке ниже для оплаты подписки:\n\n"
                    f"После успешной оплаты ваша подписка будет активирована автоматически.",
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [types.InlineKeyboardButton(text="Оплатить", url=payment_url)],
                            [types.InlineKeyboardButton(text="Я оплатил(а)", callback_data="check_payment")]
                        ]
                    )
                )
                
                await state.set_state(SubscriptionStates.processing_payment)
            else:
                error = payment_result.get("error", "Unknown error")
                logger.error(f"Payment creation error: {error}")
                
                await callback.message.answer(
                    "❌ Ошибка при создании платежа. Пожалуйста, попробуйте позже или выберите другой способ оплаты.",
                    reply_markup=get_main_menu()
                )
                await state.clear()
        
        elif method == "telegram_stars":
            # Создаем платеж через звезды Telegram
            payment_result = await create_payment(user_id, plan, "telegram_stars", bot=callback.bot)
            
            if payment_result.get("success"):
                stars_amount = payment_result.get("stars_amount")
                
                await callback.message.answer(
                    f"⭐️ Для активации подписки отправьте {stars_amount} звезд.\n\n"
                    "Нажмите на кнопку ниже, чтобы отправить звезды, затем подтвердите отправку.",
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [types.InlineKeyboardButton(text=f"Отправить {stars_amount} ⭐️", callback_data=f"stars_payment:{plan}:{stars_amount}")],
                            [types.InlineKeyboardButton(text="Я отправил(а) звезды", callback_data="check_stars")]
                        ]
                    )
                )
                
                await state.set_state(SubscriptionStates.processing_payment)
            else:
                error = payment_result.get("error", "Unknown error")
                logger.error(f"Stars payment creation error: {error}")
                
                await callback.message.answer(
                    "❌ Ошибка при создании запроса на звезды. Пожалуйста, попробуйте позже или выберите другой способ оплаты.",
                    reply_markup=get_main_menu()
                )
                await state.clear()

@handle_exception
async def check_payment_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs):
    """Обработчик проверки статуса платежа"""
    action = callback.data
    
    if action == "check_payment":
        await callback.answer("Проверяем статус платежа...")
        
        user_id = str(callback.from_user.id)
        transaction = operations.get_pending_transaction(user_id)
        
        if transaction and transaction.get("status") == "completed":
            # Платеж уже был успешно обработан
            await callback.message.answer(
                "✅ Ваш платеж был успешно обработан! Подписка активирована.",
                reply_markup=get_main_menu()
            )
            await state.set_state(NatalChartStates.dialog_active)
        else:
            # Платеж еще не обработан
            await callback.message.answer(
                "⏳ Ваш платеж еще обрабатывается. Пожалуйста, подождите или проверьте позже.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="Проверить еще раз", callback_data="check_payment")],
                        [types.InlineKeyboardButton(text="Отменить платеж", callback_data="cancel_payment")]
                    ]
                )
            )
    
    elif action == "check_stars":
        await callback.answer("Проверяем отправку звезд...")
        
        user_id = str(callback.from_user.id)
        data = await state.get_data()
        plan = data.get("subscription_plan")
        
        # В реальном приложении здесь должна быть проверка фактического получения звезд
        # через API Telegram, но для примера просто активируем подписку
        result = await telegram_stars_payment.process_stars_transfer(
            user_id, 
            plan, 
            data.get("stars_amount", 0)
        )
        
        if result.get("success"):
            await callback.message.answer(
                "✅ Спасибо за отправку звезд! Ваша подписка активирована.",
                reply_markup=get_main_menu()
            )
            await state.set_state(NatalChartStates.dialog_active)
        else:
            error = result.get("error", "Unknown error")
            
            if "Insufficient stars" in error:
                await callback.message.answer(
                    "⚠️ Вы отправили недостаточное количество звезд. Пожалуйста, проверьте сумму и попробуйте снова.",
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [types.InlineKeyboardButton(text="Я отправил(а) звезды", callback_data="check_stars")],
                            [types.InlineKeyboardButton(text="Отменить платеж", callback_data="cancel_payment")]
                        ]
                    )
                )
            else:
                await callback.message.answer(
                    "❌ Произошла ошибка при проверке отправки звезд. Пожалуйста, попробуйте позже или обратитесь к администратору.",
                    reply_markup=get_main_menu()
                )
                await state.clear()
    
    elif action == "cancel_payment":
        user_id = str(callback.from_user.id)
        
        # Отменяем незавершенные транзакции пользователя
        cancelled = operations.cancel_pending_transactions(user_id)
        
        if cancelled > 0:
            await callback.message.answer(
                "❌ Платеж отменен. Вы можете попробовать снова в любое время.",
                reply_markup=get_main_menu()
            )
        else:
            await callback.message.answer(
                "⚠️ Нет активных платежей для отмены.",
                reply_markup=get_main_menu()
            )
        
        await state.clear()

@handle_exception
async def stars_payment_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs):
    """Обработчик отправки звезд Telegram"""
    parts = callback.data.split(":")
    
    if len(parts) >= 3 and parts[0] == "stars_payment":
        plan = parts[1]
        stars_amount = int(parts[2])
        
        # Здесь должен быть вызов API Telegram для отправки звезд
        # Но так как у нас нет прямого доступа к этому API, отправляем уведомление пользователю
        await callback.answer("Пожалуйста, подтвердите отправку звезд в Telegram")
        
        # Сохраняем количество звезд в состоянии для последующей проверки
        await state.update_data(stars_amount=stars_amount)
        
        # В реальном приложении нужно использовать Telegram Payments API
        await callback.message.answer(
            f"⭐️ Пожалуйста, отправьте {stars_amount} звезд и затем нажмите кнопку 'Я отправил(а) звезды' для проверки.",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="Я отправил(а) звезды", callback_data="check_stars")],
                    [types.InlineKeyboardButton(text="Отменить платеж", callback_data="cancel_payment")]
                ]
            )
        )

@handle_exception
async def premium_info_callback(callback: types.CallbackQuery, state: FSMContext, **kwargs):
    """Обработчик нажатия на кнопку информации о премиум-подписке"""
    await callback.answer()
    
    # Получаем имя канала для ссылки
    channel_name = PREMIUM_CHANNEL_ID.replace("@", "")
    channel_link = f"https://t.me/{channel_name}"
    
    premium_info = (
        "💎 Премиум-возможности для вас!\n\n"
        "Вы можете получить доступ к премиум-функциям двумя способами:\n\n"
        "1️⃣ Подписаться на наш премиум-канал - получайте астрологические прогнозы и премиум-доступ к боту:\n"
        f"• Новости и прогнозы\n"
        f"• Эксклюзивный контент\n"
        f"• Полный доступ к функциям бота\n\n"
        "2️⃣ Оформить прямую подписку на бота:\n"
        "• Подробный ежедневный гороскоп\n"
        "• Неограниченное количество проверок совместимости\n"
        "• Безлимитное общение с астрологическим ассистентом\n"
        "• Еженедельные и ежемесячные прогнозы\n"
        "• Специальные аспекты планет и их влияние на вас\n\n"
        "Стоимость прямой подписки:\n"
        "1 месяц — $4.99\n"
        "3 месяца — $9.99\n"
        "1 год — $29.99"
    )
    
    await callback.message.answer(
        premium_info,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="💫 Подписаться на премиум-канал", url=channel_link)],
                [types.InlineKeyboardButton(text="💳 Оформить подписку на бота", callback_data="subscribe_menu")]
            ]
        )
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
    
    # Обработчик выбора способа оплаты
    dp.callback_query.register(
        payment_method_callback,
        lambda c: c.data.startswith("payment_method:")
    )
    
    # Обработчик проверки статуса платежа
    dp.callback_query.register(
        check_payment_callback,
        lambda c: c.data in ["check_payment", "check_stars", "cancel_payment"]
    )
    
    # Обработчик отправки звезд Telegram
    dp.callback_query.register(
        stars_payment_callback,
        lambda c: c.data.startswith("stars_payment:")
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