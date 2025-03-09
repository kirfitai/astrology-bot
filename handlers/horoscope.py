from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from datetime import datetime
import logging

from states.user_states import HoroscopeSettingsStates, NatalChartStates
from utils.keyboards import (
    get_main_menu,
    get_yes_no_keyboard,
    get_horoscope_menu,
    get_horoscope_time_keyboard,
    get_back_button
)
from utils.date_parser import parse_time_input
from services.geo import get_location_info, parse_coordinates
from services.ephemeris import (
    calculate_planet_positions_utc,
    calculate_houses_utc,
    format_natal_chart
)
from services.openai_service import generate_daily_horoscope
from database import operations
from handlers.start import back_to_menu_handler

logger = logging.getLogger(__name__)

async def horoscope_command(message: types.Message, state: FSMContext):
    """Обработчик команды /horoscope и нажатия на кнопку гороскопа"""
    user_id = str(message.from_user.id)
    user = operations.get_user(user_id)
    
    # Проверяем, есть ли у пользователя натальная карта
    if not user or not user.get("natal_chart"):
        await message.answer(
            "Для настройки ежедневного гороскопа сначала нужно рассчитать вашу натальную карту.\n\n"
            "Пожалуйста, используйте команду /natal или нажмите на кнопку 'Моя натальная карта'.",
            reply_markup=get_main_menu()
        )
        return
    
    # Проверяем, настроен ли уже гороскоп
    if user.get("horoscope_time") and user.get("horoscope_city"):
        await message.answer(
            f"📅 Настройки ежедневного гороскопа\n\n"
            f"⏰ Время доставки: {user.get('horoscope_time')}\n"
            f"🌍 Город: {user.get('horoscope_city')}\n\n"
            f"Что вы хотите сделать?",
            reply_markup=get_horoscope_menu()
        )
    else:
        await message.answer(
            "📅 Настройка ежедневного гороскопа\n\n"
            "Ежедневный гороскоп учитывает не только вашу натальную карту, "
            "но и текущее положение планет в выбранном вами месте.\n\n"
            "Сначала укажите, в какое время вы хотели бы получать ежедневный гороскоп:",
            reply_markup=get_horoscope_time_keyboard()
        )
        await state.set_state(HoroscopeSettingsStates.waiting_for_time)

async def horoscope_settings_handler(message: types.Message, state: FSMContext):
    """Обработчик выбора действия в меню настроек гороскопа"""
    if await back_to_menu_handler(message, state):
        return
    
    if message.text == "⏰ Настроить время":
        await message.answer(
            "В какое время вы хотели бы получать ежедневный гороскоп?",
            reply_markup=get_horoscope_time_keyboard()
        )
        await state.set_state(HoroscopeSettingsStates.waiting_for_time)
    
    elif message.text == "🌍 Изменить город":
        await message.answer(
            "Укажите город, в котором вы находитесь. Это нужно для учета текущего положения планет.",
            reply_markup=get_back_button()
        )
        await state.set_state(HoroscopeSettingsStates.waiting_for_city)
    
    elif message.text == "📝 Посмотреть текущие настройки":
        user_id = str(message.from_user.id)
        user = operations.get_user(user_id)
        
        if user.get("horoscope_time") and user.get("horoscope_city"):
            # Получаем последний гороскоп пользователя
            horoscope = operations.get_last_horoscope(user_id)
            
            settings_message = (
                f"📅 Настройки ежедневного гороскопа\n\n"
                f"⏰ Время доставки: {user.get('horoscope_time')}\n"
                f"🌍 Город: {user.get('horoscope_city')}\n"
                f"🌐 Координаты: {user.get('horoscope_latitude', 0):.4f}, {user.get('horoscope_longitude', 0):.4f}\n\n"
            )
            
            if horoscope:
                settings_message += (
                    f"📆 Последний гороскоп был отправлен: {horoscope.get('created_at')}\n\n"
                    f"Хотите получить свежий гороскоп сейчас?"
                )
                
                await message.answer(
                    settings_message,
                    reply_markup=types.ReplyKeyboardMarkup(
                        keyboard=[
                            [types.KeyboardButton(text="✨ Получить свежий гороскоп")],
                            [types.KeyboardButton(text="↩️ Назад")]
                        ],
                        resize_keyboard=True
                    )
                )
                await state.set_state(HoroscopeSettingsStates.confirming_settings)
            else:
                settings_message += "У вас пока нет истории гороскопов."
                await message.answer(settings_message, reply_markup=get_horoscope_menu())
        else:
            await message.answer(
                "У вас еще не настроен ежедневный гороскоп. Давайте его настроим!",
                reply_markup=get_horoscope_menu()
            )

