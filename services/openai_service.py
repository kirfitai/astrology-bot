import openai
import logging
from config import OPENAI_API_KEY, OPENAI_MODEL, MAX_TOKENS, COST_PER_1000_TOKENS
from database import operations

# Устанавливаем API ключ
openai.api_key = OPENAI_API_KEY

async def generate_natal_chart_interpretation(natal_chart, user_id):
    """
    Генерирует интерпретацию натальной карты с помощью OpenAI API
    """
    prompt = (
        "Ты профессиональный астролог с многолетним опытом. Проанализируй натальную карту пользователя и дай детальный разбор. "
        "Опиши основные черты личности, сильные стороны, возможные вызовы и рекомендации для развития. "
        "Если есть особые конфигурации, укажи их значение. Намекни, что это лишь часть картины.\n\n"
        "Данные натальной карты:\n"
    )
    
    try:
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Натальная карта:\n{natal_chart}"}
            ],
            max_tokens=MAX_TOKENS
        )
        
        interpretation = response.choices[0].message.content
        
        # Сохраняем статистику использования токенов
        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        cost = total_tokens / 1000 * COST_PER_1000_TOKENS
        
        operations.update_user_tokens(user_id, input_tokens, output_tokens, cost)
        operations.add_message(user_id, "out", interpretation, output_tokens, cost)
        
        logging.info(f"Интерпретация натальной карты сгенерирована. Токены: {total_tokens}, Стоимость: ${cost:.4f}")
        return interpretation
    except Exception as e:
        logging.error(f"Ошибка при генерации интерпретации натальной карты: {e}")
        return "Извините, произошла ошибка при анализе вашей натальной карты. Пожалуйста, попробуйте позже."

async def generate_compatibility_analysis(user_chart, partner_chart, relationship_type, user_id):
    """
    Генерирует анализ совместимости с помощью OpenAI API
    """
    prompt = (
        "Ты профессиональный астролог с многолетним опытом. Проведи подробный анализ совместимости между двумя людьми. "
        "Разбей анализ на следующие категории: эмоциональная, интеллектуальная, карьерная и любовная совместимость. "
        "Учитывай, что один из них — пользователь, а другой — партнёр. "
        f"Партнёр указан как: {relationship_type}.\n\n"
        "Натальная карта пользователя:\n" + user_chart + "\n\n"
        "Натальная карта партнёра:\n" + partner_chart + "\n\n"
        "Для каждого аспекта совместимости укажи как положительные, так и проблемные стороны. "
        "В конце дай общую оценку совместимости и рекомендации для улучшения отношений."
    )
    
    try:
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": prompt}],
            max_tokens=MAX_TOKENS
        )
        
        analysis = response.choices[0].message.content
        
        # Сохраняем статистику использования токенов
        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        cost = total_tokens / 1000 * COST_PER_1000_TOKENS
        
        operations.update_user_tokens(user_id, input_tokens, output_tokens, cost)
        operations.add_message(user_id, "out", analysis, output_tokens, cost)
        
        logging.info(f"Анализ совместимости сгенерирован. Токены: {total_tokens}, Стоимость: ${cost:.4f}")
        return analysis
    except Exception as e:
        logging.error(f"Ошибка при генерации анализа совместимости: {e}")
        return "Извините, произошла ошибка при анализе совместимости. Пожалуйста, попробуйте позже."

async def generate_daily_horoscope(natal_chart, current_planets, user_id, is_premium=False):
    """
    Генерирует ежедневный гороскоп с помощью OpenAI API
    """
    prompt = (
        "Ты профессиональный астролог. На основе текущего положения планет и натальной карты пользователя, "
        "составь персонализированный гороскоп на сегодня."
    )
    
    if is_premium:
        prompt += (
            " Это премиум гороскоп, поэтому сделай его более подробным и детальным. "
            "Включи следующие секции: общий настрой дня, работа и карьера, любовь и отношения, "
            "здоровье и самочувствие, финансы, а также рекомендации и советы на день. "
            "Укажи особые аспекты планет, которые могут влиять на пользователя сегодня, "
            "и как их энергию лучше использовать."
        )
    else:
        prompt += (
            " Это базовый гороскоп, поэтому сделай его кратким и информативным. "
            "Включи общий настрой дня, основную сферу внимания (работа, отношения или саморазвитие) "
            "и один главный совет на день."
        )
    
    prompt += (
        f"\n\nНатальная карта пользователя:\n{natal_chart}\n\n"
        f"Положение планет сегодня:\n{current_planets}\n"
    )
    
    try:
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": prompt}],
            max_tokens=MAX_TOKENS if is_premium else MAX_TOKENS // 2  # Для базового гороскопа используем меньше токенов
        )
        
        horoscope = response.choices[0].message.content
        
        # Сохраняем статистику использования токенов
        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        cost = total_tokens / 1000 * COST_PER_1000_TOKENS
        
        operations.update_user_tokens(user_id, input_tokens, output_tokens, cost)
        
        logging.info(f"Ежедневный гороскоп сгенерирован. Токены: {total_tokens}, Стоимость: ${cost:.4f}")
        return horoscope
    except Exception as e:
        logging.error(f"Ошибка при генерации ежедневного гороскопа: {e}")
        return "Извините, произошла ошибка при генерации гороскопа. Пожалуйста, попробуйте позже."

