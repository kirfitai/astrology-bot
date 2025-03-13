from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from aiogram.fsm.context import FSMContext
from datetime import datetime
import logging

from states.user_states import CompatibilityStates, NatalChartStates
from utils.keyboards import (
    get_main_menu,
    get_yes_no_keyboard,
    get_time_periods_keyboard,
    get_back_button,
    get_compatibility_menu,
    get_contacts_keyboard,
    get_inline_contact_actions
)
from utils.date_parser import parse_date_input, parse_time_input
from services.geo import get_location_info, get_utc_datetime, parse_coordinates
from services.ephemeris import (
    calculate_planet_positions_utc,
    calculate_houses_utc,
    format_natal_chart,
    get_aspects_between_charts,
    format_aspects
)
from services.openai_service import generate_compatibility_analysis
from database import operations
from handlers.start import back_to_menu_handler

logger = logging.getLogger(__name__)

async def compatibility_command(message: types.Message, state: FSMContext):
    """Обработчик команды /compatibility и нажатия на кнопку совместимости"""
    user_id = str(message.from_user.id)
    user = operations.get_user(user_id)
    
    # Проверяем, есть ли у пользователя натальная карта
    if not user or not user.get("natal_chart"):
        await message.answer(
            "Для проверки совместимости сначала нужно рассчитать вашу натальную карту.\n\n"
            "Пожалуйста, используйте команду /natal или нажмите на кнопку 'Моя натальная карта'.",
            reply_markup=get_main_menu()
        )
        return
    
    # Получаем контакты пользователя
    contacts = operations.get_contacts(user_id)
    
    # Показываем меню совместимости
    await message.answer(
        "💞 Проверка совместимости\n\n"
        "С кем бы вы хотели проверить совместимость?",
        reply_markup=get_compatibility_menu()
    )
    
    await state.set_state(CompatibilityStates.selecting_action)

async def compatibility_action_handler(message: types.Message, state: FSMContext):
    """Обработчик выбора действия в меню совместимости"""
    if await back_to_menu_handler(message, state):
        return
    
    user_id = str(message.from_user.id)
    
    if message.text == "➕ Добавить новый контакт":
        await message.answer(
            "Введите имя человека, с которым хотите проверить совместимость:",
            reply_markup=get_back_button()
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_name)
    
    elif message.text == "📋 Мои контакты":
        contacts = operations.get_contacts(user_id)
        
        if not contacts:
            await message.answer(
                "У вас пока нет сохраненных контактов.\n\n"
                "Давайте добавим новый контакт!",
                reply_markup=get_back_button()
            )
            await state.set_state(CompatibilityStates.waiting_for_partner_name)
            return
        
        # Формируем список контактов
        contacts_text = "📋 Ваши контакты для проверки совместимости:\n\n"
        for i, contact in enumerate(contacts, 1):
            contacts_text += f"{i}. {contact['person_name']} ({contact['relationship']})\n"
        
        await message.answer(
            contacts_text + "\nВыберите контакт или добавьте новый:",
            reply_markup=get_contacts_keyboard(contacts)
        )
        await state.set_state(CompatibilityStates.selecting_contact)

async def contact_selection_handler(message: types.Message, state: FSMContext):
    """Обработчик выбора контакта из списка"""
    if await back_to_menu_handler(message, state):
        return
    
    if message.text == "↩️ Назад":
        await message.answer(
            "💞 Проверка совместимости\n\n"
            "С кем бы вы хотели проверить совместимость?",
            reply_markup=get_compatibility_menu()
        )
        await state.set_state(CompatibilityStates.selecting_action)
        return
    
    if message.text == "➕ Добавить контакт":
        await message.answer(
            "Введите имя человека, с которым хотите проверить совместимость:",
            reply_markup=get_back_button()
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_name)
        return
    
    # Извлекаем имя контакта из кнопки
    if message.text.startswith("👤 "):
        contact_name = message.text[2:].strip()
        
        user_id = str(message.from_user.id)
        contacts = operations.get_contacts(user_id)
        
        selected_contact = None
        for contact in contacts:
            if contact['person_name'] == contact_name:
                selected_contact = contact
                break
        
        if selected_contact:
            # Сохраняем ID контакта в состоянии
            await state.update_data(selected_contact_id=selected_contact['contact_id'])
            
            # Показываем информацию о контакте и предлагаем действия
            contact_info = (
                f"👤 {selected_contact['person_name']}\n"
                f"📅 Дата рождения: {selected_contact['birth_date']}\n"
                f"🕒 Время рождения: {selected_contact['birth_time']}\n"
                f"📍 Место рождения: {selected_contact['city']}\n"
                f"👫 Отношение: {selected_contact['relationship']}\n\n"
                "Что вы хотите сделать с этим контактом?"
            )
            
            await message.answer(
                contact_info,
                reply_markup=get_inline_contact_actions(selected_contact['contact_id'])
            )
            
            # Ожидаем выбора действия с контактом через inline кнопки
            await state.set_state(CompatibilityStates.viewing_result)
        else:
            await message.answer(
                "Контакт не найден. Пожалуйста, выберите контакт из списка.",
                reply_markup=get_contacts_keyboard(contacts)
            )

