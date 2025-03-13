import logging
import traceback
import os
import sys
from datetime import datetime

from config import LOG_LEVEL

# Убедимся, что директория для логов существует
log_directory = 'logs'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Создаем форматтер для логов
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Настраиваем вывод в файл
current_date = datetime.now().strftime("%Y%m%d")
file_handler = logging.FileHandler(f'{log_directory}/bot_{current_date}.log', encoding='utf-8')
file_handler.setFormatter(formatter)

# Настраиваем вывод в консоль
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(formatter)

# Получаем корневой логгер и настраиваем его
logger = logging.getLogger('astrology_bot')
logger.setLevel(getattr(logging, LOG_LEVEL))
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Создаем словарь для отслеживания частых ошибок
error_counter = {}

def setup_logging():
    """Настраивает логирование для всех модулей бота"""
    # Устанавливаем обработчики для всех логгеров пакета
    for module in ['bot', 'handlers', 'services', 'database', 'middleware', 'utils']:
        module_logger = logging.getLogger(module)
        module_logger.setLevel(getattr(logging, LOG_LEVEL))
        module_logger.handlers = []  # Очищаем существующие обработчики
        module_logger.addHandler(file_handler)
        module_logger.addHandler(console_handler)
        module_logger.propagate = False  # Отключаем пропагацию в корневой логгер

    return logger

def log_error(e, context=None):
    """
    Логирует ошибку с контекстом и стеком вызовов.
    Отслеживает частые ошибки для возможного уведомления администратора.
    """
    error_type = type(e).__name__
    error_message = str(e)
    error_key = f"{error_type}:{error_message}"
    
    # Увеличиваем счетчик для данной ошибки
    if error_key in error_counter:
        error_counter[error_key] += 1
    else:
        error_counter[error_key] = 1
    
    # Формируем сообщение об ошибке
    error_info = {
        'error_type': error_type,
        'error_message': error_message,
        'context': context or 'No context provided',
        'stack_trace': traceback.format_exc()
    }
    
    # Логируем ошибку
    logger.error(f"Error: {error_type} - {error_message}")
    logger.error(f"Context: {error_info['context']}")
    logger.error(f"Stack trace:\n{error_info['stack_trace']}")
    
    # Если ошибка повторяется часто, отмечаем это
    if error_counter[error_key] >= 5:
        logger.critical(f"ATTENTION: Error '{error_key}' occurred {error_counter[error_key]} times. "
                       f"This may indicate a systemic issue that needs immediate attention.")
    
    return error_info

def handle_exception(func):
    """
    Декоратор для обработки исключений в функциях.
    Логирует ошибку и возвращает пользователю информативное сообщение.
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Определяем контекст вызова
            context = {
                'function': func.__name__,
                'args': str(args),
                'kwargs': str(kwargs)
            }
            
            # Логируем ошибку
            error_info = log_error(e, context)
            
            # Если в аргументах есть message, отправляем уведомление пользователю
            for arg in args:
                if hasattr(arg, 'answer'):
                    try:
                        await arg.answer(
                            "❌ Произошла ошибка при обработке вашего запроса. "
                            "Администратор был уведомлен. Пожалуйста, попробуйте позже или "
                            "воспользуйтесь другой функцией."
                        )
                    except Exception as msg_error:
                        logger.error(f"Failed to send error message to user: {str(msg_error)}")
                    break
            
            # Возвращаем информацию об ошибке для дальнейшей обработки
            return {
                'success': False,
                'error': error_info
            }
    return wrapper

def check_critical_errors(admin_notification_func=None):
    """
    Проверяет наличие критических ошибок и уведомляет администратора если необходимо.
    admin_notification_func должна быть функцией, принимающей сообщение для отправки администратору.
    """
    critical_errors = {k: v for k, v in error_counter.items() if v >= 5}
    
    if critical_errors and admin_notification_func:
        critical_messages = [f"Error '{k}' occurred {v} times" for k, v in critical_errors.items()]
        message = "⚠️ CRITICAL ERROR NOTIFICATION ⚠️\n\n" + "\n".join(critical_messages)
        
        try:
            admin_notification_func(message)
            # После уведомления сбрасываем счетчики
            for k in critical_errors:
                error_counter[k] = 0
        except Exception as e:
            logger.error(f"Failed to notify admin about critical errors: {str(e)}")
    
    return critical_errors

class ErrorContext:
    """Контекстный менеджер для упрощения отлова и логирования ошибок"""
    def __init__(self, context_name, silent=False):
        self.context_name = context_name
        self.silent = silent
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            log_error(exc_val, self.context_name)
            return self.silent  # Если silent=True, исключение будет подавлено
        return False