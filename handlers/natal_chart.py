from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from datetime import datetime
import logging
import asyncio
import random

from states.user_states import NatalChartStates
from utils.keyboards import (
    get_main_menu, 
    get_yes_no_keyboard, 
    get_time_periods_keyboard,
    get_back_button
)
from utils.date_parser import parse_date_input, parse_time_input
from services.geo import get_location_info, get_utc_datetime, parse_coordinates
from services.ephemeris import (
    calculate_planet_positions_utc, 
    calculate_houses_utc, 
    format_natal_chart
)
from services.openai_service import generate_natal_chart_interpretation
from database import operations
from handlers.start import back_to_menu_handler

logger = logging.getLogger(__name__)

# Функция для имитации печати
async def typing_action(message: types.Message, min_duration=1, max_duration=2):
    """Имитирует набор текста ботом"""
    duration = random.uniform(min_duration, max_duration)
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(duration)

# Функция для добавления тематических эмодзи
def add_astro_emoji(text, category="natal"):
    """Добавляет тематические эмодзи в начало текста"""
    emojis = {
        "natal": ["✨", "🌟", "🔮", "🌙", "💫", "⭐️", "🌠", "🌌", "🪐", "🧿"],
        "welcome": ["👋", "🎉", "✨", "🙏"],
        "error": ["❌", "⚠️", "🚫", "⛔️"],
        "success": ["✅", "🎉", "🎊", "🙌"],
        "question": ["❓", "🤔", "🧐", "🔍"]
    }
    
    category_emojis = emojis.get(category, emojis["natal"])
    chosen_emoji = random.choice(category_emojis)
    
    if not any(text.startswith(e) for e in sum(emojis.values(), [])):
        text = f"{chosen_emoji} {text}"
    
    return text

async def natal_chart_command(message: types.Message, state: FSMContext):
    """Обработчик команды /natal и нажатия на кнопку натальной карты"""
    # Имитируем печать
    await typing_action(message)
    
    # Проверяем, есть ли у пользователя уже рассчитанная карта
    user_id = str(message.from_user.id)
    user = operations.get_user(user_id)
    
    if user and user.get("natal_chart"):
        # У пользователя уже есть натальная карта
        await message.answer(
            add_astro_emoji("У вас уже есть рассчитанная натальная карта.\n\n"
            "Что вы хотите сделать?", "welcome"),
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="🔄 Пересчитать карту")],
                    [types.KeyboardButton(text="👁️ Посмотреть текущую карту")],
                    [types.KeyboardButton(text="↩️ Назад в меню")]
                ],
                resize_keyboard=True
            )
        )
        await state.set_state(NatalChartStates.dialog_active)
    else:
        # У пользователя ещё нет натальной карты
        await message.answer(
            add_astro_emoji("Для расчета натальной карты мне нужны данные о вашем рождении.\n\n"
            "Пожалуйста, введите дату вашего рождения в формате ДД.ММ.ГГГГ (например, 15.05.1990).", "welcome"),
            reply_markup=get_back_button()
        )
        await state.set_state(NatalChartStates.waiting_for_date)

async def natal_chart_action_handler(message: types.Message, state: FSMContext):
    """Обработчик выбора действия с натальной картой"""
    if await back_to_menu_handler(message, state):
        return
    
    # Имитируем печать
    await typing_action(message)
    
    if message.text == "🔄 Пересчитать карту":
        await message.answer(
            add_astro_emoji("Хорошо, давайте заново рассчитаем вашу натальную карту.\n\n"
            "Пожалуйста, введите дату вашего рождения в формате ДД.ММ.ГГГГ (например, 15.05.1990)."),
            reply_markup=get_back_button()
        )
        await state.set_state(NatalChartStates.waiting_for_date)
    elif message.text == "👁️ Посмотреть текущую карту":
        user_id = str(message.from_user.id)
        user = operations.get_user(user_id)
        
        if user and user.get("natal_chart"):
            chart_text = user["natal_chart"]
            
            # Имитируем анализ
            await message.answer(add_astro_emoji("Анализирую вашу натальную карту..."))
            await typing_action(message, 2, 3)
            
            # Получаем интерпретацию натальной карты
            interpretation = await generate_natal_chart_interpretation(chart_text, user_id)
            
            # Отправляем карту
            await message.answer(chart_text, reply_markup=get_main_menu())
            
            # Имитируем печать перед отправкой интерпретации
            await typing_action(message, 2, 3)
            
            await message.answer(
                add_astro_emoji(f"Интерпретация вашей натальной карты:\n\n{interpretation}"),
                reply_markup=get_main_menu()
            )
            await state.set_state(NatalChartStates.dialog_active)
        else:
            await message.answer(
                add_astro_emoji("К сожалению, не удалось найти вашу натальную карту. Давайте рассчитаем её заново.", "error"),
                reply_markup=get_back_button()
            )
            await state.set_state(NatalChartStates.waiting_for_date)

