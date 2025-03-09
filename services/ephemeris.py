import swisseph as swe
from datetime import datetime
from tabulate import tabulate
import logging
from config import EPHE_PATH

# Инициализация пути к ephemeris
swe.set_ephe_path(EPHE_PATH)

# Словари для перевода планет и домов
planet_names_ru = {
    "Sun": "Солнце",
    "Moon": "Луна",
    "Mercury": "Меркурий",
    "Venus": "Венера",
    "Mars": "Марс",
    "Jupiter": "Юпитер",
    "Saturn": "Сатурн",
    "Uranus": "Уран",
    "Neptune": "Нептун",
    "Pluto": "Плутон",
    "Lilith": "Лилит",
    "North Node": "Северный Узел",
    "South Node": "Южный Узел",
    "Ascendant": "Асцендент",
    "MC": "MC (Середина Неба)"
}

house_names_ru = {
    "House 1": "1-й дом",
    "House 2": "2-й дом",
    "House 3": "3-й дом",
    "House 4": "4-й дом",
    "House 5": "5-й дом",
    "House 6": "6-й дом",
    "House 7": "7-й дом",
    "House 8": "8-й дом",
    "House 9": "9-й дом",
    "House 10": "10-й дом",
    "House 11": "11-й дом",
    "House 12": "12-й дом"
}

def translate_to_russian(name):
    """Переводит названия планет и домов на русский язык"""
    return planet_names_ru.get(name, house_names_ru.get(name, name))

def get_zodiac_sign(longitude):
    """Определяет знак зодиака по долготе"""
    signs = [
        (0, "Овен"), (30, "Телец"), (60, "Близнецы"), (90, "Рак"),
        (120, "Лев"), (150, "Дева"), (180, "Весы"), (210, "Скорпион"),
        (240, "Стрелец"), (270, "Козерог"), (300, "Водолей"), (330, "Рыбы")
    ]
    for i, (degree, sign) in enumerate(signs):
        if longitude < degree:
            return signs[i - 1][1] if i > 0 else signs[-1][1]
    return signs[-1][1]

def get_house(longitude, houses):
    """Определяет дом по долготе"""
    for i in range(1, 13):
        start = houses.get(f"House {i}")
        next_house = i % 12 + 1
        end = houses.get(f"House {next_house}", 360)
        
        # Обработка перехода через 0°
        if start > end:
            if longitude >= start or longitude < end:
                return i
        else:
            if start <= longitude < end:
                return i
    
    return 1  # По умолчанию возвращаем 1-й дом, если не определено

def calculate_planet_positions_utc(utc_dt, lat, lon):
    """Вычисляет положения планет в UTC"""
    try:
        jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute / 60.0)
        planets = {
            "Sun": swe.SUN,
            "Moon": swe.MOON,
            "Mercury": swe.MERCURY,
            "Venus": swe.VENUS,
            "Mars": swe.MARS,
            "Jupiter": swe.JUPITER,
            "Saturn": swe.SATURN,
            "Uranus": swe.URANUS,
            "Neptune": swe.NEPTUNE,
            "Pluto": swe.PLUTO,
            "Lilith": swe.MEAN_APOG,
            "North Node": swe.MEAN_NODE
        }
        res = {}
        for name, pid in planets.items():
            pos, _ = swe.calc_ut(jd, pid)
            res[name] = {"longitude": pos[0], "latitude": pos[1], "house": None}
        
        # Добавляем Южный Узел (противоположный Северному)
        res["South Node"] = {"longitude": (res["North Node"]["longitude"] + 180) % 360,
                             "latitude": -res["North Node"]["latitude"],
                             "house": None}
        
        logging.info("Расчёт планет выполнен успешно")
        return res
    except Exception as e:
        logging.error(f"Ошибка расчёта планет: {e}")
        return None

