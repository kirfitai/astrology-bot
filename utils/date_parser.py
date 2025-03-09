from datetime import datetime
import re
import dateparser
import logging

def parse_date_input(date_str):
    """
    Парсит строку с датой в различных форматах
    Возвращает строку в формате DD.MM.YYYY или None в случае ошибки
    """
    try:
        # Сначала пытаемся использовать dateparser для обработки различных форматов
        dt = dateparser.parse(
            date_str, 
            settings={
                'DATE_ORDER': 'DMY',
                'STRICT_PARSING': False,
                'PREFER_DAY_OF_MONTH': 'current',
                'PREFER_DATES_FROM': 'past'
            }
        )
        
        if dt:
            result = dt.strftime("%d.%m.%Y")
            logging.info(f"Дата '{date_str}' успешно распознана как '{result}'")
            return result
        
        # Если dateparser не справился, пробуем распознать вручную
        date_str = date_str.strip()
        
        # Проверяем форматы DD.MM.YYYY, DD/MM/YYYY, DD-MM-YYYY
        patterns = [
            r'(\d{1,2})[.\s](\d{1,2})[.\s](\d{2,4})',  # DD.MM.YYYY or DD MM YYYY
            r'(\d{1,2})[/](\d{1,2})[/](\d{2,4})',      # DD/MM/YYYY
            r'(\d{1,2})[-](\d{1,2})[-](\d{2,4})'       # DD-MM-YYYY
        ]
        
        for pattern in patterns:
            match = re.search(pattern, date_str)
            if match:
                day, month, year = match.groups()
                
                # Преобразуем в числа
                day = int(day)
                month = int(month)
                year = int(year)
                
                # Коррекция года, если введен в коротком формате
                if year < 100:
                    if year > 30:  # Предполагаем, что 30 и меньше - это 2000+ годы
                        year += 1900
                    else:
                        year += 2000
                
                # Проверяем валидность даты
                if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
                    # Формируем дату в нужном формате
                    result = f"{day:02d}.{month:02d}.{year}"
                    logging.info(f"Дата '{date_str}' успешно распознана как '{result}'")
                    return result
        
        logging.error(f"Не удалось распознать дату: {date_str}")
        return None
    except Exception as e:
        logging.error(f"Ошибка при парсинге даты '{date_str}': {e}")
        return None

def parse_time_input(time_str):
    """
    Парсит строку с временем в различных форматах
    Возвращает строку в формате HH:MM или None в случае ошибки
    """
    try:
        # Нормализация строки
        time_str = time_str.strip().lower()
        
        # Обработка текстовых вариантов времени суток
        time_periods = {
            "утром": "09:00",
            "утро": "09:00",
            "утра": "09:00",
            "днем": "15:00",
            "день": "15:00",
            "дня": "15:00",
            "вечером": "21:00",
            "вечер": "21:00",
            "вечера": "21:00",
            "ночью": "03:00",
            "ночь": "03:00",
            "ночи": "03:00"
        }
        
        # Проверяем на ключевые слова времени суток
        for period, default_time in time_periods.items():
            if period in time_str:
                logging.info(f"Время '{time_str}' интерпретировано как '{default_time}' ({period})")
                return default_time
        
        # Извлечение паттернов для времени в форматах HH:MM, HH.MM, HH-MM, HH MM
        patterns = [
            r'(\d{1,2}):(\d{1,2})',  # HH:MM
            r'(\d{1,2})\.(\d{1,2})',  # HH.MM
            r'(\d{1,2})-(\d{1,2})',  # HH-MM
            r'(\d{1,2})\s+(\d{1,2})'  # HH MM
        ]
        
        for pattern in patterns:
            match = re.search(pattern, time_str)
            if match:
                hours, minutes = match.groups()
                
                # Преобразуем в числа
                hours = int(hours)
                minutes = int(minutes)
                
                # Проверяем валидность времени
                if 0 <= hours <= 23 and 0 <= minutes <= 59:
                    # Формируем время в нужном формате
                    result = f"{hours:02d}:{minutes:02d}"
                    logging.info(f"Время '{time_str}' успешно распознано как '{result}'")
                    return result
        
        # Возвращаем время по умолчанию, если не удалось распознать
        logging.info(f"Время '{time_str}' не распознано, используем значение по умолчанию '12:00'")
        return "12:00"
    except Exception as e:
        logging.error(f"Ошибка при парсинге времени '{time_str}': {e}")
        return "12:00"  # Возвращаем время по умолчанию в случае ошибки