async def contact_action_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик действий с контактом через inline кнопки"""
    action, contact_id = callback.data.split(":")
    contact_id = int(contact_id)
    
    user_id = str(callback.from_user.id)
    contact = operations.get_contact(contact_id)
    
    if not contact or contact['user_id'] != user_id:
        await callback.answer("Контакт не найден или не принадлежит вам.")
        return
    
    if action == "compatibility":
        # Получаем натальную карту пользователя
        user = operations.get_user(user_id)
        
        if not user or not user.get("natal_chart"):
            await callback.answer("Сначала необходимо рассчитать вашу натальную карту.")
            await callback.message.answer(
                "Для проверки совместимости сначала нужно рассчитать вашу натальную карту.",
                reply_markup=get_main_menu()
            )
            return
        
        await callback.answer("Рассчитываю совместимость...")
        
        # Обновляем сообщение, чтобы показать, что идет расчет
        await callback.message.edit_text(
            f"🔄 Рассчитываю совместимость с {contact['person_name']}...\n\n"
            "Пожалуйста, подождите."
        )
        
        # Рассчитываем совместимость
        user_chart = user["natal_chart"]
        partner_chart = contact["natal_chart"]
        relationship = contact["relationship"]
        
        # Генерируем анализ совместимости
        analysis = await generate_compatibility_analysis(
            user_chart, 
            partner_chart, 
            relationship, 
            user_id
        )
        
        # Сохраняем анализ в базу
        operations.add_compatibility_analysis(user_id, contact_id, analysis)
        
        # Проверяем, является ли пользователь премиум
        is_premium = user.get("subscription_type") != "free"
        
        # Получаем количество контактов
        contacts_count = len(operations.get_contacts(user_id))
        
        # Если это второй или более контакт, и пользователь на бесплатном тарифе,
        # отправляем заблюренное сообщение и предложение
        if contacts_count > 1 and not is_premium:
            # Показываем заблюренный результат и предложение оплаты
            preview_analysis = analysis[:150] + "..." if len(analysis) > 150 else analysis
            
            await callback.message.answer(
                f"💞 Результат анализа совместимости с {contact['person_name']}:\n\n"
                f"{preview_analysis}\n\n"
                "<span class='tg-spoiler'>Полный результат анализа скрыт. Для просмотра полного анализа требуется подписка.</span>",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text=f"💎 Разблокировать анализ (90 ⭐️)", callback_data=f"unlock_compatibility:{contact_id}")],
                        [types.InlineKeyboardButton(text="💎 Оформить подписку", callback_data="subscribe_menu")]
                    ]
                )
            )
        else:
            # Отправляем полный результат
            await callback.message.answer(
                f"💞 Результат анализа совместимости с {contact['person_name']}:\n\n{analysis}",
                reply_markup=get_main_menu()
            )
        
        # Возвращаемся в режим диалога
        await state.set_state(NatalChartStates.dialog_active)
    
    elif action == "edit_contact":
        # Готовимся к редактированию контакта
        await callback.answer("Редактирование контакта")
        
        # Сохраняем ID контакта в состоянии
        await state.update_data(
            contact_id=contact_id,
            edit_mode=True,
            partner_name=contact['person_name']
        )
        
        await callback.message.answer(
            f"Редактирование контакта: {contact['person_name']}\n\n"
            "Введите новую дату рождения (или оставьте текущую):",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text=f"Оставить текущую: {contact['birth_date']}")],
                    [types.KeyboardButton(text="↩️ Отмена")]
                ],
                resize_keyboard=True
            )
        )
        
        await state.set_state(CompatibilityStates.waiting_for_partner_birth_date)
    
    elif action == "delete_contact":
        # Удаляем контакт
        if operations.delete_contact(contact_id, user_id):
            await callback.answer("Контакт успешно удалён")
            await callback.message.edit_text(f"Контакт {contact['person_name']} был удалён.")
            
            # Возвращаемся к списку контактов
            contacts = operations.get_contacts(user_id)
            
            if contacts:
                await callback.message.answer(
                    "Выберите другой контакт или добавьте новый:",
                    reply_markup=get_contacts_keyboard(contacts)
                )
                await state.set_state(CompatibilityStates.selecting_contact)
            else:
                await callback.message.answer(
                    "У вас больше нет сохраненных контактов.\n\n"
                    "Хотите добавить новый контакт?",
                    reply_markup=get_compatibility_menu()
                )
                await state.set_state(CompatibilityStates.selecting_action)
        else:
            await callback.answer("Не удалось удалить контакт", show_alert=True)

async def process_partner_name(message: types.Message, state: FSMContext):
    """Обрабатывает имя партнера"""
    if await back_to_menu_handler(message, state):
        return
    
    partner_name = message.text.strip()
    
    # Проверяем на пустое имя
    if not partner_name:
        await message.answer(
            "Имя не может быть пустым. Пожалуйста, введите имя партнера:",
            reply_markup=get_back_button()
        )
        return
    
    # Сохраняем имя в состоянии
    await state.update_data(partner_name=partner_name)
    logger.info(f"Пользователь {message.from_user.id} ввёл имя партнёра: {partner_name}")
    
    # Проверяем, есть ли уже контакт с таким именем
    user_id = str(message.from_user.id)
    contacts = operations.get_contacts(user_id)
    
    existing_contact = None
    for contact in contacts:
        if contact['person_name'].lower() == partner_name.lower():
            existing_contact = contact
            break
    
    if existing_contact:
        await message.answer(
            f"У вас уже есть контакт с именем {partner_name}.\n\n"
            "Хотите использовать существующие данные или перезаписать их?",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text="Использовать существующие")],
                    [types.KeyboardButton(text="Перезаписать")],
                    [types.KeyboardButton(text="↩️ Назад")]
                ],
                resize_keyboard=True
            )
        )
        await state.update_data(existing_contact_id=existing_contact['contact_id'])
        await state.set_state(CompatibilityStates.selecting_action)  # Временный state для выбора действия
    else:
        await message.answer(
            f"Отлично! Теперь введите дату рождения {partner_name} в формате ДД.ММ.ГГГГ "
            "(например, 15.05.1990):",
            reply_markup=get_back_button()
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_birth_date)

async def process_existing_contact_action(message: types.Message, state: FSMContext):
    """Обрабатывает выбор действия для существующего контакта"""
    if await back_to_menu_handler(message, state):
        return
    
    if message.text == "↩️ Назад":
        await message.answer(
            "Введите имя человека, с которым хотите проверить совместимость:",
            reply_markup=get_back_button()
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_name)
        return
    
    data = await state.get_data()
    partner_name = data.get('partner_name')
    existing_contact_id = data.get('existing_contact_id')
    
    if message.text == "Использовать существующие":
        # Используем существующий контакт
        contact = operations.get_contact(existing_contact_id)
        
        if contact:
            # Переходим к расчету совместимости
            user_id = str(message.from_user.id)
            user = operations.get_user(user_id)
            
            if not user or not user.get("natal_chart"):
                await message.answer(
                    "Для проверки совместимости сначала нужно рассчитать вашу натальную карту.",
                    reply_markup=get_main_menu()
                )
                await state.clear()
                return
            
            await message.answer(
                f"🔄 Рассчитываю совместимость с {contact['person_name']}...\n\n"
                "Пожалуйста, подождите.",
                reply_markup=types.ReplyKeyboardRemove()
            )
            
            # Рассчитываем совместимость
            user_chart = user["natal_chart"]
            partner_chart = contact["natal_chart"]
            relationship = contact["relationship"]
            
            # Генерируем анализ совместимости
            analysis = await generate_compatibility_analysis(
                user_chart, 
                partner_chart, 
                relationship, 
                user_id
            )
            
            # Сохраняем анализ в базу
            operations.add_compatibility_analysis(user_id, existing_contact_id, analysis)
            
            # Проверяем, является ли пользователь премиум
            is_premium = user.get("subscription_type") != "free"
            
            # Получаем количество контактов
            contacts_count = len(operations.get_contacts(user_id))
            
            # Если это второй или более контакт, и пользователь на бесплатном тарифе,
            # отправляем заблюренное сообщение и предложение
            if contacts_count > 1 and not is_premium:
                # Показываем заблюренный результат и предложение оплаты
                preview_analysis = analysis[:150] + "..." if len(analysis) > 150 else analysis
                
                await message.answer(
                    f"💞 Результат анализа совместимости с {contact['person_name']}:\n\n"
                    f"{preview_analysis}\n\n"
                    "<span class='tg-spoiler'>Полный результат анализа скрыт. Для просмотра полного анализа требуется подписка.</span>",
                    parse_mode="HTML",
                    reply_markup=types.InlineKeyboardMarkup(
                        inline_keyboard=[
                            [types.InlineKeyboardButton(text=f"💎 Разблокировать анализ (90 ⭐️)", callback_data=f"unlock_compatibility:{existing_contact_id}")],
                            [types.InlineKeyboardButton(text="💎 Оформить подписку", callback_data="subscribe_menu")]
                        ]
                    )
                )
            else:
                # Разбиваем длинное сообщение на части (максимум 4000 символов для безопасности)
                chunks = []
                max_chunk_size = 4000
                header = f"💞 Результат анализа совместимости с {contact['person_name']}:\n\n"

                if len(header) + len(analysis) <= max_chunk_size:
                    # Если сообщение достаточно короткое, отправляем как есть
                    chunks = [header + analysis]
                else:
                    # Добавляем заголовок к первой части
                    current_chunk = header
        
                    # Разбиваем по абзацам для сохранения структуры
                    paragraphs = analysis.split('\n\n')
        
                    for paragraph in paragraphs:
                        # Если текущий абзац не помещается в текущий чанк, создаем новый
                        if len(current_chunk) + len(paragraph) + 2 > max_chunk_size:
                            chunks.append(current_chunk)
                            current_chunk = ""
            
                        # Добавляем абзац к текущему чанку
                        if current_chunk and paragraph:
                            current_chunk += "\n\n"
                        current_chunk += paragraph
        
                    # Добавляем последний чанк, если он не пустой
                    if current_chunk:
                        chunks.append(current_chunk)

                # Отправляем все части сообщения
                for i, chunk in enumerate(chunks):
                    # Добавляем номер части, если частей больше одной
                    if len(chunks) > 1:
                        part_indicator = f"[Часть {i+1}/{len(chunks)}]\n"
                        chunk = part_indicator + chunk
                    
                    # Клавиатуру добавляем только к последнему сообщению
                    if i == len(chunks) - 1:
                        await message.answer(chunk, reply_markup=get_main_menu())
                    else:
                        await message.answer(chunk)
            
            # Возвращаемся в режим диалога
            await state.set_state(NatalChartStates.dialog_active)
        else:
            await message.answer(
                "Контакт не найден. Давайте добавим новые данные.",
                reply_markup=get_back_button()
            )
            await state.set_state(CompatibilityStates.waiting_for_partner_birth_date)
    
    elif message.text == "Перезаписать":
        # Перезаписываем существующий контакт
        await message.answer(
            f"Хорошо, давайте обновим данные для {partner_name}.\n\n"
            f"Введите дату рождения {partner_name} в формате ДД.ММ.ГГГГ "
            "(например, 15.05.1990):",
            reply_markup=get_back_button()
        )
        await state.update_data(edit_mode=True, contact_id=existing_contact_id)
        await state.set_state(CompatibilityStates.waiting_for_partner_birth_date)

async def process_partner_birth_date(message: types.Message, state: FSMContext):
    """Обрабатывает дату рождения партнера"""
    if await back_to_menu_handler(message, state):
        return
    
    data = await state.get_data()
    partner_name = data.get('partner_name')
    edit_mode = data.get('edit_mode', False)
    
    # Проверяем, если пользователь решил оставить текущую дату
    if message.text.startswith("Оставить текущую:"):
        # Извлекаем дату из сообщения
        current_date = message.text.split(":")[1].strip()
        
        await state.update_data(partner_birth_date=current_date)
        logger.info(f"Пользователь {message.from_user.id} оставил текущую дату: {current_date}")
        
        # Переходим к вводу времени
        contact_id = data.get('contact_id')
        contact = operations.get_contact(contact_id)
        
        await message.answer(
            f"Введите время рождения {partner_name} (или оставьте текущее):",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text=f"Оставить текущее: {contact['birth_time']}")],
                    [types.KeyboardButton(text="↩️ Отмена")]
                ],
                resize_keyboard=True
            )
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_birth_time)
        return
    
    if message.text == "↩️ Отмена" and edit_mode:
        # Отменяем редактирование и возвращаемся к списку контактов
        user_id = str(message.from_user.id)
        contacts = operations.get_contacts(user_id)
        
        await message.answer(
            "Редактирование отменено.",
            reply_markup=get_contacts_keyboard(contacts)
        )
        await state.set_state(CompatibilityStates.selecting_contact)
        return
    
    parsed_date = parse_date_input(message.text.strip())
    if parsed_date:
        await state.update_data(partner_birth_date=parsed_date)
        logger.info(f"Пользователь {message.from_user.id} ввёл дату партнёра: {parsed_date}")
        
        await message.answer(
            f"Отлично! Теперь введите время рождения {partner_name}.\n\n"
            "Вы можете указать точное время в формате ЧЧ:ММ (например, 14:30) "
            "или выбрать примерное время суток:",
            reply_markup=get_time_periods_keyboard()
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_birth_time)
    else:
        await message.answer(
            "❌ Не удалось распознать дату. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ "
            "(например, 15.05.1990).",
            reply_markup=get_back_button()
        )

async def process_partner_birth_time(message: types.Message, state: FSMContext):
    """Обрабатывает время рождения партнера"""
    if await back_to_menu_handler(message, state):
        return
    
    data = await state.get_data()
    partner_name = data.get('partner_name')
    edit_mode = data.get('edit_mode', False)
    
    if message.text == "↩️ Назад":
        await message.answer(
            f"Введите дату рождения {partner_name} в формате ДД.ММ.ГГГГ (например, 15.05.1990):",
            reply_markup=get_back_button()
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_birth_date)
        return
    
    if message.text == "↩️ Отмена" and edit_mode:
        # Отменяем редактирование и возвращаемся к списку контактов
        user_id = str(message.from_user.id)
        contacts = operations.get_contacts(user_id)
        
        await message.answer(
            "Редактирование отменено.",
            reply_markup=get_contacts_keyboard(contacts)
        )
        await state.set_state(CompatibilityStates.selecting_contact)
        return
    
    # Проверяем, если пользователь решил оставить текущее время
    if message.text.startswith("Оставить текущее:"):
        # Извлекаем время из сообщения
        current_time = message.text.split(":")[1].strip()
        
        await state.update_data(partner_birth_time=current_time)
        logger.info(f"Пользователь {message.from_user.id} оставил текущее время: {current_time}")
        
        # Переходим к вводу города
        contact_id = data.get('contact_id')
        contact = operations.get_contact(contact_id)
        
        await message.answer(
            f"Введите город рождения {partner_name} (или оставьте текущий):",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text=f"Оставить текущий: {contact['city']}")],
                    [types.KeyboardButton(text="↩️ Отмена")]
                ],
                resize_keyboard=True
            )
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_city)
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
    
    await state.update_data(partner_birth_time=parsed_time)
    logger.info(f"Пользователь {message.from_user.id} ввёл время партнёра: {parsed_time}")
    
    await message.answer(
        f"Хорошо! Теперь, пожалуйста, укажите город рождения {partner_name}.\n\n"
        "Например: Москва, Санкт-Петербург, Нью-Йорк и т.д.",
        reply_markup=get_back_button()
    )
    await state.set_state(CompatibilityStates.waiting_for_partner_city)

async def process_partner_birth_city(message: types.Message, state: FSMContext):
    """Обрабатывает город рождения партнера"""
    if await back_to_menu_handler(message, state):
        return
    
    data = await state.get_data()
    partner_name = data.get('partner_name')
    edit_mode = data.get('edit_mode', False)
    
    if message.text == "↩️ Назад":
        await message.answer(
            f"Введите время рождения {partner_name}.\n\n"
            "Вы можете указать точное время в формате ЧЧ:ММ (например, 14:30) "
            "или выбрать примерное время суток:",
            reply_markup=get_time_periods_keyboard()
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_birth_time)
        return
    
    if message.text == "↩️ Отмена" and edit_mode:
        # Отменяем редактирование и возвращаемся к списку контактов
        user_id = str(message.from_user.id)
        contacts = operations.get_contacts(user_id)
        
        await message.answer(
            "Редактирование отменено.",
            reply_markup=get_contacts_keyboard(contacts)
        )
        await state.set_state(CompatibilityStates.selecting_contact)
        return
    
    # Проверяем, если пользователь решил оставить текущий город
    if message.text.startswith("Оставить текущий:"):
        # Извлекаем город из сообщения
        current_city = message.text.split(":")[1].strip()
        
        await state.update_data(partner_city=current_city)
        logger.info(f"Пользователь {message.from_user.id} оставил текущий город: {current_city}")
        
        # Переходим к вводу отношения
        contact_id = data.get('contact_id')
        contact = operations.get_contact(contact_id)
        
        await message.answer(
            f"Укажите, кем {partner_name} приходится вам (например, 'девушка', 'муж', 'друг', 'коллега' и т.д.) "
            "или оставьте текущее отношение:",
            reply_markup=types.ReplyKeyboardMarkup(
                keyboard=[
                    [types.KeyboardButton(text=f"Оставить текущее: {contact['relationship']}")],
                    [types.KeyboardButton(text="↩️ Отмена")]
                ],
                resize_keyboard=True
            )
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_relationship)
        return
    
    partner_city = message.text.strip()
    partner_birth_date = data.get("partner_birth_date")
    partner_birth_time = data.get("partner_birth_time")
    
    try:
        partner_birth_dt = datetime.strptime(f"{partner_birth_date} {partner_birth_time}", "%d.%m.%Y %H:%M")
    except Exception as e:
        logger.error(f"Ошибка обработки даты/времени партнёра для пользователя {message.from_user.id}: {e}")
        await message.answer(
            "❌ Ошибка при обработке даты и времени партнёра. Пожалуйста, попробуйте снова.",
            reply_markup=get_main_menu()
        )
        await state.clear()
        return
    
    location_info = get_location_info(partner_city, partner_birth_dt)
    if not location_info:
        await message.answer(
            "❌ Не удалось определить координаты для этого города. "
            "Пожалуйста, попробуйте другой город или напишите его более точно.",
            reply_markup=get_back_button()
        )
        return
    
    await state.update_data(
        partner_city=partner_city,
        partner_lat=location_info["lat"],
        partner_lon=location_info["lon"],
        partner_tz_name=location_info["tz_name"],
        partner_gmt_offset=location_info.get("gmt_offset"),
        partner_is_dst=location_info.get("is_dst")
    )
    logger.info(f"Партнерский город для пользователя {message.from_user.id}: {partner_city}")
    
    # Форматируем и отправляем найденную информацию о местоположении
    location_message = (
        f"📍 Найденное местоположение: {location_info.get('address', partner_city)}\n"
        f"🌐 Координаты: {location_info['lat']:.6f}, {location_info['lon']:.6f}\n"
        f"🕒 Часовой пояс: {location_info['tz_name']}"
    )
    await message.answer(location_message)
    
    await message.answer(
        f"Укажите, кем {partner_name} приходится вам (например, 'девушка', 'муж', 'друг', 'коллега' и т.д.):",
        reply_markup=get_back_button()
    )
    await state.set_state(CompatibilityStates.waiting_for_partner_relationship)

async def process_partner_relationship(message: types.Message, state: FSMContext):
    """Обрабатывает отношение партнера к пользователю"""
    if await back_to_menu_handler(message, state):
        return
    
    data = await state.get_data()
    partner_name = data.get('partner_name')
    edit_mode = data.get('edit_mode', False)
    
    if message.text == "↩️ Назад":
        await message.answer(
            f"Укажите город рождения {partner_name}:",
            reply_markup=get_back_button()
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_city)
        return
    
    if message.text == "↩️ Отмена" and edit_mode:
        # Отменяем редактирование и возвращаемся к списку контактов
        user_id = str(message.from_user.id)
        contacts = operations.get_contacts(user_id)
        
        await message.answer(
            "Редактирование отменено.",
            reply_markup=get_contacts_keyboard(contacts)
        )
        await state.set_state(CompatibilityStates.selecting_contact)
        return
    
    # Проверяем, если пользователь решил оставить текущее отношение
    if message.text.startswith("Оставить текущее:"):
        # Извлекаем отношение из сообщения
        current_relationship = message.text.split(":")[1].strip()
        
        await state.update_data(partner_relationship=current_relationship)
        logger.info(f"Пользователь {message.from_user.id} оставил текущее отношение: {current_relationship}")
        
        # Переходим к расчету совместимости
        await message.answer(
            f"✅ Данные о {partner_name} обновлены!\n\n"
            "Теперь можем рассчитать совместимость.",
            reply_markup=get_yes_no_keyboard()
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_coords_choice)
        return
    
    partner_relationship = message.text.strip()
    await state.update_data(partner_relationship=partner_relationship)
    logger.info(f"Партнерская принадлежность для пользователя {message.from_user.id}: {partner_relationship}")
    
    # Спрашиваем о координатах роддома
    await message.answer(
        "Важно: точность координат влияет на расчёт совместимости.\n\n"
        f"Знаете ли вы точные координаты места рождения {partner_name}?",
        reply_markup=get_yes_no_keyboard()
    )
    await state.set_state(CompatibilityStates.waiting_for_partner_coords_choice)

async def process_partner_coords_choice(message: types.Message, state: FSMContext):
    """Обрабатывает выбор пользователя о предоставлении координат партнера"""
    if await back_to_menu_handler(message, state):
        return
        
    text = message.text.strip().lower()
    data = await state.get_data()
    partner_name = data.get('partner_name')
    
    if text == "да":
        logger.info(f"Пользователь {message.from_user.id} согласился предоставить точные координаты партнёра")
        await message.answer(
            "Пожалуйста, отправьте координаты в формате 'широта, долгота'.\n\n"
            "Например: 55.7558, 37.6176\n\n"
            "Вы можете найти координаты в Google Maps или Яндекс.Картах.",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(CompatibilityStates.waiting_for_partner_coords)
    elif text == "нет":
        logger.info(f"Пользователь {message.from_user.id} отказался от точных координат партнёра")
        await message.answer(
            "Хорошо, будем использовать координаты центра города.\n\n"
            f"✨ Рассчитываю совместимость с {partner_name}, пожалуйста, подождите...",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await proceed_with_compatibility_calculation(message, state)
    else:
        await message.answer(
            "Пожалуйста, выберите 'Да' или 'Нет'.",
            reply_markup=get_yes_no_keyboard()
        )

async def process_partner_coords(message: types.Message, state: FSMContext):
    """Обрабатывает координаты места рождения партнера"""
    if await back_to_menu_handler(message, state):
        return
        
    coords = parse_coordinates(message.text.strip())
    if coords:
        partner_lat, partner_lon = coords
        await state.update_data(partner_lat=partner_lat, partner_lon=partner_lon)
        logger.info(f"Пользователь {message.from_user.id} ввёл точные координаты партнёра: lat={partner_lat}, lon={partner_lon}")
        
        data = await state.get_data()
        partner_name = data.get('partner_name')
        
        await message.answer(
            f"✅ Координаты приняты: {partner_lat:.6f}, {partner_lon:.6f}\n\n"
            f"✨ Рассчитываю совместимость с {partner_name}, пожалуйста, подождите...",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await proceed_with_compatibility_calculation(message, state)
    else:
        await message.answer(
            "❌ Неверный формат координат. Пожалуйста, отправьте их в формате 'широта, долгота' "
            "(например, 55.7558, 37.6176).",
            reply_markup=types.ReplyKeyboardRemove()
        )

async def proceed_with_compatibility_calculation(message: types.Message, state: FSMContext):
    """Выполняет расчет совместимости"""
    await state.set_state(CompatibilityStates.processing_compatibility)
    
    data = await state.get_data()
    partner_name = data.get('partner_name')
    partner_birth_date = data.get("partner_birth_date")
    partner_birth_time = data.get("partner_birth_time")
    partner_city = data.get("partner_city")
    partner_lat = data.get("partner_lat")
    partner_lon = data.get("partner_lon")
    partner_tz_name = data.get("partner_tz_name", "UTC")
    partner_relationship = data.get("partner_relationship")
    edit_mode = data.get('edit_mode', False)
    contact_id = data.get('contact_id')
    
    try:
        partner_utc_dt = get_utc_datetime(partner_birth_date, partner_birth_time, partner_tz_name)
        if not partner_utc_dt:
            await message.answer(
                "❌ Ошибка при расчёте времени партнёра в UTC. Пожалуйста, попробуйте позже.",
                reply_markup=get_main_menu()
            )
            await state.clear()
            return
            
        logger.info(f"Партнерское UTC время для пользователя {message.from_user.id}: {partner_utc_dt}")
    except Exception as e:
        logger.error(f"Ошибка расчёта UTC для партнёра у пользователя {message.from_user.id}: {e}")
        await message.answer(
            "❌ Ошибка при расчёте времени партнёра. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu()
        )
        await state.clear()
        return
    
    partner_planets = calculate_planet_positions_utc(partner_utc_dt, partner_lat, partner_lon)
    partner_houses = calculate_houses_utc(partner_utc_dt, partner_lat, partner_lon)
    
    if not (partner_planets and partner_houses):
        logger.error(f"Ошибка расчёта натальной карты партнёра у пользователя {message.from_user.id}")
        await message.answer(
            "❌ Ошибка при расчёте натальной карты партнёра. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu()
        )
        await state.clear()
        return
    
    formatted_partner_chart = format_natal_chart(partner_planets, partner_houses)
    
    # Получаем натальную карту пользователя
    user_id = str(message.from_user.id)
    user = operations.get_user(user_id)
    
    if not user or not user.get("natal_chart"):
        await message.answer(
            "Для проверки совместимости сначала нужно рассчитать вашу натальную карту.",
            reply_markup=get_main_menu()
        )
        await state.clear()
        return
    
    formatted_user_chart = user["natal_chart"]
    
    # Сохраняем или обновляем контакт в базе данных
    if edit_mode and contact_id:
        # Обновляем существующий контакт
        operations.add_contact(
            user_id,
            partner_name,
            partner_birth_date,
            partner_birth_time,
            partner_city,
            partner_lat,
            partner_lon,
            partner_tz_name,
            partner_relationship,
            formatted_partner_chart
        )
        logger.info(f"Контакт {partner_name} обновлен пользователем {message.from_user.id}")
    else:
        # Добавляем новый контакт
        contact_id = operations.add_contact(
            user_id,
            partner_name,
            partner_birth_date,
            partner_birth_time,
            partner_city,
            partner_lat,
            partner_lon,
            partner_tz_name,
            partner_relationship,
            formatted_partner_chart
        )
        logger.info(f"Новый контакт {partner_name} добавлен пользователем {message.from_user.id}")
    
    # Генерируем анализ совместимости
    analysis = await generate_compatibility_analysis(
        formatted_user_chart, 
        formatted_partner_chart, 
        partner_relationship, 
        user_id
    )
    
    # Сохраняем анализ в базу
    operations.add_compatibility_analysis(user_id, contact_id, analysis)
    
    # Проверяем, является ли пользователь премиум
    is_premium = user.get("subscription_type") != "free"
    
    # Получаем количество контактов
    contacts_count = len(operations.get_contacts(user_id))
    
    # Если это второй или более контакт, и пользователь на бесплатном тарифе,
    # отправляем заблюренное сообщение и предложение
    if contacts_count > 1 and not is_premium:
        # Показываем заблюренный результат и предложение оплаты
        preview_analysis = analysis[:150] + "..." if len(analysis) > 150 else analysis
        
        await message.answer(
            f"💞 Результат анализа совместимости с {partner_name}:\n\n"
            f"{preview_analysis}\n\n"
            "<span class='tg-spoiler'>Полный результат анализа скрыт. Для просмотра полного анализа требуется подписка.</span>",
            parse_mode="HTML",
            reply_markup=types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [types.InlineKeyboardButton(text=f"💎 Разблокировать анализ (90 ⭐️)", callback_data=f"unlock_compatibility:{contact_id}")],
                    [types.InlineKeyboardButton(text="💎 Оформить подписку", callback_data="subscribe_menu")]
                ]
            )
        )
    else:
        # Отправляем полный результат
        await message.answer(
            f"💞 Результат анализа совместимости с {partner_name}:\n\n{analysis}",
            reply_markup=get_main_menu()
        )
    
    # Возвращаемся в режим диалога
    await state.set_state(NatalChartStates.dialog_active)

# Обработчик разблокировки анализа совместимости
async def unlock_compatibility_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик разблокировки анализа совместимости"""
    _, contact_id = callback.data.split(":")
    contact_id = int(contact_id)
    
    user_id = str(callback.from_user.id)
    contact = operations.get_contact(contact_id)
    
    if not contact or contact['user_id'] != user_id:
        await callback.answer("Контакт не найден или не принадлежит вам.")
        return
    
    # Отправляем счет для разблокировки анализа совместимости
    from aiogram.types import LabeledPrice
    
    prices = [LabeledPrice(label="Разблокировка анализа", amount=90)]
    
    await callback.message.answer_invoice(
        title=f"Разбор совместимости с {contact['person_name']}",
        description=f"Оплата за просмотр полного анализа совместимости с {contact['person_name']}",
        payload=f"unlock_comp_{contact_id}_{user_id}",
        provider_token="",
        currency="XTR",
        prices=prices
    )
    
    await callback.answer()

