import sqlite3
from datetime import datetime
from config import DB_FILE

def init_db():
    """Инициализирует базу данных и создает необходимые таблицы"""
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        
        # Таблица пользователей
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            birth_date TEXT,
            birth_time TEXT,
            city TEXT,
            latitude REAL,
            longitude REAL,
            tz_name TEXT,
            natal_chart TEXT,
            subscription_type TEXT DEFAULT 'free',
            subscription_end_date TEXT,
            free_messages_left INTEGER DEFAULT 3,
            horoscope_time TEXT DEFAULT '08:00',
            horoscope_city TEXT,
            horoscope_latitude REAL,
            horoscope_longitude REAL,
            registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
            last_activity TEXT DEFAULT CURRENT_TIMESTAMP,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            total_cost REAL DEFAULT 0.0
        )
        """)
        
        # Таблица контактов для совместимости
        cur.execute("""
        CREATE TABLE IF NOT EXISTS contacts (
            contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            person_name TEXT,
            birth_date TEXT,
            birth_time TEXT,
            city TEXT,
            latitude REAL,
            longitude REAL,
            tz_name TEXT,
            relationship TEXT,
            natal_chart TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, person_name)
        )
        """)
        
        # Таблица анализов совместимости
        cur.execute("""
        CREATE TABLE IF NOT EXISTS compatibility_analyses (
            analysis_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            contact_id INTEGER,
            analysis_text TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
        )
        """)
        
        # Таблица сообщений
        cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            direction TEXT,  -- 'in' для входящих, 'out' для исходящих
            content TEXT,
            tokens INTEGER DEFAULT 0,
            cost REAL DEFAULT 0.0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Таблица транзакций подписки с обновленной структурой
        cur.execute("""
        CREATE TABLE IF NOT EXISTS subscription_transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            subscription_type TEXT,
            amount REAL,
            status TEXT,
            payment_method TEXT,
            start_date TEXT,
            end_date TEXT,
            additional_data TEXT, -- JSON данные для хранения доп. информации о платеже
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Таблица гороскопов
        cur.execute("""
        CREATE TABLE IF NOT EXISTS horoscopes (
            horoscope_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            horoscope_text TEXT,
            horoscope_type TEXT,  -- 'daily' или 'monthly'
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Таблица администраторов
        cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Индексы для ускорения запросов
        cur.execute("CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_contacts_user_id ON contacts(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_horoscopes_user_id ON horoscopes(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON subscription_transactions(user_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_status ON subscription_transactions(status)")
        
        # Проверяем, нужно ли добавить column additional_data в таблицу subscription_transactions
        # если она уже существует, но без этого поля
        try:
            cur.execute("SELECT additional_data FROM subscription_transactions LIMIT 1")
        except sqlite3.OperationalError:
            # Колонки нет, добавляем
            cur.execute("ALTER TABLE subscription_transactions ADD COLUMN additional_data TEXT")
            conn.commit()
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Ошибка инициализации базы данных: {e}")
        return False