async def process_horoscope_time(message: types.Message, state: FSMContext):
    """Обрабатывает выбор времени для ежедневного гороскопа"""
    if await back_to_menu_handler(message, state):
        return
    
    if message.text == "↩️ Назад":
        user_id = str(message.from_user.id)
        user = operations.get_user(user_id)
        
        if user.get("horoscope_time") and user.get("horoscope_city"):
            await message.answer(
                "Вы вернулись в меню настроек гороскопа.",
                reply_markup=get_horoscope_menu()
            )
        else:
            await message.answer(
                "Настройка гороскопа отменена.",
                reply_markup=get_main_menu()
            )
        
        await state.clear()
        return
    
    time_str = message.text.strip()
    parsed_time = parse_time_input(time_str)
    
    await state.update_data(horoscope_time=parsed_time)
    logger.info(f"Пользователь {message.from_user.id} выбрал время гороскопа: {parsed_time}")
    
    # Проверяем, есть ли уже город в настройках
    user_id = str(message.from_user.id)
    user = operations.get_user(user_id)
    
    if user.get("horoscope_city"):
        # Если город уже есть, обновляем только время
        operations.update_user_horoscope_settings(
            user_id,
            parsed_time,
            user.get("horoscope_city"),
            user.get("horoscope_latitude"),
            user.get("horoscope_longitude")
        )
        
        await message.answer(
            f"✅ Время доставки гороскопа изменено на {parsed_time}.\n\n"
            f"Вы будете получать ежедневный гороскоп в {parsed_time}.",
            reply_markup=get_horoscope_menu()
        )
        
        await state.clear()
    else:
        # Если города еще нет, запрашиваем его
        await message.answer(
            "Отлично! Теперь укажите город, в котором вы находитесь. "
            "Это нужно для учета текущего положения планет.",
            reply_markup=get_back_button()
        )
        await state.set_state(HoroscopeSettingsStates.waiting_for_city)

async def process_horoscope_city(message: types.Message, state: FSMContext):
    """Обрабатывает выбор города для ежедневного гороскопа"""
    if await back_to_menu_handler(message, state):
        return
    
    if message.text == "↩️ Назад":
        await message.answer(
            "В какое время вы хотели бы получать ежедневный гороскоп?",
            reply_markup=get_horoscope_time_keyboard()
        )
        await state.set_state(HoroscopeSettingsStates.waiting_for_time)
        return
    
    city = message.text.strip()
    location_info = get_location_info(city)
    
    if not location_info:
        await message.answer(
            "❌ Не удалось определить координаты для этого города. "
            "Пожалуйста, попробуйте другой город или напишите его более точно.",
            reply_markup=get_back_button()
        )
        return
    
    await state.update_data(
        horoscope_city=city,
        horoscope_latitude=location_info["lat"],
        horoscope_longitude=location_info["lon"]
    )
    logger.info(f"Пользователь {message.from_user.id} выбрал город для гороскопа: {city}")
    
    # Форматируем и отправляем найденную информацию о местоположении
    location_message = (
        f"📍 Найденное местоположение: {location_info.get('address', city)}\n"
        f"🌐 Координаты: {location_info['lat']:.6f}, {location_info['lon']:.6f}\n"
        f"🕒 Часовой пояс: {location_info['tz_name']}"
    )
    await message.answer(location_message)
    
    # Спрашиваем о координатах
    await message.answer(
        "Хотите указать более точные координаты для более точного гороскопа?",
        reply_markup=get_yes_no_keyboard()
    )
    await state.set_state(HoroscopeSettingsStates.waiting_for_coords_choice)