async def process_birth_date(message: types.Message, state: FSMContext):
    """Обрабатывает дату рождения пользователя"""
    if await back_to_menu_handler(message, state):
        return
    
    # Имитируем печать
    await typing_action(message)
    
    parsed_date = parse_date_input(message.text.strip())
    if parsed_date:
        await state.update_data(date=parsed_date)
        logger.info(f"Пользователь {message.from_user.id} ввёл дату: {parsed_date}")
        
        await message.answer(
            add_astro_emoji("Отлично! Теперь, пожалуйста, введите время вашего рождения.\n\n"
            "Вы можете указать точное время в формате ЧЧ:ММ (например, 14:30) "
            "или выбрать примерное время суток:", "success"),
            reply_markup=get_time_periods_keyboard()
        )
        await state.set_state(NatalChartStates.waiting_for_time)
    else:
        await message.answer(
            add_astro_emoji("Не удалось распознать дату. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ "
            "(например, 15.05.1990).", "error"),
            reply_markup=get_back_button()
        )

async def process_birth_time(message: types.Message, state: FSMContext):
    """Обрабатывает время рождения пользователя"""
    if await back_to_menu_handler(message, state):
        return
    
    # Имитируем печать
    await typing_action(message)
    
    if message.text == "↩️ Назад":
        await message.answer(
            add_astro_emoji("Пожалуйста, введите дату вашего рождения в формате ДД.ММ.ГГГГ (например, 15.05.1990)."),
            reply_markup=get_back_button()
        )
        await state.set_state(NatalChartStates.waiting_for_date)
        return
    
    # Обрабатываем варианты времени суток
    time_mapping = {
        "Утром (09:00)": "09:00",
        "Днем (15:00)": "15:00",
        "Вечером (21:00)": "21:00",
        "Ночью (03:00)": "03:00"
    }
    
    if message.text in time_mapping:
        parsed_time = time_mapping[message.text]
    else:
        parsed_time = parse_time_input(message.text.strip())
    
    await state.update_data(time=parsed_time)
    logger.info(f"Пользователь {message.from_user.id} ввёл время: {parsed_time}")
    
    await message.answer(
        add_astro_emoji("Хорошо! Теперь, пожалуйста, укажите город вашего рождения.\n\n"
        "Например: Москва, Санкт-Петербург, Нью-Йорк и т.д.", "success"),
        reply_markup=get_back_button()
    )
    await state.set_state(NatalChartStates.waiting_for_city)

