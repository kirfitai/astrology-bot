import sqlite3
from datetime import datetime, timedelta
from config import DB_FILE

def dict_factory(cursor, row):
    """Конвертирует строки SQLite в словари"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_connection():
    """Создает соединение с базой данных с row_factory"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = dict_factory
    return conn

# --- Операции с пользователями ---

def get_user(user_id):
    """Получает данные пользователя по ID"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user

def create_user(user_id, username, first_name, last_name):
    """Создает нового пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (user_id, username, first_name, last_name, free_messages_left)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            last_name = excluded.last_name,
            last_activity = CURRENT_TIMESTAMP
        """,
        (user_id, username, first_name, last_name, 10)
    )
    conn.commit()
    conn.close()
    return get_user(user_id)

def update_user_birth_info(user_id, birth_date, birth_time, city, latitude, longitude, tz_name, natal_chart):
    """Обновляет информацию о рождении пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users SET
            birth_date = ?,
            birth_time = ?,
            city = ?,
            latitude = ?,
            longitude = ?,
            tz_name = ?,
            natal_chart = ?,
            last_activity = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (birth_date, birth_time, city, latitude, longitude, tz_name, natal_chart, user_id)
    )
    conn.commit()
    conn.close()
    return get_user(user_id)

def update_user_horoscope_settings(user_id, time, city, latitude, longitude):
    """Обновляет настройки гороскопа пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users SET
            horoscope_time = ?,
            horoscope_city = ?,
            horoscope_latitude = ?,
            horoscope_longitude = ?,
            last_activity = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (time, city, latitude, longitude, user_id)
    )
    conn.commit()
    conn.close()
    return get_user(user_id)

def update_user_tokens(user_id, input_tokens, output_tokens, cost):
    """Обновляет статистику использования токенов пользователем"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users SET
            input_tokens = input_tokens + ?,
            output_tokens = output_tokens + ?,
            total_cost = total_cost + ?,
            last_activity = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (input_tokens, output_tokens, cost, user_id)
    )
    conn.commit()
    conn.close()
    return get_user(user_id)

def decrement_free_messages(user_id):
    """Уменьшает количество бесплатных сообщений"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users SET
            free_messages_left = MAX(0, free_messages_left - 1),
            last_activity = CURRENT_TIMESTAMP
        WHERE user_id = ? AND subscription_type = 'free'
        """,
        (user_id,)
    )
    conn.commit()
    conn.close()
    return get_user(user_id)

def check_user_can_message(user_id):
    """Проверяет, может ли пользователь отправлять сообщения"""
    user = get_user(user_id)
    if not user:
        return False
    
    if user['subscription_type'] != 'free':
        # Проверяем, не истекла ли подписка
        if user['subscription_end_date']:
            end_date = datetime.fromisoformat(user['subscription_end_date'])
            if end_date > datetime.now():
                return True
            else:
                # Подписка истекла, возвращаем к бесплатному плану
                conn = get_connection()
                cur = conn.cursor()
                cur.execute(
                    """
                    UPDATE users SET
                        subscription_type = 'free',
                        subscription_end_date = NULL
                    WHERE user_id = ?
                    """,
                    (user_id,)
                )
                conn.commit()
                conn.close()
    
    # Для бесплатного плана проверяем лимит сообщений
    return user['free_messages_left'] > 0

def update_user_subscription(user_id, subscription_type, months=1):
    """Обновляет подписку пользователя"""
    end_date = datetime.now() + timedelta(days=30*months)
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE users SET
            subscription_type = ?,
            subscription_end_date = ?,
            last_activity = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        (subscription_type, end_date.isoformat(), user_id)
    )
    conn.commit()
    conn.close()
    return get_user(user_id)

def get_users_with_horoscope_at_time(current_time):
    """Получает пользователей, для которых нужно отправить гороскоп в указанное время"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM users 
        WHERE horoscope_time = ? 
        AND horoscope_city IS NOT NULL
        """,
        (current_time,)
    )
    users = cur.fetchall()
    conn.close()
    return users

def get_all_users():
    """Получает всех пользователей для административных целей"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY last_activity DESC")
    users = cur.fetchall()
    conn.close()
    return users

# --- Операции с контактами ---

def add_contact(user_id, person_name, birth_date, birth_time, city, latitude, longitude, tz_name, relationship, natal_chart):
    """Добавляет или обновляет контакт для совместимости"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO contacts 
        (user_id, person_name, birth_date, birth_time, city, latitude, longitude, tz_name, relationship, natal_chart)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, person_name) DO UPDATE SET
            birth_date = excluded.birth_date,
            birth_time = excluded.birth_time,
            city = excluded.city,
            latitude = excluded.latitude,
            longitude = excluded.longitude,
            tz_name = excluded.tz_name,
            relationship = excluded.relationship,
            natal_chart = excluded.natal_chart
        """,
        (user_id, person_name, birth_date, birth_time, city, latitude, longitude, tz_name, relationship, natal_chart)
    )
    conn.commit()
    contact_id = cur.lastrowid
    conn.close()
    return contact_id

def get_contacts(user_id):
    """Получает все контакты пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contacts WHERE user_id = ? ORDER BY person_name", (user_id,))
    contacts = cur.fetchall()
    conn.close()
    return contacts

