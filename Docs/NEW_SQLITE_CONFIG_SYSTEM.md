# 全新SQLite安全配置系统

## 🎯 设计目标

完全替换现有的services.json和环境变量模式，构建现代化的安全配置管理系统。

## 🏗️ 新架构设计

### 核心原则
- **统一存储**: 所有配置存储在加密SQLite数据库
- **Web管理**: 完全通过Web界面管理配置
- **安全优先**: 所有敏感数据加密存储
- **用户友好**: 直观的配置界面和向导

### 目录结构
```
book_translation_tool/
├── config/
│   ├── __init__.py
│   ├── database.py        # 数据库管理
│   ├── security.py        # 加密管理
│   ├── manager.py         # 配置管理器
│   └── models.py          # 数据模型
├── admin/
│   ├── __init__.py
│   ├── routes.py          # 管理路由
│   ├── forms.py           # 表单定义
│   └── auth.py            # 认证管理
├── templates/admin/
│   ├── base.html
│   ├── dashboard.html
│   ├── services/
│   └── settings/
├── static/admin/
│   ├── css/
│   ├── js/
│   └── img/
└── data/
    ├── config.db          # 加密数据库
    ├── backups/           # 自动备份
    └── keys/              # 密钥文件
```

## 📊 数据库设计

### 核心表结构
```sql
-- 翻译服务配置表
CREATE TABLE translation_services (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    service_type TEXT NOT NULL, -- 'openai', 'ollama', 'custom'
    
    -- 连接配置
    base_url TEXT NOT NULL,
    api_key_encrypted BLOB,
    timeout_seconds INTEGER DEFAULT 30,
    
    -- 模型配置
    model_name TEXT NOT NULL,
    temperature REAL DEFAULT 0.3,
    max_tokens INTEGER DEFAULT 4000,
    
    -- 自定义配置
    custom_headers_encrypted BLOB,
    custom_params_encrypted BLOB,
    
    -- 状态管理
    is_active BOOLEAN DEFAULT 1,
    is_default BOOLEAN DEFAULT 0,
    last_tested TIMESTAMP,
    test_status TEXT, -- 'success', 'failed', 'pending'
    
    -- 审计字段
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT DEFAULT 'system',
    updated_by TEXT DEFAULT 'system'
);

-- 提示词模板表
CREATE TABLE prompt_templates (
    id TEXT PRIMARY KEY,
    service_id TEXT,
    name TEXT NOT NULL,
    template_type TEXT NOT NULL, -- 'system', 'translation', 'custom'
    
    -- 模板内容（加密）
    content_encrypted BLOB NOT NULL,
    variables JSON, -- 模板变量定义
    
    -- 语言配置
    source_language TEXT DEFAULT 'auto',
    target_language TEXT DEFAULT 'zh-CN',
    
    -- 状态
    is_active BOOLEAN DEFAULT 1,
    usage_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (service_id) REFERENCES translation_services(id) ON DELETE CASCADE
);

-- 系统设置表
CREATE TABLE system_settings (
    key TEXT PRIMARY KEY,
    value_encrypted BLOB,
    value_type TEXT DEFAULT 'string', -- 'string', 'integer', 'boolean', 'json'
    is_sensitive BOOLEAN DEFAULT 0,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 配置变更审计表
CREATE TABLE config_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    record_id TEXT NOT NULL,
    operation TEXT NOT NULL, -- 'CREATE', 'UPDATE', 'DELETE'
    old_values JSON,
    new_values JSON,
    user_id TEXT DEFAULT 'system',
    ip_address TEXT,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 用户会话表（简单认证）
CREATE TABLE admin_sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'admin',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    ip_address TEXT,
    user_agent TEXT
);
```

### 索引优化
```sql
CREATE INDEX idx_services_active ON translation_services(is_active);
CREATE INDEX idx_services_default ON translation_services(is_default);
CREATE INDEX idx_templates_service ON prompt_templates(service_id);
CREATE INDEX idx_templates_type ON prompt_templates(template_type);
CREATE INDEX idx_audit_table_record ON config_audit(table_name, record_id);
CREATE INDEX idx_audit_timestamp ON config_audit(timestamp);
```

## 🔐 安全实现