async def process_birth_city(message: types.Message, state: FSMContext):
    """Обрабатывает город рождения пользователя"""
    if await back_to_menu_handler(message, state):
        return
    
    # Имитируем печать и поиск
    await typing_action(message, 2, 3)
    
    city = message.text.strip()
    data = await state.get_data()
    date = data.get('date')
    time_str = data.get('time')
    
    try:
        birth_dt = datetime.strptime(f"{date} {time_str}", "%d.%m.%Y %H:%M")
    except Exception as e:
        logger.error(f"Ошибка обработки даты/времени для пользователя {message.from_user.id}: {e}")
        await message.answer(
            add_astro_emoji("Ошибка при обработке даты и времени. Пожалуйста, начните сначала.", "error"),
            reply_markup=get_main_menu()
        )
        await state.clear()
        return
    
    location_info = get_location_info(city, birth_dt)
    if not location_info:
        await message.answer(
            add_astro_emoji("Не удалось определить координаты для этого города. "
            "Пожалуйста, попробуйте другой город или напишите его более точно.", "error"),
            reply_markup=get_back_button()
        )
        return
    
    await state.update_data(
        city=city,
        lat=location_info["lat"],
        lon=location_info["lon"],
        tz_name=location_info["tz_name"],
        gmt_offset=location_info.get("gmt_offset"),
        is_dst=location_info.get("is_dst")
    )
    logger.info(f"Пользователь {message.from_user.id} выбрал город: {city}")
    
    # Форматируем и отправляем найденную информацию о местоположении
    location_message = (
        f"📍 Найденное местоположение: {location_info.get('address', city)}\n"
        f"🌐 Координаты: {location_info['lat']:.6f}, {location_info['lon']:.6f}\n"
        f"🕒 Часовой пояс: {location_info['tz_name']}"
    )
    await message.answer(location_message)
    
    # Имитируем печать перед следующим вопросом
    await typing_action(message)
    
    # Спрашиваем о координатах роддома
    await message.answer(
        add_astro_emoji("Важно: точность координат влияет на расчёт домов гороскопа.\n\n"
        "Знаете ли вы точные координаты роддома или места вашего рождения?", "question"),
        reply_markup=get_yes_no_keyboard()
    )
    await state.set_state(NatalChartStates.waiting_for_hospital_coords_choice)

