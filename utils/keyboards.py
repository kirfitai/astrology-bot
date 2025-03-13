from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

# --- Основное меню ---
def get_main_menu():
    """Создает основное меню бота"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔮 Гороскоп"), KeyboardButton(text="💞 Совместимость")],
            [KeyboardButton(text="🌟 Моя натальная карта"), KeyboardButton(text="💰 Подписка")]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return kb

# --- Клавиатуры для ввода данных рождения ---
def get_yes_no_keyboard():
    """Клавиатура Да/Нет"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")]
        ],
        resize_keyboard=True
    )
    return kb

def get_back_button():
    """Добавляет кнопку Назад в основное меню"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="↩️ Назад в меню")]
        ],
        resize_keyboard=True
    )
    return kb

def get_time_periods_keyboard():
    """Клавиатура для быстрого выбора времени суток"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Утром (09:00)"),
                KeyboardButton(text="Днем (15:00)")
            ],
            [
                KeyboardButton(text="Вечером (21:00)"),
                KeyboardButton(text="Ночью (03:00)")
            ],
            [KeyboardButton(text="↩️ Назад")]
        ],
        resize_keyboard=True
    )
    return kb

# --- Клавиатуры для совместимости ---
def get_compatibility_menu():
    """Создает меню совместимости"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Добавить новый контакт")],
            [KeyboardButton(text="📋 Мои контакты")],
            [KeyboardButton(text="↩️ Назад в меню")]
        ],
        resize_keyboard=True
    )
    return kb

def get_contacts_keyboard(contacts):
    """Создает клавиатуру со списком контактов"""
    builder = ReplyKeyboardBuilder()
    
    # Добавляем контакты по два в ряд
    for i in range(0, len(contacts), 2):
        row = []
        row.append(KeyboardButton(text=f"👤 {contacts[i]['person_name']}"))
        
        if i + 1 < len(contacts):
            row.append(KeyboardButton(text=f"👤 {contacts[i+1]['person_name']}"))
        
        builder.row(*row)
    
    # Добавляем кнопки управления
    builder.row(
        KeyboardButton(text="➕ Добавить контакт"),
        KeyboardButton(text="↩️ Назад")
    )
    
    return builder.as_markup(resize_keyboard=True)

def get_inline_contact_actions(contact_id):
    """Создает инлайн клавиатуру с действиями для контакта"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Совместимость", callback_data=f"compatibility:{contact_id}"),
                InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_contact:{contact_id}")
            ],
            [
                InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_contact:{contact_id}")
            ]
        ]
    )
    return kb

# --- Клавиатуры для гороскопа ---
def get_horoscope_menu():
    """Создает меню настроек гороскопа"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏰ Настроить время")],
            [KeyboardButton(text="🌍 Изменить город")],
            [KeyboardButton(text="📝 Посмотреть текущие настройки")],
            [KeyboardButton(text="↩️ Назад в меню")]
        ],
        resize_keyboard=True
    )
    return kb

def get_horoscope_time_keyboard():
    """Клавиатура для выбора времени гороскопа"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="07:00"),
                KeyboardButton(text="08:00"),
                KeyboardButton(text="09:00")
            ],
            [
                KeyboardButton(text="12:00"),
                KeyboardButton(text="18:00"),
                KeyboardButton(text="21:00")
            ],
            [KeyboardButton(text="↩️ Назад")]
        ],
        resize_keyboard=True
    )
    return kb

# --- Клавиатуры для подписок ---
def get_subscription_menu(is_subscribed=False):
    """Создает меню управления подпиской"""
    if is_subscribed:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="📊 Информация о подписке")],
                [KeyboardButton(text="🔄 Продлить подписку")],
                [KeyboardButton(text="↩️ Назад в меню")]
            ],
            resize_keyboard=True
        )
    else:
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="💎 Купить подписку")],
                [KeyboardButton(text="❓ Преимущества подписки")],
                [KeyboardButton(text="↩️ Назад в меню")]
            ],
            resize_keyboard=True
        )
    return kb

def get_subscription_plans():
    """Создает инлайн клавиатуру с планами подписки"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✨ 1 неделя - 90 ⭐️", callback_data="subscribe:1_week")
            ],
            [
                InlineKeyboardButton(text="✨ 1 месяц - 499 ⭐️", callback_data="subscribe:1_month")
            ],
            [
                InlineKeyboardButton(text="✨ 3 месяца - 999 ⭐️", callback_data="subscribe:3_month")
            ],
            [
                InlineKeyboardButton(text="✨ 1 год - 2999 ⭐️", callback_data="subscribe:1_year")
            ]
        ]
    )
    return kb

def get_payment_methods():
    """Создает инлайн клавиатуру с методами оплаты"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐️ Оплатить звездами Telegram", callback_data="payment_method:telegram_stars")
            ],
            [
                InlineKeyboardButton(text="↩️ Отменить", callback_data="cancel_payment")
            ]
        ]
    )
    return kb

# --- Админские клавиатуры ---
def get_admin_menu():
    """Создает главное меню администратора"""
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="💰 Финансы"), KeyboardButton(text="⚙️ Настройки")],
            [KeyboardButton(text="🚪 Выход")]
        ],
        resize_keyboard=True
    )
    return kb

def get_admin_user_actions(user_id):
    """Создает инлайн клавиатуру с действиями для пользователя"""
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💬 Сообщения", callback_data=f"admin_messages:{user_id}"),
                InlineKeyboardButton(text="📝 Подписка", callback_data=f"admin_subscription:{user_id}")
            ],
            [
                InlineKeyboardButton(text="🔮 Натальная карта", callback_data=f"admin_natal:{user_id}"),
                InlineKeyboardButton(text="📨 Отправить сообщение", callback_data=f"admin_send_message:{user_id}")
            ]
        ]
    )
    return kb