def register_handlers(dp: Dispatcher):
    """Регистрирует обработчики для работы с совместимостью"""
    # Команда /compatibility и кнопка меню
    dp.message.register(compatibility_command, Command("compatibility"))
    dp.message.register(compatibility_command, F.text == "💞 Совместимость")
    
    # Обработчик выбора действия в меню совместимости
    dp.message.register(
        compatibility_action_handler,
        CompatibilityStates.selecting_action,
        F.text.in_(["➕ Добавить новый контакт", "📋 Мои контакты"])
    )
    
    # Обработчик выбора существующего контакта
    dp.message.register(contact_selection_handler, CompatibilityStates.selecting_contact)
    
    # Обработчик действий с контактом через inline кнопки
    dp.callback_query.register(
        contact_action_callback,
        lambda c: c.data.startswith(("compatibility:", "edit_contact:", "delete_contact:"))
    )
    
    # Обработчик действий с существующим контактом
    dp.message.register(
        process_existing_contact_action,
        CompatibilityStates.selecting_action,
        F.text.in_(["Использовать существующие", "Перезаписать", "↩️ Назад"])
    )
    
    # Ввод имени партнера
    dp.message.register(process_partner_name, CompatibilityStates.waiting_for_partner_name)
    
    # Ввод даты рождения партнера
    dp.message.register(process_partner_birth_date, CompatibilityStates.waiting_for_partner_birth_date)
    
    # Ввод времени рождения партнера
    dp.message.register(process_partner_birth_time, CompatibilityStates.waiting_for_partner_birth_time)
    
    # Ввод города рождения партнера
    dp.message.register(process_partner_birth_city, CompatibilityStates.waiting_for_partner_city)
    
    # Ввод отношения партнера
    dp.message.register(process_partner_relationship, CompatibilityStates.waiting_for_partner_relationship)
    
    # Выбор о предоставлении координат партнера
    dp.message.register(process_partner_coords_choice, CompatibilityStates.waiting_for_partner_coords_choice)
    
    # Ввод координат партнера
    dp.message.register(process_partner_coords, CompatibilityStates.waiting_for_partner_coords)
    
    # Обработчик разблокировки анализа совместимости
    dp.callback_query.register(
        unlock_compatibility_callback,
        lambda c: c.data.startswith("unlock_compatibility:")
    )