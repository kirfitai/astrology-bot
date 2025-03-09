from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from aiogram import Bot
from database import operations
from services.ephemeris import calculate_planet_positions_utc, calculate_houses_utc, format_natal_chart
from services.openai_service import generate_daily_horoscope, generate_monthly_horoscope

logger = logging.getLogger(__name__)

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Настраивает и возвращает планировщик для отправки гороскопов"""
    scheduler = AsyncIOScheduler()
    
    # Добавляем задачи для отправки гороскопов в каждый час
    for hour in range(24):
        for minute in [0, 30]:  # Проверяем каждые 30 минут
            time_str = f"{hour:02d}:{minute:02d}"
            scheduler.add_job(
                send_daily_horoscopes,
                CronTrigger(hour=hour, minute=minute),
                kwargs={"bot": bot, "time_str": time_str}
            )
    
    # Добавляем задачу для отправки месячных гороскопов (последний день месяца в 12:00)
    scheduler.add_job(
        send_monthly_horoscopes,
        CronTrigger(day="last", hour=12, minute=0),
        kwargs={"bot": bot}
    )
    
    # Планируем ежедневную проверку истекших подписок (в 00:30)
    scheduler.add_job(
        check_expired_subscriptions,
        CronTrigger(hour=0, minute=30),
        kwargs={"bot": bot}
    )
    
    logger.info("Планировщик гороскопов и проверки подписок настроен")
    return scheduler

async def send_daily_horoscopes(bot: Bot, time_str: str):
    """Отправляет ежедневные гороскопы пользователям, у которых настроена доставка на указанное время"""
    try:
        logger.info(f"Начинаем отправку ежедневных гороскопов на время {time_str}")
        
        # Получаем пользователей, которые должны получить гороскоп в это время
        users = operations.get_users_with_horoscope_at_time(time_str)
        if not users:
            logger.info(f"Нет пользователей для отправки гороскопа на время {time_str}")
            return
        
        logger.info(f"Найдено {len(users)} пользователей для отправки гороскопа на время {time_str}")
        
        # Текущая дата для заголовка гороскопа
        today = datetime.now().strftime("%d.%m.%Y")
        
        # Отправляем гороскоп каждому пользователю
        for user in users:
            user_id = user["user_id"]
            
            try:
                # Проверяем наличие натальной карты и координат
                natal_chart = user.get("natal_chart")
                if not natal_chart:
                    logger.warning(f"У пользователя {user_id} нет натальной карты")
                    continue
                
                lat = user.get("horoscope_latitude")
                lon = user.get("horoscope_longitude")
                if not lat or not lon:
                    logger.warning(f"У пользователя {user_id} не указаны координаты для гороскопа")
                    continue
                
                # Рассчитываем текущее положение планет
                now = datetime.now()
                planets = calculate_planet_positions_utc(now, lat, lon)
                houses = calculate_houses_utc(now, lat, lon)
                
                if not planets or not houses:
                    logger.error(f"Ошибка расчёта положения планет для пользователя {user_id}")
                    continue
                
                formatted_planets = format_natal_chart(planets, houses)
                
                # Определяем, является ли пользователь премиум-подписчиком
                is_premium = user.get("subscription_type") != "free"
                
                # Генерируем гороскоп
                horoscope_text = await generate_daily_horoscope(
                    natal_chart,
                    formatted_planets,
                    user_id,
                    is_premium
                )
                
                # Сохраняем гороскоп в базу
                operations.add_horoscope(user_id, horoscope_text)
                
                # Отправляем гороскоп
                await bot.send_message(
                    user_id,
                    f"🌟 Ваш персональный гороскоп на {today}:\n\n{horoscope_text}"
                )
                
                logger.info(f"Отправлен ежедневный гороскоп пользователю {user_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке гороскопа пользователю {user_id}: {e}")
        
        logger.info(f"Завершена отправка ежедневных гороскопов на время {time_str}")
    except Exception as e:
        logger.error(f"Ошибка в функции send_daily_horoscopes: {e}")

async def send_monthly_horoscopes(bot: Bot):
    """Отправляет месячные гороскопы всем пользователям с подпиской"""
    try:
        logger.info("Начинаем отправку месячных гороскопов")
        
        # Получаем всех пользователей с активной подпиской
        users = operations.get_all_users()
        if not users:
            logger.info("Нет пользователей для отправки месячного гороскопа")
            return
        
        # Следующий месяц для заголовка гороскопа
        now = datetime.now()
        next_month = now.month + 1 if now.month < 12 else 1
        next_month_year = now.year if now.month < 12 else now.year + 1
        next_month_name = {
            1: "январь", 2: "февраль", 3: "март", 4: "апрель",
            5: "май", 6: "июнь", 7: "июль", 8: "август",
            9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь"
        }[next_month]
        
        # Отправляем гороскоп пользователям с подпиской
        for user in users:
            user_id = user["user_id"]
            
            # Отправляем месячный гороскоп только пользователям с подпиской
            if user.get("subscription_type") == "free":
                continue
            
            try:
                # Проверяем наличие натальной карты и координат
                natal_chart = user.get("natal_chart")
                if not natal_chart:
                    logger.warning(f"У пользователя {user_id} нет натальной карты")
                    continue
                
                lat = user.get("horoscope_latitude") or user.get("latitude")
                lon = user.get("horoscope_longitude") or user.get("longitude")
                if not lat or not lon:
                    logger.warning(f"У пользователя {user_id} не указаны координаты для гороскопа")
                    continue
                
                # Рассчитываем положение планет на 1-е число следующего месяца
                forecast_date = datetime(next_month_year, next_month, 1, 12, 0)
                planets = calculate_planet_positions_utc(forecast_date, lat, lon)
                houses = calculate_houses_utc(forecast_date, lat, lon)
                
                if not planets or not houses:
                    logger.error(f"Ошибка расчёта положения планет для пользователя {user_id}")
                    continue
                
                formatted_planets = format_natal_chart(planets, houses)
                
                # Генерируем месячный гороскоп
                horoscope_text = await generate_monthly_horoscope(
                    natal_chart,
                    formatted_planets,
                    user_id,
                    is_premium=True
                )
                
                # Сохраняем гороскоп в базу
                operations.add_horoscope(user_id, horoscope_text, "monthly")
                
                # Отправляем гороскоп
                await bot.send_message(
                    user_id,
                    f"🌙 Ваш персональный гороскоп на {next_month_name} {next_month_year}:\n\n{horoscope_text}"
                )
                
                logger.info(f"Отправлен месячный гороскоп пользователю {user_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке месячного гороскопа пользователю {user_id}: {e}")
        
        logger.info("Завершена отправка месячных гороскопов")
    except Exception as e:
        logger.error(f"Ошибка в функции send_monthly_horoscopes: {e}")

async def check_expired_subscriptions(bot: Bot):
    """Проверяет истекшие подписки и отправляет уведомления пользователям"""
    try:
        logger.info("Начинаем проверку истекших подписок")
        
        # Получаем всех пользователей
        users = operations.get_all_users()
        if not users:
            logger.info("Нет пользователей для проверки подписок")
            return
        
        now = datetime.now()
        
        # Проверяем подписки, которые истекают скоро или уже истекли
        for user in users:
            user_id = user["user_id"]
            
            # Пропускаем пользователей с бесплатным планом
            if user.get("subscription_type") == "free":
                continue
            
            # Проверяем дату окончания подписки
            if user.get("subscription_end_date"):
                end_date = datetime.fromisoformat(user.get("subscription_end_date"))
                days_left = (end_date - now).days
                
                # Если подписка истекает в течение 3 дней или уже истекла
                if 0 <= days_left <= 3:
                    # Отправляем уведомление о скором истечении подписки
                    await bot.send_message(
                        user_id,
                        f"⚠️ Ваша Premium подписка истекает через {days_left} дней.\n\n"
                        "Не забудьте продлить её, чтобы продолжить пользоваться всеми преимуществами!",
                        reply_markup=bot.types.InlineKeyboardMarkup(
                            inline_keyboard=[
                                [bot.types.InlineKeyboardButton(
                                    text="🔄 Продлить подписку", 
                                    callback_data="subscribe_menu"
                                )]
                            ]
                        )
                    )
                    logger.info(f"Отправлено уведомление о скором истечении подписки пользователю {user_id}")
                elif days_left < 0:
                    # Подписка истекла, обновляем статус
                    operations.update_user_subscription(user_id, "free")
                    
                    # Отправляем уведомление об истечении подписки
                    await bot.send_message(
                        user_id,
                        "⚠️ Ваша Premium подписка истекла.\n\n"
                        "Вы переведены на бесплатный план. Для продолжения использования всех функций "
                        "бота, пожалуйста, обновите подписку.",
                        reply_markup=bot.types.InlineKeyboardMarkup(
                            inline_keyboard=[
                                [bot.types.InlineKeyboardButton(
                                    text="💎 Обновить Premium", 
                                    callback_data="subscribe_menu"
                                )]
                            ]
                        )
                    )
                    logger.info(f"Отправлено уведомление об истечении подписки пользователю {user_id}")
        
        logger.info("Завершена проверка истекших подписок")
    except Exception as e:
        logger.error(f"Ошибка в функции check_expired_subscriptions: {e}")