def calculate_houses_utc(utc_dt, lat, lon):
    """Вычисляет положения домов в UTC"""
    try:
        jd = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour + utc_dt.minute / 60.0)
        houses, asc_mc = swe.houses(jd, lat, lon, b'P')
        asc = asc_mc[0]
        mc = asc_mc[1]
        houses_dict = {f"House {i+1}": house for i, house in enumerate(houses)}
        houses_dict["Ascendant"] = asc
        houses_dict["MC"] = mc
        logging.info("Расчёт домов выполнен успешно")
        return houses_dict
    except Exception as e:
        logging.error(f"Ошибка расчёта домов: {e}")
        return None

def assign_houses_to_planets(planets, houses):
    """Присваивает планетам дома"""
    if not planets or not houses:
        return planets
    
    result = planets.copy()
    for planet_name, data in result.items():
        house_num = get_house(data["longitude"], houses)
        data["house"] = house_num
    
    return result

def format_natal_chart(planets, houses):
    """Форматирует натальную карту для вывода пользователю"""
    planets_with_houses = assign_houses_to_planets(planets, houses)
    
    formatted_data = []
    for planet, data in planets_with_houses.items():
        sign = get_zodiac_sign(data["longitude"])
        house = data["house"]
        planet_ru = translate_to_russian(planet)
        formatted_data.append([planet_ru, sign, f"Дом {house}" if house else "Не определен"])
    
    result = tabulate(formatted_data, headers=["Планета", "Знак", "Дом"], tablefmt="pretty")
    logging.info("Натальная карта отформатирована")
    return result

def get_aspects_between_charts(chart1, chart2):
    """Вычисляет аспекты между двумя натальными картами"""
    aspects = []
    
    # Определяем важные аспекты и их орбисы
    aspect_types = {
        0: {"name": "Соединение", "orb": 8, "influence": "сильное"},
        60: {"name": "Секстиль", "orb": 4, "influence": "положительное"},
        90: {"name": "Квадратура", "orb": 6, "influence": "напряженное"},
        120: {"name": "Трин", "orb": 8, "influence": "положительное"},
        180: {"name": "Оппозиция", "orb": 8, "influence": "напряженное"}
    }
    
    # Определяем наиболее важные планеты для анализа
    important_planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Ascendant", "MC"]
    
    for planet1_name in important_planets:
        if planet1_name not in chart1:
            continue
            
        for planet2_name in important_planets:
            if planet2_name not in chart2:
                continue
                
            # Избегаем сравнения планеты с самой собой в разных картах
            if planet1_name == planet2_name:
                continue
                
            planet1 = chart1[planet1_name]
            planet2 = chart2[planet2_name]
            
            # Вычисляем разницу в долготе
            diff = abs(planet1["longitude"] - planet2["longitude"])
            if diff > 180:
                diff = 360 - diff
                
            # Проверяем аспекты
            for angle, aspect_info in aspect_types.items():
                orb = aspect_info["orb"]
                if angle - orb <= diff <= angle + orb:
                    exact_diff = abs(diff - angle)
                    strength = "сильный" if exact_diff <= orb/2 else "умеренный"
                    
                    aspects.append({
                        "planet1": planet1_name,
                        "planet2": planet2_name,
                        "aspect_type": aspect_info["name"],
                        "angle": angle,
                        "exact_diff": exact_diff,
                        "strength": strength,
                        "influence": aspect_info["influence"]
                    })
    
    return aspects

def format_aspects(aspects):
    """Форматирует аспекты для вывода пользователю"""
    if not aspects:
        return "Нет значимых аспектов между картами."
        
    formatted_aspects = []
    for aspect in aspects:
        planet1_ru = translate_to_russian(aspect["planet1"])
        planet2_ru = translate_to_russian(aspect["planet2"])
        formatted_aspects.append([
            f"{planet1_ru} - {planet2_ru}",
            aspect["aspect_type"],
            aspect["strength"],
            aspect["influence"]
        ])
    
    result = tabulate(formatted_aspects, headers=["Планеты", "Аспект", "Сила", "Влияние"], tablefmt="pretty")
    return result