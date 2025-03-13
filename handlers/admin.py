from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
import logging

from states.user_states import AdminStates
from utils.keyboards import get_main_menu, get_admin_menu, get_admin_user_actions
from database import operations
from config import ADMIN_USERNAME, ADMIN_PASSWORD

logger = logging.getLogger(__name__)

async def admin_command(message: types.Message, state: FSMContext):
    """Обработчик команды /admin для входа в административную панель"""
    await message.answer(
        "🔒 Вход в административную панель\n\n"
        "Пожалуйста, введите имя пользователя:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="Отмена")]],
            resize_keyboard=True
        )
    )
    await state.set_state(AdminStates.waiting_for_login)

async def process_admin_login(message: types.Message, state: FSMContext):
    """Обрабатывает ввод логина для административной панели"""
    if message.text == "Отмена":
        await message.answer("Вход отменен.", reply_markup=get_main_menu())
        await state.clear()
        return
    
    login = message.text.strip()
    
    if login == ADMIN_USERNAME:
        await state.update_data(admin_login=login)
        await message.answer(
            "Введите пароль:",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text="Отмена")]],
                resize_keyboard=True
            )
        )
        await state.set_state(AdminStates.waiting_for_password)
    else:
        await message.answer(
            "❌ Неверное имя пользователя. Попробуйте еще раз или нажмите 'Отмена':",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text="Отмена")]],
                resize_keyboard=True
            )
        )

async def process_admin_password(message: types.Message, state: FSMContext):
    """Обрабатывает ввод пароля для административной панели"""
    if message.text == "Отмена":
        await message.answer("Вход отменен.", reply_markup=get_main_menu())
        await state.clear()
        return
    
    password = message.text.strip()
    
    if password == ADMIN_PASSWORD:
        await message.answer(
            "✅ Вход выполнен успешно! Добро пожаловать в административную панель.",
            reply_markup=get_admin_menu()
        )
        await state.set_state(AdminStates.admin_active)
        
        # Получаем общую статистику
        stats = operations.get_total_stats()
        
        stats_message = (
            "📊 Статистика бота:\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"👤 Активных за 7 дней: {stats['active_users']}\n"
            f"💎 С подпиской: {stats['paid_users']}\n"
            f"💬 Сообщений: {stats['total_messages']}\n"
            f"💞 Проверок совместимости: {stats['total_compatibility_analyses']}\n"
            f"🔮 Гороскопов: {stats['total_horoscopes']}\n"
            f"💰 Расходы на API: ${stats['total_api_cost']:.2f}"
        )
        
        await message.answer(stats_message, reply_markup=get_admin_menu())
    else:
        await message.answer(
            "❌ Неверный пароль. Попробуйте еще раз или нажмите 'Отмена':",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[[types.KeyboardButton(text="Отмена")]],
                resize_keyboard=True
            )
        )