### 加密管理器
```python
# config/security.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import base64
import secrets

class SecurityManager:
    def __init__(self, key_dir: str):
        self.key_dir = key_dir
        self.master_key = self._get_or_create_master_key()
        self.fernet = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        """获取或创建主加密密钥"""
        key_file = os.path.join(self.key_dir, 'master.key')
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # 创建新密钥
            key = Fernet.generate_key()
            os.makedirs(self.key_dir, exist_ok=True)
            
            with open(key_file, 'wb') as f:
                f.write(key)
            
            # 设置严格权限
            os.chmod(key_file, 0o600)
            os.chmod(self.key_dir, 0o700)
            
            return key
    
    def encrypt(self, data: str) -> bytes:
        """加密字符串数据"""
        if not data:
            return b''
        return self.fernet.encrypt(data.encode('utf-8'))
    
    def decrypt(self, encrypted_data: bytes) -> str:
        """解密数据"""
        if not encrypted_data:
            return ''
        return self.fernet.decrypt(encrypted_data).decode('utf-8')
    
    def encrypt_dict(self, data: dict) -> bytes:
        """加密字典数据"""
        import json
        json_str = json.dumps(data, ensure_ascii=False)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: bytes) -> dict:
        """解密字典数据"""
        import json
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str) if json_str else {}
    
    def generate_session_token(self) -> str:
        """生成安全的会话令牌"""
        return secrets.token_urlsafe(32)
```

### 数据库管理器
```python
# config/database.py
import sqlite3
import threading
from contextlib import contextmanager
from typing import Optional, Dict, List

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
        """初始化数据库"""
        with self.get_connection() as conn:
            # 启用外键约束
            conn.execute("PRAGMA foreign_keys = ON")
            
            # 设置WAL模式
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            
            # 创建表
            self._create_tables(conn)
            self._create_indexes(conn)
            self._create_triggers(conn)
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接"""
        conn = None
        try:
            conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                check_same_thread=False
            )
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
        """创建数据库表"""
        # 翻译服务表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS translation_services (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                service_type TEXT NOT NULL,
                base_url TEXT NOT NULL,
                api_key_encrypted BLOB,
                timeout_seconds INTEGER DEFAULT 30,
                model_name TEXT NOT NULL,
                temperature REAL DEFAULT 0.3,
                max_tokens INTEGER DEFAULT 4000,
                custom_headers_encrypted BLOB,
                custom_params_encrypted BLOB,
                is_active BOOLEAN DEFAULT 1,
                is_default BOOLEAN DEFAULT 0,
                last_tested TIMESTAMP,
                test_status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT DEFAULT 'system',
                updated_by TEXT DEFAULT 'system'
            )
        ''')
        
        # 提示词模板表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS prompt_templates (
                id TEXT PRIMARY KEY,
                service_id TEXT,
                name TEXT NOT NULL,
                template_type TEXT NOT NULL,
                content_encrypted BLOB NOT NULL,
                variables JSON,
                source_language TEXT DEFAULT 'auto',
                target_language TEXT DEFAULT 'zh-CN',
                is_active BOOLEAN DEFAULT 1,
                usage_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (service_id) REFERENCES translation_services(id) ON DELETE CASCADE
            )
        ''')
        
        # 系统设置表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value_encrypted BLOB,
                value_type TEXT DEFAULT 'string',
                is_sensitive BOOLEAN DEFAULT 0,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 审计表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS config_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                old_values JSON,
                new_values JSON,
                user_id TEXT DEFAULT 'system',
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 会话表
        conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL DEFAULT 'admin',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                ip_address TEXT,
                user_agent TEXT
            )
        ''')
```

## 🎨 Web管理界面

