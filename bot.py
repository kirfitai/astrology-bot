import asyncio
import logging
from datetime import datetime
from collections import deque

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, LabeledPrice, PreCheckoutQuery

from config import TELEGRAM_TOKEN, LOG_LEVEL
from database.models import init_db
from services.scheduler import setup_scheduler

# Настраиваем логирование
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)

# Создаем экземпляр бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрируем команды бота
async def set_commands():
    commands = [
        BotCommand(command="/start", description="Начать взаимодействие с ботом"),
        BotCommand(command="/menu", description="Показать меню"),
        BotCommand(command="/help", description="Получить помощь"),
        BotCommand(command="/natal", description="Рассчитать натальную карту"),
        BotCommand(command="/compatibility", description="Проверить совместимость"),
        BotCommand(command="/horoscope", description="Настроить ежедневный гороскоп"),
        BotCommand(command="/subscription", description="Управление подпиской"),
        BotCommand(command="/reset", description="Сбросить текущее состояние")
    ]
    await bot.set_my_commands(commands)

# Импортируем и регистрируем все обработчики
async def register_handlers():
    # Импортируем модули с обработчиками
    from handlers import (
        start,
        natal_chart,
        compatibility,
        horoscope,
        dialog,
        subscription,
        admin
    )
    
    # Регистрируем обработчики в диспетчере
    # Порядок регистрации важен - более специфичные обработчики должны быть зарегистрированы раньше
    start.register_handlers(dp)
    natal_chart.register_handlers(dp)
    compatibility.register_handlers(dp)
    horoscope.register_handlers(dp)
    subscription.register_handlers(dp)
    admin.register_handlers(dp)
    
    # Обработчик диалогов должен быть зарегистрирован последним,
    # так как он будет обрабатывать все сообщения, не обработанные другими обработчиками
    dialog.register_handlers(dp)
    
    logger.info("Все обработчики зарегистрированы")

# Регистрируем middleware
async def register_middleware():
    from middleware.subscription import SubscriptionMiddleware
    
    # Регистрируем middleware
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())
    
    logger.info("Middleware зарегистрирован")

# Функция запуска бота
async def main():
    logger.info("Запуск астрологического бота...")
    
    # Инициализируем базу данных
    if not init_db():
        logger.error("Не удалось инициализировать базу данных. Выход.")
        return
    
    # Настраиваем планировщик для гороскопов
    scheduler = setup_scheduler(bot)
    
    # Устанавливаем команды бота
    await set_commands()
    
    # Регистрируем middleware
    await register_middleware()
    
    # Регистрируем обработчики
    await register_handlers()
    
    try:
        # Запускаем планировщик
        scheduler.start()
        
        # Запускаем бота
        logger.info("Бот запущен")
        await bot.delete_webhook(drop_pending_updates=True)
        
        # Логируем статус подсистемы платежей
        logger.info("Подсистема платежей через Telegram Stars настроена")
        
        await dp.start_polling(bot)
    finally:
        # Останавливаем планировщик
        scheduler.shutdown()
        
        # Закрываем соединение бота
        await bot.session.close()
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())