from aiogram.fsm.state import State, StatesGroup

class NatalChartStates(StatesGroup):
    """Состояния для процесса расчёта натальной карты"""
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_city = State()
    waiting_for_hospital_coords_choice = State()
    waiting_for_hospital_coords = State()
    calculating = State()
    dialog_active = State()  # Режим активного диалога после расчёта карты

class CompatibilityStates(StatesGroup):
    """Состояния для процесса проверки совместимости"""
    selecting_action = State()  # Выбор действия: добавить новый контакт или выбрать существующий
    selecting_contact = State()  # Выбор существующего контакта
    waiting_for_partner_name = State()
    waiting_for_partner_birth_date = State()
    waiting_for_partner_birth_time = State()
    waiting_for_partner_city = State()
    waiting_for_partner_relationship = State()
    waiting_for_partner_coords_choice = State()
    waiting_for_partner_coords = State()
    processing_compatibility = State()
    viewing_result = State()

class HoroscopeSettingsStates(StatesGroup):
    """Состояния для настройки ежедневного гороскопа"""
    selecting_action = State()  # Выбор действия: настроить/изменить
    waiting_for_time = State()
    waiting_for_city = State()
    waiting_for_coords_choice = State()
    waiting_for_coords = State()
    confirming_settings = State()

class SubscriptionStates(StatesGroup):
    """Состояния для процесса подписки"""
    selecting_plan = State()
    processing_payment = State()
    confirming_payment = State()

class AdminStates(StatesGroup):
    """Состояния для административной панели"""
    waiting_for_login = State()
    waiting_for_password = State()
    admin_active = State()  # Режим активного администрирования
    selecting_user = State()
    viewing_user_details = State()