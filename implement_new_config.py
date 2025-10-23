#!/usr/bin/env python3
"""
全新SQLite安全配置系统快速实施脚本
"""

import os
import sys
import shutil
from datetime import datetime

def create_directory_structure():
    """创建新的目录结构"""
    directories = [
        'config',
        'admin', 
        'templates/admin/services',
        'templates/admin/settings',
        'static/admin/css',
        'static/admin/js',
        'static/admin/img',
        'data/backups',
        'data/keys'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ 创建目录: {directory}")
    
    # 设置安全权限
    os.chmod('data/keys', 0o700)
    os.chmod('data', 0o755)
    print("✓ 设置目录权限")

def backup_old_config():
    """备份旧配置文件"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"old_config_backup_{timestamp}"
    
    os.makedirs(backup_dir, exist_ok=True)
    
    files_to_backup = [
        'services.json',
        '.env',
        'config_loader.py'
    ]
    
    for file in files_to_backup:
        if os.path.exists(file):
            shutil.copy2(file, backup_dir)
            print(f"✓ 备份文件: {file} -> {backup_dir}/")
    
    return backup_dir

def create_core_files():
    """创建核心实现文件"""
    
    # config/__init__.py
    with open('config/__init__.py', 'w') as f:
        f.write('"""新配置管理系统"""\n')
    
    # config/security.py
    security_code = '''from cryptography.fernet import Fernet
import os
import secrets

class SecurityManager:
    def __init__(self, key_dir: str):
        self.key_dir = key_dir
        self.master_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        key_file = os.path.join(self.key_dir, 'master.key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            os.makedirs(self.key_dir, exist_ok=True)
            
            with open(key_file, 'wb') as f:
                f.write(key)
            
            os.chmod(key_file, 0o600)
            return key
    
    def encrypt(self, data: str) -> bytes:
        if not data:
            return b''
        return self.fernet.encrypt(data.encode('utf-8'))
    
    def decrypt(self, encrypted_data: bytes) -> str:
        if not encrypted_data:
            return ''
        return self.fernet.decrypt(encrypted_data).decode('utf-8')
'''
    
    with open('config/security.py', 'w') as f:
        f.write(security_code)
    
    # config/database.py
    database_code = '''import sqlite3
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
'''
    
    with open('config/database.py', 'w') as f:
        f.write(database_code)
    
    # config/manager.py
    manager_code = '''import uuid
from typing import List, Dict, Optional
from .database import DatabaseManager
from .security import SecurityManager

class ConfigManager:
    def __init__(self, db_path: str, key_dir: str):
        self.db = DatabaseManager(db_path)
        self.security = SecurityManager(key_dir)
    
    def create_service(self, config: Dict) -> str:
        service_id = str(uuid.uuid4())
        
        with self.db.get_connection() as conn:
            api_key_encrypted = self.security.encrypt(config.get('api_key', ''))
            
            conn.execute("""
                INSERT INTO translation_services (
                    id, name, description, service_type, base_url,
                    api_key_encrypted, model_name, temperature, max_tokens
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                service_id,
                config['name'],
                config.get('description', ''),
                config['service_type'],
                config['base_url'],
                api_key_encrypted,
                config['model_name'],
                config.get('temperature', 0.3),
                config.get('max_tokens', 4000)
            ))
        
        return service_id
    
    def get_service(self, service_id: str) -> Optional[Dict]:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM translation_services WHERE id = ?',
                (service_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            service = dict(row)
            service['api_key'] = self.security.decrypt(service['api_key_encrypted'])
            service.pop('api_key_encrypted', None)
            
            return service
    
    def list_services(self, active_only: bool = True) -> List[Dict]:
        with self.db.get_connection() as conn:
            query = 'SELECT * FROM translation_services'
            if active_only:
                query += ' WHERE is_active = 1'
            query += ' ORDER BY is_default DESC, name ASC'
            
            cursor = conn.execute(query)
            services = []
            
            for row in cursor.fetchall():
                service = dict(row)
                service.pop('api_key_encrypted', None)
                services.append(service)
            
            return services
    
    def get_default_service(self) -> Optional[Dict]:
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM translation_services WHERE is_default = 1 AND is_active = 1'
            )
            row = cursor.fetchone()
            
            if row:
                return self.get_service(row['id'])
            
            cursor = conn.execute(
                'SELECT * FROM translation_services WHERE is_active = 1 ORDER BY created_at ASC LIMIT 1'
            )
            row = cursor.fetchone()
            
            if row:
                return self.get_service(row['id'])
            
            return None
'''
    
    with open('config/manager.py', 'w') as f:
        f.write(manager_code)
    
    print("✓ 创建核心实现文件")

def update_requirements():
    """更新依赖文件"""
    new_requirements = [
        "cryptography>=41.0.0",
        "Flask-WTF>=1.2.0",
        "WTForms>=3.1.0"
    ]
    
    # 读取现有requirements
    existing_requirements = []
    if os.path.exists('requirements.txt'):
        with open('requirements.txt', 'r') as f:
            existing_requirements = f.read().splitlines()
    
    # 添加新依赖
    for req in new_requirements:
        if not any(req.split('>=')[0] in line for line in existing_requirements):
            existing_requirements.append(req)
    
    # 写回文件
    with open('requirements.txt', 'w') as f:
        f.write('\\n'.join(existing_requirements))
    
    print("✓ 更新requirements.txt")

def create_migration_script():
    """创建迁移脚本"""
    migration_code = '''#!/usr/bin/env python3