async def process_coords_choice(message: types.Message, state: FSMContext):
    """Обрабатывает выбор пользователя о предоставлении точных координат"""
    if await back_to_menu_handler(message, state):
        return
        
    text = message.text.strip().lower()
    
    if text == "да":
        logger.info(f"Пользователь {message.from_user.id} согласился предоставить точные координаты для гороскопа")
        await message.answer(
            "Пожалуйста, отправьте координаты в формате 'широта, долгота'.\n\n"
            "Например: 55.7558, 37.6176\n\n"
            "Вы можете найти координаты в Google Maps или Яндекс.Картах.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(HoroscopeSettingsStates.waiting_for_coords)
    elif text == "нет":
        logger.info(f"Пользователь {message.from_user.id} отказался от точных координат для гороскопа")
        
        # Сохраняем настройки гороскопа
        data = await state.get_data()
        horoscope_time = data.get('horoscope_time')
        horoscope_city = data.get('horoscope_city')
        horoscope_lat = data.get('horoscope_latitude')
        horoscope_lon = data.get('horoscope_longitude')
        
        user_id = str(message.from_user.id)
        operations.update_user_horoscope_settings(
            user_id,
            horoscope_time,
            horoscope_city,
            horoscope_lat,
            horoscope_lon
        )
        
        await message.answer(
            f"✅ Настройки гороскопа сохранены!\n\n"
            f"⏰ Время доставки: {horoscope_time}\n"
            f"🌍 Город: {horoscope_city}\n\n"
            f"Вы будете получать ежедневный персонализированный гороскоп в {horoscope_time}.\n\n"
            f"Хотите получить первый гороскоп прямо сейчас?",
            reply_markup=get_yes_no_keyboard()
        )
        await state.set_state(HoroscopeSettingsStates.confirming_settings)
    else:
        await message.answer(
            "Пожалуйста, выберите 'Да' или 'Нет'.",
            reply_markup=get_yes_no_keyboard()
        )

async def process_coords(message: types.Message, state: FSMContext):
    """Обрабатывает координаты для гороскопа"""
    if await back_to_menu_handler(message, state):
        return
        
    coords = parse_coordinates(message.text.strip())
    if coords:
        lat, lon = coords
        
        await state.update_data(horoscope_latitude=lat, horoscope_longitude=lon)
        logger.info(f"Пользователь {message.from_user.id} ввёл точные координаты для гороскопа: lat={lat}, lon={lon}")
        
        # Сохраняем настройки гороскопа
        data = await state.get_data()
        horoscope_time = data.get('horoscope_time')
        horoscope_city = data.get('horoscope_city')
        
        user_id = str(message.from_user.id)
        operations.update_user_horoscope_settings(
            user_id,
            horoscope_time,
            horoscope_city,
            lat,
            lon
        )
        
        await message.answer(
            f"✅ Настройки гороскопа сохранены!\n\n"
            f"⏰ Время доставки: {horoscope_time}\n"
            f"🌍 Город: {horoscope_city}\n"
            f"🌐 Координаты: {lat:.6f}, {lon:.6f}\n\n"
            f"Вы будете получать ежедневный персонализированный гороскоп в {horoscope_time}.\n\n"
            f"Хотите получить первый гороскоп прямо сейчас?",
            reply_markup=get_yes_no_keyboard()
        )
        await state.set_state(HoroscopeSettingsStates.confirming_settings)
    else:
        await message.answer(
            "❌ Неверный формат координат. Пожалуйста, отправьте их в формате 'широта, долгота' "
            "(например, 55.7558, 37.6176).",
            reply_markup=types.ReplyKeyboardRemove()
        )

async def confirm_settings(message: types.Message, state: FSMContext):
    """Обрабатывает подтверждение настроек и запрос гороскопа"""
    if await back_to_menu_handler(message, state):
        return
    
    if message.text == "↩️ Назад":
        await message.answer(
            "Вы вернулись в меню настроек гороскопа.",
            reply_markup=get_horoscope_menu()
        )
        await state.clear()
        return
    
    if message.text.lower() == "да" or message.text == "✨ Получить свежий гороскоп":
        user_id = str(message.from_user.id)
        user = operations.get_user(user_id)
        
        if not user or not user.get("natal_chart"):
            await message.answer(
                "Для получения гороскопа сначала нужно рассчитать вашу натальную карту.",
                reply_markup=get_main_menu()
            )
            await state.clear()
            return
        
        await message.answer(
            "✨ Составляю персональный гороскоп, пожалуйста, подождите...",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        # Рассчитываем текущее положение планет
        now = datetime.now()
        lat = user.get("horoscope_latitude", 0)
        lon = user.get("horoscope_longitude", 0)
        
        planets = calculate_planet_positions_utc(now, lat, lon)
        houses = calculate_houses_utc(now, lat, lon)
        
        if not planets or not houses:
            await message.answer(
                "❌ Ошибка расчёта положения планет. Пожалуйста, попробуйте позже.",
                reply_markup=get_main_menu()
            )
            await state.clear()
            return
        
        formatted_planets = format_natal_chart(planets, houses)
        
        # Определяем, является ли пользователь премиум-подписчиком
        is_premium = user.get("subscription_type") != "free"
        
        # Генерируем гороскоп
        natal_chart = user.get("natal_chart", "")
        horoscope_text = await generate_daily_horoscope(
            natal_chart,
            formatted_planets,
            user_id,
            is_premium
        )
        
        # Сохраняем гороскоп в базу
        operations.add_horoscope(user_id, horoscope_text)
        
        # Отправляем гороскоп
        await message.answer(
            f"🌟 Ваш персональный гороскоп на {now.strftime('%d.%m.%Y')}:\n\n{horoscope_text}",
            reply_markup=get_main_menu()
        )
        
        # Если пользователь не премиум, предлагаем подписку
        if not is_premium:
            await message.answer(
                "💡 Хотите получать более подробный гороскоп каждый день?\n\n"
                "С премиум-подпиской вы получите расширенный гороскоп с детальным анализом "
                "всех сфер жизни и персональными рекомендациями на день.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="💎 Узнать о премиум-подписке", callback_data="premium_info")]
                    ]
                )
            )
        
        await state.set_state(NatalChartStates.dialog_active)
    elif message.text.lower() == "нет":
        await message.answer(
            "Хорошо! Вы получите свой первый гороскоп в выбранное время.",
            reply_markup=get_main_menu()
        )
        await state.clear()
    else:
        await message.answer(
            "Пожалуйста, выберите 'Да' или 'Нет'.",
            reply_markup=get_yes_no_keyboard()
        )

