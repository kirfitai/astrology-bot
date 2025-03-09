from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from datetime import datetime, timedelta
import logging

from states.user_states import SubscriptionStates, NatalChartStates
from utils.keyboards import (
    get_main_menu,
    get_subscription_menu,
    get_subscription_plans,
    get_back_button
)
from database import operations
from config import SUBSCRIPTION_PRICES
from handlers.start import back_to_menu_handler

logger = logging.getLogger(__name__)

async def subscription_command(message: types.Message, state: FSMContext):
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
            f"У вас бесплатный план. Осталось сообщений: {messages_left}/10\n\n"
            "С Premium подпиской вы получите:\n"
            "• Безлимитное общение с ботом\n"
            "• Расширенный ежедневный гороскоп\n"
            "• Безлимитные проверки совместимости\n"
            "• Еженедельные и ежемесячные прогнозы\n"
            "• Расширенный анализ всех сфер жизни",
            reply_markup=get_subscription_menu(is_subscribed=False)
        )
    
    await state.set_state(SubscriptionStates.selecting_plan)

async def subscription_action_handler(message: types.Message, state: FSMContext):
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

async def subscription_callback(callback: types.CallbackQuery, state: FSMContext):
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
        
        # Показываем информацию о платеже
        payment_text = (
            f"💳 Оформление подписки\n\n"
            f"План: {plan_text}\n"
            f"Стоимость: ${price}\n\n"
            f"Для оплаты нажмите на кнопку ниже. Вы будете перенаправлены на страницу оплаты."
        )
        
        await callback.message.answer(
            payment_text,
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text="💳 Оплатить", callback_data=f"payment:{plan}")]
                ]
            )
        )
        
        await state.set_state(SubscriptionStates.processing_payment)

async def payment_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки оплаты"""
    action, plan = callback.data.split(":")
    
    if action == "payment":
        # Здесь должна быть интеграция с платежной системой
        # В данном случае симулируем успешную оплату
        
        await callback.answer("Инициирую платеж...")
        
        data = await state.get_data()
        price = data.get("subscription_price", 0)
        months = data.get("subscription_months", 1)
        
        # В реальном проекте здесь должен быть код для создания платежа в Tribute
        # и перенаправления пользователя на страницу оплаты
        
        # Для демонстрации просто создаем запись о транзакции и обновляем подписку
        user_id = str(callback.from_user.id)
        
        # Симулируем успешную оплату
        operations.add_subscription_transaction(
            user_id,
            plan,
            price,
            "completed",
            "card",
            months
        )
        
        # Обновляем подписку пользователя
        user = operations.update_user_subscription(user_id, plan, months)
        
        end_date = datetime.now() + timedelta(days=30*months)
        
        await callback.message.answer(
            f"✅ Подписка успешно оформлена!\n\n"
            f"Тип подписки: {plan}\n"
            f"Действует до: {end_date.strftime('%d.%m.%Y')}\n\n"
            f"Теперь вам доступны все Premium возможности бота. Наслаждайтесь!",
            reply_markup=get_main_menu()
        )
        
        await state.set_state(NatalChartStates.dialog_active)

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
    
    # Обработчик кнопки оплаты
    dp.callback_query.register(
        payment_callback,
        lambda c: c.data.startswith("payment:")
    )
    
    # Обработчик запроса информации о премиум-подписке
    dp.callback_query.register(
        lambda c, state: subscription_command(c.message, state),
        lambda c: c.data == "subscribe_menu"
    )