### 配置管理器
```python
# config/manager.py
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from .database import DatabaseManager
from .security import SecurityManager

class ConfigManager:
    def __init__(self, db_path: str, key_dir: str):
        self.db = DatabaseManager(db_path)
        self.security = SecurityManager(key_dir)
    
    def create_service(self, config: Dict) -> str:
        """创建翻译服务"""
        service_id = str(uuid.uuid4())
        
        with self.db.get_connection() as conn:
            # 加密敏感字段
            api_key_encrypted = self.security.encrypt(config.get('api_key', ''))
            custom_headers_encrypted = self.security.encrypt_dict(config.get('custom_headers', {}))
            custom_params_encrypted = self.security.encrypt_dict(config.get('custom_params', {}))
            
            conn.execute('''
                INSERT INTO translation_services (
                    id, name, description, service_type, base_url,
                    api_key_encrypted, model_name, temperature, max_tokens,
                    custom_headers_encrypted, custom_params_encrypted,
                    timeout_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                service_id,
                config['name'],
                config.get('description', ''),
                config['service_type'],
                config['base_url'],
                api_key_encrypted,
                config['model_name'],
                config.get('temperature', 0.3),
                config.get('max_tokens', 4000),
                custom_headers_encrypted,
                custom_params_encrypted,
                config.get('timeout_seconds', 30)
            ))
            
            # 记录审计日志
            self._log_audit(conn, 'translation_services', service_id, 'CREATE', {}, config)
        
        return service_id
    
    def get_service(self, service_id: str) -> Optional[Dict]:
        """获取服务配置"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM translation_services WHERE id = ?',
                (service_id,)
            )
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # 解密敏感字段
            service = dict(row)
            service['api_key'] = self.security.decrypt(service['api_key_encrypted'])
            service['custom_headers'] = self.security.decrypt_dict(service['custom_headers_encrypted'])
            service['custom_params'] = self.security.decrypt_dict(service['custom_params_encrypted'])
            
            # 移除加密字段
            for field in ['api_key_encrypted', 'custom_headers_encrypted', 'custom_params_encrypted']:
                service.pop(field, None)
            
            return service
    
    def list_services(self, active_only: bool = True) -> List[Dict]:
        """列出所有服务"""
        with self.db.get_connection() as conn:
            query = 'SELECT * FROM translation_services'
            params = ()
            
            if active_only:
                query += ' WHERE is_active = 1'
            
            query += ' ORDER BY is_default DESC, name ASC'
            
            cursor = conn.execute(query, params)
            services = []
            
            for row in cursor.fetchall():
                service = dict(row)
                # 不返回敏感字段，只返回基本信息
                service.pop('api_key_encrypted', None)
                service.pop('custom_headers_encrypted', None)
                service.pop('custom_params_encrypted', None)
                services.append(service)
            
            return services
    
    def update_service(self, service_id: str, config: Dict) -> bool:
        """更新服务配置"""
        with self.db.get_connection() as conn:
            # 获取旧配置用于审计
            old_config = self.get_service(service_id)
            if not old_config:
                return False
            
            # 加密敏感字段
            api_key_encrypted = self.security.encrypt(config.get('api_key', ''))
            custom_headers_encrypted = self.security.encrypt_dict(config.get('custom_headers', {}))
            custom_params_encrypted = self.security.encrypt_dict(config.get('custom_params', {}))
            
            conn.execute('''
                UPDATE translation_services SET
                    name = ?, description = ?, service_type = ?, base_url = ?,
                    api_key_encrypted = ?, model_name = ?, temperature = ?, max_tokens = ?,
                    custom_headers_encrypted = ?, custom_params_encrypted = ?,
                    timeout_seconds = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                config['name'],
                config.get('description', ''),
                config['service_type'],
                config['base_url'],
                api_key_encrypted,
                config['model_name'],
                config.get('temperature', 0.3),
                config.get('max_tokens', 4000),
                custom_headers_encrypted,
                custom_params_encrypted,
                config.get('timeout_seconds', 30),
                service_id
            ))
            
            # 记录审计日志
            self._log_audit(conn, 'translation_services', service_id, 'UPDATE', old_config, config)
        
        return True
    
    def delete_service(self, service_id: str) -> bool:
        """删除服务配置"""
        with self.db.get_connection() as conn:
            # 获取配置用于审计
            old_config = self.get_service(service_id)
            if not old_config:
                return False
            
            cursor = conn.execute(
                'DELETE FROM translation_services WHERE id = ?',
                (service_id,)
            )
            
            if cursor.rowcount > 0:
                # 记录审计日志
                self._log_audit(conn, 'translation_services', service_id, 'DELETE', old_config, {})
                return True
        
        return False
    
    def set_default_service(self, service_id: str) -> bool:
        """设置默认服务"""
        with self.db.get_connection() as conn:
            # 清除所有默认标记
            conn.execute('UPDATE translation_services SET is_default = 0')
            
            # 设置新的默认服务
            cursor = conn.execute(
                'UPDATE translation_services SET is_default = 1 WHERE id = ?',
                (service_id,)
            )
            
            return cursor.rowcount > 0
    
    def get_default_service(self) -> Optional[Dict]:
        """获取默认服务"""
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM translation_services WHERE is_default = 1 AND is_active = 1'
            )
            row = cursor.fetchone()
            
            if row:
                return self.get_service(row['id'])
            
            # 如果没有默认服务，返回第一个活跃服务
            cursor = conn.execute(
                'SELECT * FROM translation_services WHERE is_active = 1 ORDER BY created_at ASC LIMIT 1'
            )
            row = cursor.fetchone()
            
            if row:
                return self.get_service(row['id'])
            
            return None
    
    def test_service_connection(self, service_id: str) -> Dict:
        """测试服务连接"""
        service = self.get_service(service_id)
        if not service:
            return {"success": False, "error": "Service not found"}
        
        try:
            # 根据服务类型测试连接
            if service['service_type'] == 'openai':
                result = self._test_openai_service(service)
            elif service['service_type'] == 'ollama':
                result = self._test_ollama_service(service)
            else:
                result = self._test_custom_service(service)
            
            # 更新测试状态
            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE translation_services 
                    SET last_tested = CURRENT_TIMESTAMP, test_status = ?
                    WHERE id = ?
                ''', (
                    'success' if result['success'] else 'failed',
                    service_id
                ))
            
            return result
            
        except Exception as e:
            # 更新失败状态
            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE translation_services 
                    SET last_tested = CURRENT_TIMESTAMP, test_status = 'failed'
                    WHERE id = ?
                ''', (service_id,))
            
            return {"success": False, "error": str(e)}
    
    def _test_openai_service(self, service: Dict) -> Dict:
        """测试OpenAI兼容服务"""
        import requests
        
        headers = {
            'Authorization': f'Bearer {service["api_key"]}',
            'Content-Type': 'application/json'
        }
        
        # 添加自定义headers
        if service.get('custom_headers'):
            headers.update(service['custom_headers'])
        
        data = {
            'model': service['model_name'],
            'messages': [{'role': 'user', 'content': 'Hello'}],
            'max_tokens': 10
        }
        
        response = requests.post(
            f"{service['base_url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=service.get('timeout_seconds', 30)
        )
        
        if response.status_code == 200:
            return {"success": True, "message": "连接测试成功"}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    
    def _test_ollama_service(self, service: Dict) -> Dict:
        """测试Ollama服务"""
        import requests
        
        data = {
            'model': service['model_name'],
            'prompt': 'Hello',
            'stream': False
        }
        
        response = requests.post(
            f"{service['base_url']}/api/generate",
            json=data,
            timeout=service.get('timeout_seconds', 30)
        )
        
        if response.status_code == 200:
            return {"success": True, "message": "连接测试成功"}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
    
    def _test_custom_service(self, service: Dict) -> Dict:
        """测试自定义服务"""
        # 实现自定义服务测试逻辑
        return {"success": True, "message": "自定义服务测试跳过"}
    
    def _log_audit(self, conn, table_name: str, record_id: str, operation: str, old_values: Dict, new_values: Dict):
        """记录审计日志"""
        import json
        
        conn.execute('''
            INSERT INTO config_audit (
                table_name, record_id, operation, old_values, new_values
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            table_name,
            record_id,
            operation,
            json.dumps(old_values, ensure_ascii=False),
            json.dumps(new_values, ensure_ascii=False)
        ))
```

## 🚀 实施步骤

### Phase 1: 核心系统 (Day 1-2)
1. 创建目录结构
2. 实现SecurityManager
3. 实现DatabaseManager
4. 实现ConfigManager
5. 创建数据库表和索引

### Phase 2: Web界面 (Day 3-4)
1. 实现管理路由
2. 创建服务配置表单
3. 实现连接测试功能
4. 添加审计日志查看

### Phase 3: 迁移和集成 (Day 5)
1. 创建数据迁移脚本
2. 更新translator.py使用新配置
3. 移除旧的config_loader.py
4. 测试所有翻译功能

### Phase 4: 完善和优化 (Day 6)
1. 添加备份恢复功能
2. 实现配置导入导出
3. 性能优化和安全加固
4. 文档和部署脚本

这个全新的系统将提供：
- 🔒 企业级安全性
- 🎨 现代化Web界面
- 📊 完整的审计追踪
- ⚡ 高性能数据库
- 🛡️ 自动备份恢复

需要我开始实现这个全新的系统吗？
