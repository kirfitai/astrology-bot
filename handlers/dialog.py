from aiogram import Dispatcher, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from collections import deque
import logging

from states.user_states import NatalChartStates
from utils.keyboards import get_main_menu
from services.openai_service import process_user_dialog
from database import operations
from config import MAX_MESSAGES

logger = logging.getLogger(__name__)

async def user_dialog_handler(message: types.Message, state: FSMContext):
    """Обработчик диалога пользователя с ботом в контексте натальной карты"""
    user_id = str(message.from_user.id)
    user = operations.get_user(user_id)
    
    # Проверяем, может ли пользователь отправлять сообщения
    can_message = operations.check_user_can_message(user_id)
    if not can_message:
        # Пользователь исчерпал бесплатный лимит
        subscription_type = user.get("subscription_type", "free")
        
        if subscription_type == "free":
            # Отправляем заблюренное сообщение и предложение приобрести подписку
            await message.answer(
                "⚠️ Вы исчерпали лимит бесплатных сообщений (3 сообщения).\n\n"
                "<span class='tg-spoiler'>Для продолжения общения с ботом приобретите подписку.</span>",
                parse_mode="HTML",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="💎 Разблокировать ответ (90 ⭐️)", callback_data="unlock_message")],
                        [types.InlineKeyboardButton(text="💎 Узнать о подписке", callback_data="premium_info")]
                    ]
                )
            )
            return
        else:
            # Подписка истекла
            await message.answer(
                "⚠️ Ваша подписка истекла.\n\n"
                "Для продолжения общения с ботом продлите подписку.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="subscribe_menu")]
                    ]
                )
            )
            return
    
    # Получаем данные пользователя
    if not user or not user.get("natal_chart"):
        await message.answer(
            "Для общения сначала нужно рассчитать вашу натальную карту.\n\n"
            "Пожалуйста, используйте команду /natal или нажмите на кнопку 'Моя натальная карта'.",
            reply_markup=get_main_menu()
        )
        return
    
    # Получаем сохраненную историю сообщений
    history = await get_or_create_message_history(state)
    
    # Получаем контакты пользователя
    contacts = operations.get_contacts(user_id)
    
    # Получаем натальную карту пользователя
    natal_chart = user.get("natal_chart", "")
    
    # Отправляем индикатор набора текста
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # Обрабатываем сообщение пользователя
    result = await process_user_dialog(
        user_id,
        message.text,
        natal_chart,
        contacts,
        history
    )
    
    # Обновляем историю сообщений
    history.append({"role": "user", "content": message.text})
    history.append({"role": "assistant", "content": result["reply"]})
    await state.update_data(message_history=list(history))
    
    # Формируем ответное сообщение
    reply_text = result["reply"]
    
    # Добавляем информацию об упомянутых контактах, если они есть
    if result["mentioned_contacts"]:
        contacts_info = ", ".join(result["mentioned_contacts"])
        mention_note = f"\n\n_Учтены данные: {contacts_info}_"
        reply_text += mention_note
    
    # Отправляем ответ пользователю
    await message.answer(reply_text, reply_markup=get_main_menu())
    
    # Если у пользователя бесплатный план, показываем оставшийся лимит
    if user.get("subscription_type") == "free":
        free_left = user.get("free_messages_left", 0)
        if free_left <= 3:  # Показываем предупреждение, если осталось мало сообщений
            await message.answer(
                f"⚠️ У вас осталось {free_left} бесплатных сообщений из 3.\n"
                "После исчерпания лимита ответы будут скрыты и доступны только по подписке.",
                reply_markup=types.InlineKeyboardMarkup(
                    inline_keyboard=[
                        [types.InlineKeyboardButton(text="💎 Узнать о подписке", callback_data="premium_info")]
                    ]
                )
            )

async def get_or_create_message_history(state: FSMContext):
    """Получает или создает историю сообщений из состояния"""
    data = await state.get_data()
    
    if "message_history" in data:
        # Преобразуем список обратно в deque
        history_list = data["message_history"]
        history = deque(history_list, maxlen=MAX_MESSAGES)
    else:
        # Создаем новую историю
        history = deque(maxlen=MAX_MESSAGES)
    
    return history

# Обработчик разблокировки сообщения
async def unlock_message_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = str(callback.from_user.id)
    
    # Отправляем счет для разблокировки одного сообщения
    from aiogram.types import LabeledPrice
    
    prices = [LabeledPrice(label="Разблокировка ответа", amount=90)]
    
    await callback.message.answer_invoice(
        title="Разблокировка ответа",
        description="Одноразовая оплата для разблокировки ответа бота",
        payload=f"unlock_msg_{user_id}_{int(datetime.now().timestamp())}",
        provider_token="",
        currency="XTR",
        prices=prices
    )
    
    await callback.answer()

def register_handlers(dp: Dispatcher):
    """Регистрирует обработчики для диалога"""
    # Обработчик сообщений в режиме диалога
    dp.message.register(user_dialog_handler, StateFilter(NatalChartStates.dialog_active))
    
    # Обработчик разблокировки сообщения
    dp.callback_query.register(
        unlock_message_callback,
        lambda c: c.data == "unlock_message"
    )