async def admin_menu_handler(message: types.Message, state: FSMContext):
    """Обработчик выбора действия в административном меню"""
    if message.text == "🚪 Выход":
        await message.answer("Вы вышли из административной панели.", reply_markup=get_main_menu())
        await state.clear()
        return
    
    if message.text == "👥 Пользователи":
        # Получаем список пользователей
        users = operations.get_all_users()
        
        if not users:
            await message.answer("Пользователи не найдены.", reply_markup=get_admin_menu())
            return
        
        # Формируем список пользователей
        users_text = "👥 Список пользователей:\n\n"
        
        for i, user in enumerate(users[:20], 1):  # Показываем только первые 20 пользователей
            username = user.get("username", "")
            first_name = user.get("first_name", "")
            last_name = user.get("last_name", "")
            subscription_type = user.get("subscription_type", "free")
            messages_count = user.get("input_tokens", 0) + user.get("output_tokens", 0)
            
            user_name = username or f"{first_name} {last_name}"
            subscription_emoji = "💎" if subscription_type != "free" else "🆓"
            
            users_text += f"{i}. {subscription_emoji} {user_name} (ID: {user['user_id']})\n"
        
        users_text += "\nВыберите пользователя, указав его номер или ID:"
        
        await message.answer(users_text, reply_markup=get_admin_menu())
        await state.set_state(AdminStates.selecting_user)
    
    elif message.text == "📊 Статистика":
        # Получаем общую статистику
        stats = operations.get_total_stats()
        
        stats_message = (
            "📊 Статистика бота:\n\n"
            f"👥 Пользователей: {stats['total_users']}\n"
            f"👤 Активных за 7 дней: {stats['active_users']}\n"
            f"💎 С подпиской: {stats['paid_users']}\n"
            f"💬 Сообщений: {stats['total_messages']}\n"
            f"💞 Проверок совместимости: {stats['total_compatibility_analyses']}\n"
            f"🔮 Гороскопов: {stats['total_horoscopes']}\n"
            f"💰 Расходы на API: ${stats['total_api_cost']:.2f}"
        )
        
        await message.answer(stats_message, reply_markup=get_admin_menu())
    
    elif message.text == "💰 Финансы":
        # Получаем финансовую статистику
        stats = operations.get_total_stats()
        
        # Получаем список активных подписок
        users = operations.get_all_users()
        subscription_counts = {"1_month": 0, "3_month": 0, "1_year": 0}
        
        for user in users:
            if user.get("subscription_type") != "free":
                subscription_counts[user.get("subscription_type", "1_month")] += 1
        
        # Рассчитываем приблизительный доход
        revenue = (
            subscription_counts["1_month"] * 4.99 +
            subscription_counts["3_month"] * 9.99 +
            subscription_counts["1_year"] * 29.99
        )
        
        finance_message = (
            "💰 Финансовая статистика:\n\n"
            f"💎 Активных подписок: {stats['paid_users']}\n"
            f"  - 1 месяц ($4.99): {subscription_counts['1_month']}\n"
            f"  - 3 месяца ($9.99): {subscription_counts['3_month']}\n"
            f"  - 1 год ($29.99): {subscription_counts['1_year']}\n\n"
            f"💵 Приблизительный доход: ${revenue:.2f}\n"
            f"💸 Расходы на API: ${stats['total_api_cost']:.2f}\n\n"
            f"📈 Прибыль: ${revenue - stats['total_api_cost']:.2f}"
        )
        
        await message.answer(finance_message, reply_markup=get_admin_menu())
    
    elif message.text == "⚙️ Настройки":
        settings_message = (
            "⚙️ Настройки бота:\n\n"
            "• Бесплатных сообщений: 3\n"
            "• Токены API OpenAI: настроены\n"
            "• Токен Telegram: настроен\n"
            "• База данных: SQLite\n\n"
            "Для изменения настроек отредактируйте файл конфигурации."
        )
        
        await message.answer(settings_message, reply_markup=get_admin_menu())

async def select_user_handler(message: types.Message, state: FSMContext):
    """Обработчик выбора пользователя в административной панели"""
    if message.text == "🚪 Выход":
        await message.answer("Вы вышли из административной панели.", reply_markup=get_main_menu())
        await state.clear()
        return
    
    if message.text in ["👥 Пользователи", "📊 Статистика", "💰 Финансы", "⚙️ Настройки"]:
        await admin_menu_handler(message, state)
        return
    
    # Пытаемся определить ID пользователя
    user_id = None
    
    # Если введен номер пользователя из списка
    if message.text.isdigit():
        index = int(message.text) - 1
        users = operations.get_all_users()
        
        if 0 <= index < len(users):
            user_id = users[index]["user_id"]
    else:
        # Если введен ID пользователя напрямую
        user_id = message.text.strip()
    
    if user_id:
        user = operations.get_user(user_id)
        
        if user:
            # Сохраняем ID пользователя в состоянии
            await state.update_data(selected_user_id=user_id)
            
            # Форматируем информацию о пользователе
            user_info = format_user_info(user)
            
            await message.answer(
                user_info,
                reply_markup=get_admin_user_actions(user_id)
            )
            
            await state.set_state(AdminStates.viewing_user_details)
        else:
            await message.answer(
                "Пользователь не найден. Попробуйте еще раз.",
                reply_markup=get_admin_menu()
            )
    else:
        await message.answer(
            "Неверный формат ID пользователя. Попробуйте еще раз.",
            reply_markup=get_admin_menu()
        )