"""
从旧配置迁移到新SQLite系统
"""

import json
import os
from config.manager import ConfigManager

def migrate_from_old_config():
    """从services.json迁移配置"""
    
    # 初始化新配置管理器
    manager = ConfigManager('data/config.db', 'data/keys')
    
    # 检查是否存在旧配置
    if not os.path.exists('services.json'):
        print("未找到services.json，创建默认配置")
        create_default_config(manager)
        return
    
    # 读取旧配置
    with open('services.json', 'r', encoding='utf-8') as f:
        old_config = json.load(f)
    
    migrated_count = 0
    
    # 迁移服务配置
    for service_id, service_config in old_config.get('services', {}).items():
        try:
            new_config = {
                'name': service_config.get('comment', service_id),
                'service_type': service_config.get('service_type', 'openai'),
                'base_url': (service_config.get('openai_compatible_base_url') or 
                           service_config.get('ollama_url', '')),
                'model_name': service_config.get('model_name', ''),
                'description': f'从 {service_id} 迁移'
            }
            
            # 处理API密钥
            if 'api_key' in service_config:
                new_config['api_key'] = service_config['api_key']
            elif 'api_key_env_var' in service_config:
                env_var = service_config['api_key_env_var']
                api_key = os.getenv(env_var)
                if api_key:
                    new_config['api_key'] = api_key
                    print(f"从环境变量 {env_var} 获取API密钥")
                else:
                    print(f"警告: 环境变量 {env_var} 未设置，跳过此服务")
                    continue
            
            # 创建服务
            new_service_id = manager.create_service(new_config)
            print(f"✓ 迁移服务: {service_id} -> {new_service_id}")
            migrated_count += 1
            
        except Exception as e:
            print(f"✗ 迁移服务 {service_id} 失败: {e}")
    
    print(f"\\n迁移完成: {migrated_count} 个服务")

def create_default_config(manager):
    """创建默认配置"""
    default_service = {
        'name': 'Ollama本地服务',
        'description': '本地Ollama服务',
        'service_type': 'ollama',
        'base_url': 'http://localhost:11434',
        'model_name': 'llama3',
        'api_key': ''
    }
    
    service_id = manager.create_service(default_service)
    print(f"✓ 创建默认服务: {service_id}")

if __name__ == '__main__':
    migrate_from_old_config()
'''
    
    with open('migrate_config.py', 'w') as f:
        f.write(migration_code)
    
    os.chmod('migrate_config.py', 0o755)
    print("✓ 创建迁移脚本")

def create_new_config_loader():
    """创建新的配置加载器"""
    new_loader_code = '''"""
新的配置加载器 - 替换原有的config_loader.py
"""

from config.manager import ConfigManager

# 全局配置管理器实例
_config_manager = None

def get_config_manager():
    """获取配置管理器实例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager('data/config.db', 'data/keys')
    return _config_manager

def load_service_config():
    """加载服务配置 - 兼容原有API"""
    manager = get_config_manager()
    services = manager.list_services()
    
    # 转换为原有格式
    config = {
        'services': {},
        'default_service_name': None
    }
    
    for service in services:
        service_data = {
            'service_type': service['service_type'],
            'openai_compatible_base_url': service['base_url'],
            'model_name': service['model_name'],
            'comment': service['description']
        }
        
        config['services'][service['name']] = service_data
        
        if service.get('is_default'):
            config['default_service_name'] = service['name']
    
    return config

def get_api_key_from_config(service_config):
    """获取API密钥 - 兼容原有API"""
    # 新系统中API密钥通过服务ID获取
    # 这里需要根据服务名称查找
    manager = get_config_manager()
    services = manager.list_services()
    
    for service in services:
        if service['name'] == service_config.get('comment', ''):
            full_service = manager.get_service(service['id'])
            return full_service.get('api_key', '') if full_service else ''
    
    return ''
'''
    
    with open('new_config_loader.py', 'w') as f:
        f.write(new_loader_code)
    
    print("✓ 创建新配置加载器")

def main():
    """主函数"""
    print("🚀 开始实施全新SQLite安全配置系统...")
    print()
    
    try:
        # 1. 备份旧配置
        backup_dir = backup_old_config()
        print(f"📁 旧配置已备份到: {backup_dir}")
        print()
        
        # 2. 创建目录结构
        create_directory_structure()
        print()
        
        # 3. 创建核心文件
        create_core_files()
        print()
        
        # 4. 更新依赖
        update_requirements()
        print()
        
        # 5. 创建迁移脚本
        create_migration_script()
        print()
        
        # 6. 创建新配置加载器
        create_new_config_loader()
        print()
        
        print("✅ 基础架构创建完成！")
        print()
        print("📋 下一步操作:")
        print("1. 安装新依赖: pip install -r requirements.txt")
        print("2. 运行迁移: python migrate_config.py")
        print("3. 测试新系统: python -c 'from config.manager import ConfigManager; print(\"系统正常\")'")
        print("4. 更新应用代码使用新配置系统")
        print()
        print(f"🔄 如需回滚，请恢复 {backup_dir} 中的文件")
        
    except Exception as e:
        print(f"❌ 实施失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