async def premium_info_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку информации о премиум-подписке"""
    await callback.answer()
    
    premium_info = (
        "💎 Премиум-подписка — расширенные возможности для вас!\n\n"
        "• Подробный ежедневный гороскоп с анализом всех сфер жизни\n"
        "• Неограниченное количество проверок совместимости\n"
        "• Безлимитное общение с астрологическим ассистентом\n"
        "• Еженедельные и ежемесячные прогнозы\n"
        "• Специальные аспекты планет и их влияние на вас\n\n"
        "Стоимость подписки:\n"
        "1 месяц — $4.99\n"
        "3 месяца — $9.99\n"
        "1 год — $29.99"
    )
    
    await callback.message.answer(
        premium_info,
        reply_markup=types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(text="💳 Оформить подписку", callback_data="subscribe_menu")]
            ]
        )
    )

def register_handlers(dp: Dispatcher):
    """Регистрирует обработчики для работы с гороскопами"""
    # Команда /horoscope и кнопка меню
    dp.message.register(horoscope_command, Command("horoscope"))
    dp.message.register(horoscope_command, F.text == "🔮 Гороскоп")
    
    # Обработчик выбора действия в меню настроек гороскопа
    dp.message.register(
        horoscope_settings_handler,
        F.text.in_(["⏰ Настроить время", "🌍 Изменить город", "📝 Посмотреть текущие настройки"])
    )
    
    # Ввод времени для гороскопа
    dp.message.register(process_horoscope_time, HoroscopeSettingsStates.waiting_for_time)
    
    # Ввод города для гороскопа
    dp.message.register(process_horoscope_city, HoroscopeSettingsStates.waiting_for_city)
    
    # Выбор о предоставлении координат
    dp.message.register(process_coords_choice, HoroscopeSettingsStates.waiting_for_coords_choice)
    
    # Ввод координат
    dp.message.register(process_coords, HoroscopeSettingsStates.waiting_for_coords)
    
    # Подтверждение настроек и запрос гороскопа
    dp.message.register(confirm_settings, HoroscopeSettingsStates.confirming_settings)
    
    # Обработчик нажатия на кнопку информации о премиум-подписке
    dp.callback_query.register(premium_info_callback, lambda c: c.data == "premium_info")