def get_contact(contact_id):
    """Получает данные контакта по ID"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM contacts WHERE contact_id = ?", (contact_id,))
    contact = cur.fetchone()
    conn.close()
    return contact

def delete_contact(contact_id, user_id):
    """Удаляет контакт пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM contacts WHERE contact_id = ? AND user_id = ?", (contact_id, user_id))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def find_contact_by_name_or_relationship(user_id, text):
    """Ищет контакт по имени или отношению"""
    conn = get_connection()
    cur = conn.cursor()
    text_pattern = f"%{text}%"
    cur.execute(
        """
        SELECT * FROM contacts 
        WHERE user_id = ? AND (
            LOWER(person_name) LIKE LOWER(?) OR 
            LOWER(relationship) LIKE LOWER(?)
        )
        """,
        (user_id, text_pattern, text_pattern)
    )
    contacts = cur.fetchall()
    conn.close()
    return contacts

# --- Операции с сообщениями ---

def add_message(user_id, direction, content, tokens=0, cost=0):
    """Добавляет сообщение в историю"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO messages (user_id, direction, content, tokens, cost)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, direction, content, tokens, cost)
    )
    conn.commit()
    message_id = cur.lastrowid
    conn.close()
    return message_id

def get_user_messages(user_id, limit=20):
    """Получает историю сообщений пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM messages 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT ?
        """,
        (user_id, limit)
    )
    messages = cur.fetchall()
    conn.close()
    # Возвращаем в обратном порядке, чтобы самые старые были вначале
    return list(reversed(messages))

# --- Операции с гороскопами ---

def add_horoscope(user_id, horoscope_text, horoscope_type='daily'):
    """Сохраняет гороскоп в базу данных"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO horoscopes (user_id, horoscope_text, horoscope_type)
        VALUES (?, ?, ?)
        """,
        (user_id, horoscope_text, horoscope_type)
    )
    conn.commit()
    horoscope_id = cur.lastrowid
    conn.close()
    return horoscope_id

def get_last_horoscope(user_id, horoscope_type='daily'):
    """Получает последний гороскоп пользователя указанного типа"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM horoscopes 
        WHERE user_id = ? AND horoscope_type = ? 
        ORDER BY created_at DESC 
        LIMIT 1
        """,
        (user_id, horoscope_type)
    )
    horoscope = cur.fetchone()
    conn.close()
    return horoscope

# --- Операции с подписками ---

def add_subscription_transaction(user_id, subscription_type, amount, status, payment_method, months=1):
    """Сохраняет транзакцию подписки"""
    start_date = datetime.now().isoformat()
    end_date = (datetime.now() + timedelta(days=30*months)).isoformat()
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO subscription_transactions 
        (user_id, subscription_type, amount, status, payment_method, start_date, end_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (user_id, subscription_type, amount, status, payment_method, start_date, end_date)
    )
    conn.commit()
    transaction_id = cur.lastrowid
    conn.close()
    
    if status == 'completed':
        update_user_subscription(user_id, subscription_type, months)
    
    return transaction_id

def get_user_transactions(user_id):
    """Получает историю транзакций пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM subscription_transactions 
        WHERE user_id = ? 
        ORDER BY created_at DESC
        """,
        (user_id,)
    )
    transactions = cur.fetchall()
    conn.close()
    return transactions

# --- Операции для административной панели ---

def get_admin_by_username(username):
    """Получает администратора по имени пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM admins WHERE username = ?", (username,))
    admin = cur.fetchone()
    conn.close()
    return admin

def add_compatibility_analysis(user_id, contact_id, analysis_text):
    """Сохраняет анализ совместимости"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO compatibility_analyses 
        (user_id, contact_id, analysis_text)
        VALUES (?, ?, ?)
        """,
        (user_id, contact_id, analysis_text)
    )
    conn.commit()
    analysis_id = cur.lastrowid
    conn.close()
    return analysis_id

def get_user_compatibility_analyses(user_id):
    """Получает анализы совместимости пользователя"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ca.*, c.person_name, c.relationship
        FROM compatibility_analyses ca
        JOIN contacts c ON ca.contact_id = c.contact_id
        WHERE ca.user_id = ?
        ORDER BY ca.created_at DESC
        """,
        (user_id,)
    )
    analyses = cur.fetchall()
    conn.close()
    return analyses

def get_total_stats():
    """Получает общую статистику для админ-панели"""
    conn = get_connection()
    cur = conn.cursor()
    
    stats = {}
    
    # Общее число пользователей
    cur.execute("SELECT COUNT(*) as count FROM users")
    stats['total_users'] = cur.fetchone()['count']
    
    # Число активных пользователей (активность за последние 7 дней)
    seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
    cur.execute(
        "SELECT COUNT(*) as count FROM users WHERE last_activity > ?",
        (seven_days_ago,)
    )
    stats['active_users'] = cur.fetchone()['count']
    
    # Число пользователей с платной подпиской
    cur.execute(
        "SELECT COUNT(*) as count FROM users WHERE subscription_type != 'free'"
    )
    stats['paid_users'] = cur.fetchone()['count']
    
    # Общая сумма затрат на OpenAI API
    cur.execute("SELECT SUM(total_cost) as total FROM users")
    stats['total_api_cost'] = cur.fetchone()['total'] or 0
    
    # Общее количество сообщений
    cur.execute("SELECT COUNT(*) as count FROM messages")
    stats['total_messages'] = cur.fetchone()['count']
    
    # Общее количество расчетов совместимости
    cur.execute("SELECT COUNT(*) as count FROM compatibility_analyses")
    stats['total_compatibility_analyses'] = cur.fetchone()['count']
    
    # Общее количество гороскопов
    cur.execute("SELECT COUNT(*) as count FROM horoscopes")
    stats['total_horoscopes'] = cur.fetchone()['count']
    
    conn.close()
    return stats