async def generate_monthly_horoscope(natal_chart, forecast_planets, user_id, is_premium=False):
    """
    Генерирует месячный гороскоп с помощью OpenAI API
    """
    prompt = (
        "Ты профессиональный астролог. На основе положения планет и натальной карты пользователя, "
        "составь персонализированный гороскоп на месяц."
    )
    
    if is_premium:
        prompt += (
            " Это премиум гороскоп, поэтому сделай его более подробным и детальным. "
            "Раздели гороскоп на недели, указав особенности каждой из них. "
            "Включи следующие секции для каждой недели: общий настрой, работа и карьера, "
            "любовь и отношения, здоровье, финансы. "
            "В конце добавь общие рекомендации на месяц и укажи благоприятные дни для важных начинаний."
        )
    else:
        prompt += (
            " Это базовый гороскоп, поэтому сделай его кратким и информативным. "
            "Включи общие тенденции месяца, ключевые даты и главные сферы внимания."
        )
    
    prompt += (
        f"\n\nНатальная карта пользователя:\n{natal_chart}\n\n"
        f"Положение планет на 1 число месяца:\n{forecast_planets}\n"
    )
    
    try:
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": prompt}],
            max_tokens=MAX_TOKENS if is_premium else MAX_TOKENS // 2
        )
        
        horoscope = response.choices[0].message.content
        
        # Сохраняем статистику использования токенов
        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        cost = total_tokens / 1000 * COST_PER_1000_TOKENS
        
        operations.update_user_tokens(user_id, input_tokens, output_tokens, cost)
        
        logging.info(f"Месячный гороскоп сгенерирован. Токены: {total_tokens}, Стоимость: ${cost:.4f}")
        return horoscope
    except Exception as e:
        logging.error(f"Ошибка при генерации месячного гороскопа: {e}")
        return "Извините, произошла ошибка при генерации гороскопа. Пожалуйста, попробуйте позже."

async def process_user_dialog(user_id, user_message, natal_chart, contacts, message_history):
    """
    Обрабатывает диалог пользователя с учетом контекста
    """
    # Ищем упоминания контактов в сообщении
    additional_info = ""
    mentioned_contacts = []
    
    for contact in contacts:
        person_name = contact.get("person_name", "").lower()
        relationship = contact.get("relationship", "").lower()
        
        if (person_name and person_name in user_message.lower()) or (relationship and relationship in user_message.lower()):
            additional_info += f"\nДанные контакта {contact['person_name']}:\n{contact['natal_chart']}\n"
            mentioned_contacts.append(contact['person_name'])
    
    # Формируем системное сообщение с контекстом
    system_msg = (
        "Ты профессиональный астролог с многолетним опытом. "
        "Отвечаешь на вопросы пользователя, используя астрологические знания. "
        "Твои ответы должны быть информативными, но при этом оставлять пространство для дополнительных вопросов.\n\n"
        f"Вот данные натальной карты пользователя:\n{natal_chart}\n"
    )
    
    if additional_info:
        system_msg += f"\n{additional_info}\n"
        system_msg += "\nВ своем ответе учитывай данные этих дополнительных натальных карт, если вопрос касается взаимоотношений."
    
    # Создаем сообщения для отправки в API
    messages = [{"role": "system", "content": system_msg}]
    
    # Добавляем историю сообщений
    for msg in message_history:
        messages.append(msg)
    
    # Добавляем текущее сообщение пользователя
    messages.append({"role": "user", "content": user_message})
    
    try:
        # Сохраняем входящее сообщение в базу
        operations.add_message(user_id, "in", user_message)
        
        # Отправляем запрос к API
        response = openai.ChatCompletion.create(
            model=OPENAI_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS
        )
        
        reply = response.choices[0].message.content
        
        # Сохраняем статистику использования токенов
        usage = response.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", 0)
        cost = total_tokens / 1000 * COST_PER_1000_TOKENS
        
        operations.update_user_tokens(user_id, input_tokens, output_tokens, cost)
        operations.add_message(user_id, "out", reply, output_tokens, cost)
        
        # Уменьшаем счетчик бесплатных сообщений, если пользователь на бесплатном плане
        operations.decrement_free_messages(user_id)
        
        logging.info(f"Ответ сгенерирован. Токены: {total_tokens}, Стоимость: ${cost:.4f}")
        
        return {
            "reply": reply,
            "mentioned_contacts": mentioned_contacts,
            "tokens": total_tokens,
            "cost": cost
        }
    except Exception as e:
        logging.error(f"Ошибка при обработке диалога: {e}")
        return {
            "reply": "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.",
            "mentioned_contacts": [],
            "tokens": 0,
            "cost": 0
        }