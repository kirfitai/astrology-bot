from aiogram import Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile

from utils.keyboards import get_main_menu
from database import operations
from states.user_states import NatalChartStates

async def start_command(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    # Сбрасываем текущее состояние пользователя
    await state.clear()
    
    # Получаем или создаем пользователя в базе
    user_id = str(message.from_user.id)
    username = message.from_user.username or ""
    first_name = message.from_user.first_name or ""
    last_name = message.from_user.last_name or ""
    
    operations.create_user(user_id, username, first_name, last_name)
    
    # Формируем приветственное сообщение
    greeting = (
        f"🌟 Приветствую, {first_name}! 🌟\n\n"
        "Я ваш персональный астрологический бот. Со мной вы сможете:\n"
        "• Рассчитать свою натальную карту 🔮\n"
        "• Получать ежедневные гороскопы 📅\n"
        "• Проверять совместимость с другими людьми 💑\n"
        "• Задавать вопросы о вашей астрологической карте 💫\n\n"
        "Чтобы начать, давайте рассчитаем вашу натальную карту. "
        "Пожалуйста, введите дату вашего рождения в формате ДД.ММ.ГГГГ (например, 15.05.1990)."
    )
    
    # Отправляем приветственное сообщение
    await message.answer(greeting, reply_markup=get_main_menu())
    
    # Устанавливаем состояние для ожидания даты рождения
    await state.set_state(NatalChartStates.waiting_for_date)

async def menu_command(message: types.Message, state: FSMContext):
    """Обработчик команды /menu"""
    # Показываем главное меню
    await message.answer("Выберите действие:", reply_markup=get_main_menu())

async def help_command(message: types.Message):
    """Обработчик команды /help"""
    help_text = (
        "🌟 Помощь по использованию астрологического бота 🌟\n\n"
        "🔮 <b>Основные команды:</b>\n"
        "/start - Начать взаимодействие с ботом\n"
        "/menu - Показать главное меню\n"
        "/natal - Рассчитать натальную карту\n"
        "/compatibility - Проверить совместимость\n"
        "/horoscope - Настроить ежедневный гороскоп\n"
        "/subscription - Управление подпиской\n"
        "/reset - Сбросить текущее состояние\n\n"
        
        "🌙 <b>Натальная карта:</b>\n"
        "Для расчета натальной карты нужны ваши дата, время и место рождения. "
        "Чем точнее данные, тем точнее будет расчет.\n\n"
        
        "💞 <b>Совместимость:</b>\n"
        "Для проверки совместимости нужно добавить контакты людей, "
        "с которыми вы хотите проверить совместимость. "
        "Для каждого контакта потребуются те же данные, что и для вашей натальной карты.\n\n"
        
        "📅 <b>Гороскоп:</b>\n"
        "Настройте время и место для получения ежедневного персонализированного гороскопа.\n\n"
        
        "💬 <b>Диалог:</b>\n"
        "После расчета натальной карты вы можете задавать боту вопросы, "
        "а он будет отвечать, учитывая особенности вашей карты.\n\n"
        
        "💰 <b>Подписка:</b>\n"
        "У вас есть 10 бесплатных сообщений. После этого вам потребуется подписка для продолжения общения."
    )
    
    await message.answer(help_text, parse_mode="HTML")

async def reset_command(message: types.Message, state: FSMContext):
    """Обработчик команды /reset"""
    await state.clear()
    await message.answer("Состояние сброшено. Вы можете начать взаимодействие заново.", reply_markup=get_main_menu())

async def back_to_menu_handler(message: types.Message, state: FSMContext):
    """Обработчик для возврата в главное меню"""
    if message.text == "↩️ Назад в меню":
        await state.clear()
        await message.answer("Вы вернулись в главное меню.", reply_markup=get_main_menu())
        return True
    return False

def register_handlers(dp: Dispatcher):
    """Регистрирует обработчики команд старта и меню"""
    # Команда /start
    dp.message.register(start_command, CommandStart())
    
    # Команда /menu
    dp.message.register(menu_command, Command("menu"))
    
    # Команда /help
    dp.message.register(help_command, Command("help"))
    
    # Команда /reset
    dp.message.register(reset_command, Command("reset"))