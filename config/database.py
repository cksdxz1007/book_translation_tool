import sqlite3
import threading
from contextlib import contextmanager

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, db_path: str):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, db_path: str):
        if not hasattr(self, 'initialized'):
            self.db_path = db_path
            self.initialized = True
            self._init_database()
    
    def _init_database(self):
        with self.get_connection() as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            self._create_tables(conn)
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def _create_tables(self, conn):
        # 翻译服务表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS translation_services (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                service_type TEXT NOT NULL,
                base_url TEXT NOT NULL,
                api_key_encrypted BLOB,
                model_name TEXT NOT NULL,
                temperature REAL DEFAULT 0.3,
                max_tokens INTEGER DEFAULT 4000,
                is_active BOOLEAN DEFAULT 1,
                is_default BOOLEAN DEFAULT 0,
                last_tested TIMESTAMP,
                test_status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 系统设置表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value_encrypted BLOB,
                is_sensitive BOOLEAN DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
