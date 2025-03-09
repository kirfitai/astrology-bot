import asyncio
import random
from aiogram import types

async def typing_action(message: types.Message, min_duration=1, max_duration=2):
    """
    Отправляет индикатор "печатает..." на указанное время
    
    Args:
        message: Сообщение, от которого будет отправлен индикатор
        min_duration: Минимальная продолжительность в секундах
        max_duration: Максимальная продолжительность в секундах
    """
    duration = random.uniform(min_duration, max_duration)
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    await asyncio.sleep(duration)

def add_astro_emoji(text, category=None):
    """
    Добавляет тематические эмодзи к тексту сообщения
    
    Args:
        text: Исходный текст
        category: Категория сообщения (natal, compatibility, horoscope, etc.)
        
    Returns:
        str: Текст с добавленными эмодзи
    """
    # Базовые эмодзи для всех категорий
    general_emojis = ["✨", "🌟", "🔮", "🌙", "💫", "⭐️", "🌠", "🌌"]
    
    # Эмодзи для конкретных категорий
    category_emojis = {
        "natal": ["🔮", "🌠", "🧿", "🪐", "🌒", "📜"],
        "compatibility": ["💞", "❤️", "💑", "👩‍❤️‍👨", "🌹", "🤝"],
        "horoscope": ["🗓️", "🌅", "🌄", "📆", "⏰", "🧘‍♀️"],
        "planets": ["☀️", "🌙", "🪐", "⭐️", "🌎", "🌚"],
        "welcome": ["👋", "🎉", "✨", "🙏", "🌈"],
        "subscription": ["💎", "💰", "🏆", "✅", "🔑", "💯"]
    }
    
    # Выбираем эмодзи
    emojis = category_emojis.get(category, general_emojis) if category else general_emojis
    chosen_emoji = random.choice(emojis)
    
    # Добавляем эмодзи в начало текста, если оно уже не начинается с эмодзи
    if not any(text.startswith(e) for e in general_emojis + sum(category_emojis.values(), [])):
        text = f"{chosen_emoji} {text}"
        
    return text