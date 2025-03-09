from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
import pytz
from datetime import datetime
import logging
import re

# Инициализация геолокатора и инструмента для определения временной зоны
geolocator = Nominatim(user_agent="astrology_bot")
tfinder = TimezoneFinder()

def parse_coordinates(coords_str):
    """
    Парсит строку с координатами в формате 'широта, долгота'
    Возвращает кортеж (широта, долгота) или None в случае ошибки
    """
    try:
        # Очищаем строку от лишних символов и заменяем запятую на пробел
        cleaned_str = re.sub(r'[^\d.,\s\-+]', '', coords_str)
        
        # Разделяем строку по запятой или пробелу
        parts = re.split(r'[,\s]+', cleaned_str)
        
        # Фильтруем пустые части
        parts = [p for p in parts if p]
        
        if len(parts) >= 2:
            lat = float(parts[0])
            lon = float(parts[1])
            
            # Проверяем диапазон координат
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
            else:
                logging.error(f"Координаты вне диапазона: {lat}, {lon}")
                return None
        else:
            logging.error(f"Недостаточно частей в строке координат: {coords_str}")
            return None
    except Exception as e:
        logging.error(f"Ошибка парсинга координат '{coords_str}': {e}")
        return None

def get_location_info(city, birth_dt=None):
    """
    Получает информацию о местоположении по названию города
    Возвращает словарь с координатами и временной зоной
    """
    try:
        location = geolocator.geocode(city)
        if not location:
            logging.error(f"Не удалось получить координаты для города: {city}")
            return None
        
        lat = location.latitude
        lon = location.longitude
        tz_name = tfinder.timezone_at(lng=lon, lat=lat)
        
        if not tz_name:
            tz_name = "UTC"
            logging.warning(f"Не удалось определить временную зону для {city}, используем UTC")
        
        result = {
            "lat": lat,
            "lon": lon,
            "tz_name": tz_name,
            "address": location.address
        }
        
        # Если предоставлена дата/время рождения, получаем информацию о смещении времени
        if birth_dt:
            tz = pytz.timezone(tz_name)
            localized_dt = tz.localize(birth_dt, is_dst=None)
            offset = int(localized_dt.utcoffset().total_seconds())
            is_dst = bool(localized_dt.dst())
            
            result["gmt_offset"] = offset
            result["is_dst"] = is_dst
        
        logging.info(f"Получены координаты для {city}: lat={lat}, lon={lon}, tz={tz_name}")
        return result
    except Exception as e:
        logging.error(f"Ошибка в get_location_info для {city}: {e}")
        return None

def get_utc_datetime(date_str, time_str, tz_name):
    """
    Преобразует локальное время в UTC
    Возвращает объект datetime в UTC
    """
    try:
        local_dt = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        tz = pytz.timezone(tz_name)
        localized_dt = tz.localize(local_dt, is_dst=None)
        utc_dt = localized_dt.astimezone(pytz.utc)
        logging.info(f"Время {local_dt} ({tz_name}) преобразовано в UTC: {utc_dt}")
        return utc_dt
    except Exception as e:
        logging.error(f"Ошибка в get_utc_datetime: {e}")
        return None

def format_location_info(location_info):
    """
    Форматирует информацию о местоположении для вывода пользователю
    """
    if not location_info:
        return "Информация о местоположении недоступна"
    
    parts = [
        f"📍 {location_info.get('address', 'Адрес не определен')}",
        f"🌐 Координаты: {location_info.get('lat', 0):.4f}, {location_info.get('lon', 0):.4f}",
        f"🕒 Временная зона: {location_info.get('tz_name', 'UTC')}"
    ]
    
    if "gmt_offset" in location_info:
        hours = location_info["gmt_offset"] // 3600
        sign = "+" if hours >= 0 else "-"
        parts.append(f"⏱ Смещение от GMT: {sign}{abs(hours):02d}:00")
    
    return "\n".join(parts)