async def user_action_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик действий с пользователем через inline кнопки"""
    action, user_id = callback.data.split(":")
    
    if action == "admin_messages":
        # Показываем историю сообщений пользователя
        messages = operations.get_user_messages(user_id)
        
        if not messages:
            await callback.answer("У пользователя нет сообщений")
            return
        
        # Форматируем историю сообщений
        messages_text = f"💬 История сообщений пользователя {user_id}:\n\n"
        
        for i, msg in enumerate(messages[-10:], 1):  # Показываем последние 10 сообщений
            direction = "👤" if msg["direction"] == "in" else "🤖"
            created_at = msg.get("created_at", "")
            content = msg.get("content", "")
            
            # Обрезаем длинные сообщения
            if len(content) > 100:
                content = content[:100] + "..."
            
            messages_text += f"{i}. {direction} {created_at}: {content}\n\n"
        
        await callback.message.answer(messages_text, reply_markup=get_admin_menu())
        await callback.answer()
    
    elif action == "admin_subscription":
        # Показываем информацию о подписке пользователя
        user = operations.get_user(user_id)
        
        if not user:
            await callback.answer("Пользователь не найден")
            return
        
        # Получаем историю транзакций
        transactions = operations.get_user_transactions(user_id)
        
        # Форматируем информацию о подписке
        subscription_text = (
            f"💎 Информация о подписке пользователя {user_id}:\n\n"
            f"Тип подписки: {user.get('subscription_type', 'free')}\n"
            f"Дата окончания: {user.get('subscription_end_date', 'Нет')}\n\n"
        )
        
        if transactions:
            subscription_text += "💳 История транзакций:\n\n"
            
            for i, tx in enumerate(transactions, 1):
                subscription_text += (
                    f"{i}. Дата: {tx.get('created_at', '')}\n"
                    f"   План: {tx.get('subscription_type', '')}\n"
                    f"   Сумма: ${tx.get('amount', 0)}\n"
                    f"   Статус: {tx.get('status', '')}\n\n"
                )
        else:
            subscription_text += "У пользователя нет истории транзакций."
        
        await callback.message.answer(subscription_text, reply_markup=get_admin_menu())
        await callback.answer()
    
    elif action == "admin_natal":
        # Показываем натальную карту пользователя
        user = operations.get_user(user_id)
        
        if not user:
            await callback.answer("Пользователь не найден")
            return
        
        natal_chart = user.get("natal_chart", "Натальная карта не рассчитана")
        
        natal_text = (
            f"🔮 Натальная карта пользователя {user_id}:\n\n"
            f"{natal_chart}\n\n"
            f"Дата рождения: {user.get('birth_date', 'Не указана')}\n"
            f"Время рождения: {user.get('birth_time', 'Не указано')}\n"
            f"Город рождения: {user.get('city', 'Не указан')}"
        )
        
        await callback.message.answer(natal_text, reply_markup=get_admin_menu())
        await callback.answer()
    
    elif action == "admin_send_message":
        # Подготавливаемся к отправке сообщения пользователю
        await state.update_data(message_to_user_id=user_id)
        
        await callback.message.answer(
            f"Введите сообщение для отправки пользователю {user_id}:",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="Отмена отправки")]
                ],
                resize_keyboard=True
            )
        )
        
        await state.set_state(AdminStates.admin_active)  # Используем тот же state, но обработаем по-другому
        await callback.answer()

async def send_message_to_user(message: types.Message, state: FSMContext):
    """Отправляет сообщение пользователю от имени администратора"""
    if message.text == "Отмена отправки":
        await message.answer("Отправка сообщения отменена.", reply_markup=get_admin_menu())
        return
    
    data = await state.get_data()
    user_id = data.get("message_to_user_id")
    
    if not user_id:
        await message.answer("Ошибка: ID пользователя не найден.", reply_markup=get_admin_menu())
        return
    
    try:
        # Отправляем сообщение пользователю
        await message.bot.send_message(
            user_id,
            f"📣 Сообщение от администратора:\n\n{message.text}"
        )
        
        await message.answer(
            f"✅ Сообщение успешно отправлено пользователю {user_id}.",
            reply_markup=get_admin_menu()
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        await message.answer(
            f"❌ Ошибка при отправке сообщения: {e}",
            reply_markup=get_admin_menu()
        )

def format_user_info(user):
    """Форматирует информацию о пользователе для административной панели"""
    user_id = user.get("user_id", "")
    username = user.get("username", "")
    first_name = user.get("first_name", "")
    last_name = user.get("last_name", "")
    subscription_type = user.get("subscription_type", "free")
    subscription_end = user.get("subscription_end_date", "")
    birth_date = user.get("birth_date", "Не указана")
    birth_time = user.get("birth_time", "Не указано")
    city = user.get("city", "Не указан")
    free_messages_left = user.get("free_messages_left", 0)
    registration_date = user.get("registration_date", "")
    last_activity = user.get("last_activity", "")
    input_tokens = user.get("input_tokens", 0)
    output_tokens = user.get("output_tokens", 0)
    total_cost = user.get("total_cost", 0)
    
    # Расчет общего количества сообщений
    total_tokens = input_tokens + output_tokens
    
    user_info = (
        f"👤 Информация о пользователе:\n\n"
        f"ID: {user_id}\n"
        f"Имя пользователя: {username}\n"
        f"Имя: {first_name}\n"
        f"Фамилия: {last_name}\n\n"
        
        f"📅 Дата регистрации: {registration_date}\n"
        f"⏱ Последняя активность: {last_activity}\n\n"
        
        f"💎 Подписка: {subscription_type}\n"
        f"📆 Дата окончания: {subscription_end}\n"
        f"🔢 Бесплатных сообщений: {free_messages_left}\n\n"
        
        f"🌟 Дата рождения: {birth_date}\n"
        f"🕒 Время рождения: {birth_time}\n"
        f"🌍 Город рождения: {city}\n\n"
        
        f"💬 Всего токенов: {total_tokens}\n"
        f"📥 Входящие токены: {input_tokens}\n"
        f"📤 Исходящие токены: {output_tokens}\n"
        f"💰 Стоимость API: ${total_cost:.4f}\n\n"
        
        f"Выберите действие:"
    )
    
    return user_info

def register_handlers(dp: Dispatcher):
    """Регистрирует обработчики для административной панели"""
    # Команда /admin
    dp.message.register(admin_command, Command("admin"))
    
    # Обработчик ввода логина
    dp.message.register(process_admin_login, AdminStates.waiting_for_login)
    
    # Обработчик ввода пароля
    dp.message.register(process_admin_password, AdminStates.waiting_for_password)
    
    # Обработчик выбора действия в меню администратора
    dp.message.register(
        admin_menu_handler,
        AdminStates.admin_active,
        F.text.in_(["👥 Пользователи", "📊 Статистика", "💰 Финансы", "⚙️ Настройки", "🚪 Выход"])
    )
    
    # Обработчик выбора пользователя
    dp.message.register(select_user_handler, AdminStates.selecting_user)
    
    # Обработчик действий с пользователем через inline кнопки
    dp.callback_query.register(
        user_action_callback,
        lambda c: c.data.startswith(("admin_messages:", "admin_subscription:", "admin_natal:", "admin_send_message:"))
    )
    
    # Обработчик отправки сообщения пользователю
    dp.message.register(
        send_message_to_user,
        AdminStates.admin_active,
        lambda message: message.text != "Отмена отправки" and not message.text.startswith("/")
    )