async def process_coords_choice(message: types.Message, state: FSMContext):
    """Обрабатывает выбор пользователя о предоставлении координат роддома"""
    if await back_to_menu_handler(message, state):
        return
    
    # Имитируем печать
    await typing_action(message)
    
    text = message.text.strip().lower()
    if text == "да":
        logger.info(f"Пользователь {message.from_user.id} согласился предоставить точные координаты")
        await message.answer(
            add_astro_emoji("Пожалуйста, отправьте координаты в формате 'широта, долгота'.\n\n"
            "Например: 55.7558, 37.6176\n\n"
            "Вы можете найти координаты в Google Maps или Яндекс.Картах."),
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(NatalChartStates.waiting_for_hospital_coords)
    elif text == "нет":
        logger.info(f"Пользователь {message.from_user.id} отказался от точных координат")
        await message.answer(
            add_astro_emoji("Хорошо, будем использовать координаты центра города.\n\n"
            "Рассчитываю вашу натальную карту, пожалуйста, подождите...", "success"),
            reply_markup=types.ReplyKeyboardRemove()
        )
        await proceed_with_calculation(message, state)
    else:
        await message.answer(
            add_astro_emoji("Пожалуйста, выберите 'Да' или 'Нет'.", "question"),
            reply_markup=get_yes_no_keyboard()
        )

async def process_hospital_coords(message: types.Message, state: FSMContext):
    """Обрабатывает координаты роддома"""
    if await back_to_menu_handler(message, state):
        return
    
    # Имитируем печать и проверку
    await typing_action(message)
    
    coords = parse_coordinates(message.text.strip())
    if coords:
        lat, lon = coords
        await state.update_data(lat=lat, lon=lon)
        logger.info(f"Пользователь {message.from_user.id} ввёл точные координаты: lat={lat}, lon={lon}")
        
        await message.answer(
            add_astro_emoji(f"Координаты приняты: {lat:.6f}, {lon:.6f}\n\n"
            "Рассчитываю вашу натальную карту, пожалуйста, подождите...", "success"),
            reply_markup=types.ReplyKeyboardRemove()
        )
        await proceed_with_calculation(message, state)
    else:
        await message.answer(
            add_astro_emoji("Неверный формат координат. Пожалуйста, отправьте их в формате 'широта, долгота' "
            "(например, 55.7558, 37.6176).", "error"),
            reply_markup=types.ReplyKeyboardRemove()
        )

async def proceed_with_calculation(message: types.Message, state: FSMContext):
    """Выполняет расчет натальной карты"""
    await state.set_state(NatalChartStates.calculating)
    
    # Имитируем длительный расчет
    calculation_message = await message.answer("🧮 Рассчитываю вашу натальную карту...")
    await typing_action(message, 3, 5)  # Более долгая имитация для расчетов
    
    data = await state.get_data()
    date = data.get('date')
    time_str = data.get('time')
    tz_name = data.get('tz_name', 'UTC')
    lat = data.get('lat')
    lon = data.get('lon')
    
    utc_dt = get_utc_datetime(date, time_str, tz_name)
    if not utc_dt:
        await message.answer(
            add_astro_emoji("Ошибка при расчёте времени в UTC. Пожалуйста, попробуйте позже.", "error"),
            reply_markup=get_main_menu()
        )
        await state.clear()
        return
    
    logger.info(f"Пользователь {message.from_user.id}: UTC = {utc_dt}, lat = {lat}, lon = {lon}")
    
    planets = calculate_planet_positions_utc(utc_dt, lat, lon)
    houses = calculate_houses_utc(utc_dt, lat, lon)
    
    if not planets or not houses:
        await message.answer(
            add_astro_emoji("Ошибка расчёта натальной карты. Пожалуйста, попробуйте позже.", "error"),
            reply_markup=get_main_menu()
        )
        await state.clear()
        return
    
    formatted_chart = format_natal_chart(planets, houses)
    logger.info(f"Натальная карта пользователя {message.from_user.id} рассчитана")
    
    # Удаляем сообщение о расчете
    await calculation_message.delete()
    
    # Сохраняем данные в состоянии
    await state.update_data(planets=planets, houses=houses, formatted_chart=formatted_chart)
    
    # Обновляем данные пользователя в базе
    user_id = str(message.from_user.id)
    operations.update_user_birth_info(
        user_id, 
        date, 
        time_str, 
        data.get('city', ''), 
        lat, 
        lon, 
        tz_name, 
        formatted_chart
    )
    
    # Получаем интерпретацию натальной карты
    await message.answer(add_astro_emoji("Натальная карта рассчитана! Анализирую результаты...", "success"))
    await typing_action(message, 2, 3)
    
    interpretation = await generate_natal_chart_interpretation(formatted_chart, user_id)
    
    # Отправляем результат
    await message.answer(formatted_chart, reply_markup=get_main_menu())
    
    # Имитируем печать перед отправкой интерпретации
    await typing_action(message, 2, 3)
    
    await message.answer(
        add_astro_emoji(f"Интерпретация вашей натальной карты:\n\n{interpretation}"),
        reply_markup=get_main_menu()
    )
    
    await typing_action(message, 1, 2)
    
    await message.answer(
        add_astro_emoji("Теперь вы можете задавать мне вопросы о вашей натальной карте и жизни, "
        "и я буду отвечать с учетом особенностей вашей карты."),
        reply_markup=get_main_menu()
    )
    
    # Переходим в режим диалога
    await state.set_state(NatalChartStates.dialog_active)

def register_handlers(dp: Dispatcher):
    """Регистрирует обработчики для работы с натальной картой"""
    # Команда /natal и кнопка меню
    dp.message.register(natal_chart_command, Command("natal"))
    dp.message.register(natal_chart_command, F.text == "🌟 Моя натальная карта")    
    # Обработчик действий с натальной картой
    dp.message.register(
        natal_chart_action_handler,
        NatalChartStates.dialog_active,
        F.text.in_(["🔄 Пересчитать карту", "👁️ Посмотреть текущую карту"])
    )
    
    # Ввод даты рождения
    dp.message.register(process_birth_date, NatalChartStates.waiting_for_date)
    
    # Ввод времени рождения
    dp.message.register(process_birth_time, NatalChartStates.waiting_for_time)
    
    # Ввод города рождения
    dp.message.register(process_birth_city, NatalChartStates.waiting_for_city)
    
    # Выбор о предоставлении координат
    dp.message.register(process_coords_choice, NatalChartStates.waiting_for_hospital_coords_choice)
    
    # Ввод координат роддома
    dp.message.register(process_hospital_coords, NatalChartStates.waiting_for_hospital_coords)