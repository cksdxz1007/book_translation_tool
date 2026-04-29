#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite配置管理器

提供加密的配置存储和管理功能
"""

import os
import sqlite3
import logging
from cryptography.fernet import Fernet
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

def parse_token_input(value: str) -> Optional[int]:
    """
    将用户输入转换为 token 数字

    支持格式:
    - "128K" -> 128000
    - "8K" -> 8192
    - "1000" -> 1000
    - "1M" -> 1000000
    """
    if not value or not value.strip():
        return None

    value = value.strip().upper()

    # 处理 K, M 后缀 (使用 1024 进制，符合计算机科学惯例)
    multiplier = 1
    if value.endswith('K'):
        multiplier = 1024
        value = value[:-1]
    elif value.endswith('M'):
        multiplier = 1024 * 1024
        value = value[:-1]

    try:
        return int(float(value) * multiplier)
    except (ValueError, TypeError):
        return None

def format_token_value(value: Optional[int]) -> str:
    """
    将数字转换为友好显示格式（使用 1024 进制）

    例如:
    - 131072 -> "128K"
    - 8192 -> "8K"
    - 1048576 -> "1M"
    - None -> ""
    """
    if value is None:
        return ""

    # Convert to int if it's a string
    if isinstance(value, str):
        try:
            value = int(value)
        except (ValueError, TypeError):
            return ""

    if value >= 1024 * 1024:
        return f"{value // (1024 * 1024)}M"
    elif value >= 1024:
        return f"{value // 1024}K"
    else:
        return str(value)

class ConfigManager:
    """配置管理器"""

    def __init__(self, db_path: str = 'data/config.db', key_path: str = 'data/keys/master.key'):
        self.db_path = db_path
        self.key_path = key_path
        self.cipher = self._init_cipher()
        self._init_db()

    def _init_cipher(self) -> Optional[Fernet]:
        """初始化加密器"""
        try:
            if os.path.exists(self.key_path):
                with open(self.key_path, 'rb') as f:
                    key = f.read()
                return Fernet(key)
            else:
                # 生成新密钥
                key = Fernet.generate_key()
                os.makedirs(os.path.dirname(self.key_path), exist_ok=True)
                with open(self.key_path, 'wb') as f:
                    f.write(key)
                return Fernet(key)
        except Exception as e:
            logger.error(f"初始化加密器失败: {e}")
            return None

    def _init_db(self):
        """初始化数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS services (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    type TEXT NOT NULL,
                    url TEXT,
                    model TEXT,
                    api_key TEXT,
                    config TEXT,
                    is_default INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'unknown',
                    last_checked TIMESTAMP,
                    context_length TEXT,
                    max_output_length TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 检查并添加 is_default 列（兼容旧数据库）
            cursor.execute("PRAGMA table_info(services)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'is_default' not in columns:
                cursor.execute('ALTER TABLE services ADD COLUMN is_default INTEGER DEFAULT 0')

            # 检查并添加 status 列（兼容旧数据库）
            if 'status' not in columns:
                cursor.execute('ALTER TABLE services ADD COLUMN status TEXT DEFAULT "unknown"')

            # 检查并添加 last_checked 列（兼容旧数据库）
            if 'last_checked' not in columns:
                cursor.execute('ALTER TABLE services ADD COLUMN last_checked TIMESTAMP')

            # 检查并添加 context_length 列（兼容旧数据库）
            if 'context_length' not in columns:
                cursor.execute('ALTER TABLE services ADD COLUMN context_length INTEGER')
            else:
                # 如果是 TEXT 类型，转换为 INTEGER
                cursor.execute("PRAGMA table_info(services)")
                for col in cursor.fetchall():
                    if col[1] == 'context_length' and col[2] == 'TEXT':
                        logger.info("转换 context_length 从 TEXT 到 INTEGER")
                        cursor.execute('ALTER TABLE services ADD COLUMN context_length_new INTEGER')
                        cursor.execute('UPDATE services SET context_length_new = CAST(context_length AS INTEGER) WHERE context_length IS NOT NULL')
                        cursor.execute('ALTER TABLE services DROP COLUMN context_length')
                        cursor.execute('ALTER TABLE services RENAME COLUMN context_length_new TO context_length')

            # 检查并添加 max_output_length 列（兼容旧数据库）
            if 'max_output_length' not in columns:
                cursor.execute('ALTER TABLE services ADD COLUMN max_output_length INTEGER')
            else:
                # 如果是 TEXT 类型，转换为 INTEGER
                cursor.execute("PRAGMA table_info(services)")
                for col in cursor.fetchall():
                    if col[1] == 'max_output_length' and col[2] == 'TEXT':
                        logger.info("转换 max_output_length 从 TEXT 到 INTEGER")
                        cursor.execute('ALTER TABLE services ADD COLUMN max_output_length_new INTEGER')
                        cursor.execute('UPDATE services SET max_output_length_new = CAST(max_output_length AS INTEGER) WHERE max_output_length IS NOT NULL')
                        cursor.execute('ALTER TABLE services DROP COLUMN max_output_length')
                        cursor.execute('ALTER TABLE services RENAME COLUMN max_output_length_new TO max_output_length')

            conn.commit()
            conn.close()
            logger.info("数据库初始化完成")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")

    def encrypt_data(self, data: str) -> str:
        """加密数据"""
        if not self.cipher:
            return data
        try:
            encrypted = self.cipher.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            return data

    def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        if not self.cipher:
            return encrypted_data
        try:
            decrypted = self.cipher.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            return encrypted_data

    def save_service(self, name: str, service_type: str, url: str = None,
                    model: str = None, api_key: str = None, config: Dict = None,
                    context_length: str = None, max_output_length: str = None,
                    is_default: bool = False) -> bool:
        """保存翻译服务配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 加密敏感数据
            encrypted_api_key = self.encrypt_data(api_key) if api_key else None
            encrypted_config = self.encrypt_data(str(config)) if config else None

            # 转换 token 输入为数字
            context_length_int = parse_token_input(context_length) if context_length else None
            max_output_length_int = parse_token_input(max_output_length) if max_output_length else None

            # 如果设为默认，先取消其他默认
            if is_default:
                cursor.execute('UPDATE services SET is_default = 0')

            cursor.execute('''
                INSERT OR REPLACE INTO services
                (name, type, url, model, api_key, config, context_length, max_output_length, is_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, service_type, url, model, encrypted_api_key, encrypted_config, context_length_int, max_output_length_int, 1 if is_default else 0))

            conn.commit()
            conn.close()
            logger.info(f"服务配置已保存: {name}")
            return True
        except Exception as e:
            logger.error(f"保存服务配置失败: {e}")
            return False

    def update_service(self, service_id: int, name: str, service_type: str, url: str = None,
                      model: str = None, api_key=None, context_length: str = None,
                      max_output_length: str = None) -> bool:
        """更新翻译服务配置

        Args:
            api_key: Three states supported:
                - None: Don't change (preserve existing)
                - '' (empty string): Clear the API key
                - 'value': Set to new value (will be encrypted)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Handle api_key update logic
            # None = don't change, '' = clear, 'value' = set new value
            if api_key is None:
                # Don't change - fetch existing
                cursor.execute('SELECT api_key FROM services WHERE id = ?', (service_id,))
                row = cursor.fetchone()
                encrypted_api_key = row[0] if row else None
            elif api_key == '':
                # Clear the API key
                encrypted_api_key = None
            else:
                # Set new value
                encrypted_api_key = self.encrypt_data(api_key)

            # 转换 token 输入为数字
            context_length_int = parse_token_input(context_length) if context_length else None
            max_output_length_int = parse_token_input(max_output_length) if max_output_length else None

            cursor.execute('''
                UPDATE services SET name=?, type=?, url=?, model=?, api_key=?, context_length=?, max_output_length=?
                WHERE id=?
            ''', (name, service_type, url, model, encrypted_api_key, context_length_int, max_output_length_int, service_id))

            conn.commit()
            conn.close()
            logger.info(f"服务配置已更新: {name}")
            return True
        except Exception as e:
            logger.error(f"更新服务配置失败: {e}")
            return False

    def set_default_service(self, service_id: int) -> bool:
        """设置默认翻译服务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 先取消所有默认
            cursor.execute('UPDATE services SET is_default = 0')
            # 设置新默认
            cursor.execute('UPDATE services SET is_default = 1 WHERE id = ?', (service_id,))

            conn.commit()
            conn.close()
            logger.info(f"已设置默认服务 ID: {service_id}")
            return True
        except Exception as e:
            logger.error(f"设置默认服务失败: {e}")
            return False

    def delete_service_by_id(self, service_id: int) -> bool:
        """根据ID删除翻译服务配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM services WHERE id = ?', (service_id,))

            conn.commit()
            conn.close()
            logger.info(f"服务配置已删除 ID: {service_id}")
            return True
        except Exception as e:
            logger.error(f"删除服务配置失败: {e}")
            return False

    def get_service(self, name: str) -> Optional[Dict[str, Any]]:
        """获取翻译服务配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM services WHERE name = ?', (name,))
            row = cursor.fetchone()

            conn.close()

            if row:
                # 计算索引以处理不同数据库版本的字段
                # id, name, type, url, model, api_key, config, is_default, status, last_checked, context_length, max_output_length, created_at
                context_length_idx = 10 if len(row) > 10 else None
                max_output_length_idx = 11 if len(row) > 11 else None
                created_at_idx = 12 if len(row) > 12 else None

                service = {
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'url': row[3],
                    'model': row[4],
                    'api_key': self.decrypt_data(row[5]) if row[5] else None,
                    'config': self.decrypt_data(row[6]) if row[6] else None,
                    'context_length': row[context_length_idx] if context_length_idx and row[context_length_idx] is not None else None,
                    'context_length_formatted': format_token_value(row[context_length_idx]) if context_length_idx and row[context_length_idx] is not None else "",
                    'max_output_length': row[max_output_length_idx] if max_output_length_idx and row[max_output_length_idx] is not None else None,
                    'max_output_length_formatted': format_token_value(row[max_output_length_idx]) if max_output_length_idx and row[max_output_length_idx] is not None else "",
                    'created_at': row[created_at_idx] if created_at_idx and len(row) > created_at_idx else None
                }
                return service
            return None
        except Exception as e:
            logger.error(f"获取服务配置失败: {e}")
            return None

    def get_service_by_id(self, service_id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取翻译服务配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 将service_id转换为整数
            service_id_int = int(service_id)
            cursor.execute('SELECT * FROM services WHERE id = ?', (service_id_int,))
            row = cursor.fetchone()

            conn.close()

            if row:
                # 计算索引以处理不同数据库版本的字段
                # id, name, type, url, model, api_key, config, is_default, status, last_checked, context_length, max_output_length, created_at
                context_length_idx = 10 if len(row) > 10 else None
                max_output_length_idx = 11 if len(row) > 11 else None
                created_at_idx = 12 if len(row) > 12 else None

                service = {
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'url': row[3],
                    'model': row[4],
                    'api_key': self.decrypt_data(row[5]) if row[5] else None,
                    'config': self.decrypt_data(row[6]) if row[6] else None,
                    'is_default': row[7] if len(row) > 7 else False,
                    'status': row[8] if len(row) > 8 else None,
                    'last_checked': row[9] if len(row) > 9 else None,
                    'context_length': row[context_length_idx] if context_length_idx and row[context_length_idx] is not None else None,
                    'context_length_formatted': format_token_value(row[context_length_idx]) if context_length_idx and row[context_length_idx] is not None else "",
                    'max_output_length': row[max_output_length_idx] if max_output_length_idx and row[max_output_length_idx] is not None else None,
                    'max_output_length_formatted': format_token_value(row[max_output_length_idx]) if max_output_length_idx and row[max_output_length_idx] is not None else "",
                    'created_at': row[created_at_idx] if created_at_idx and len(row) > created_at_idx else None
                }
                return service
            return None
        except Exception as e:
            logger.error(f"通过ID获取服务配置失败: {e}")
            return None

    def get_all_services(self) -> list:
        """获取所有翻译服务配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT id, name, type, url, model, api_key, config, is_default, status, last_checked, context_length, max_output_length, created_at FROM services ORDER BY is_default DESC, created_at DESC')
            rows = cursor.fetchall()

            conn.close()

            services = []
            for row in rows:
                service = {
                    'id': row[0],
                    'name': row[1],
                    'type': row[2],
                    'url': row[3],
                    'model': row[4],
                    'api_key': self.decrypt_data(row[5]) if row[5] else None,
                    'config': self.decrypt_data(row[6]) if row[6] else None,
                    'is_default': bool(row[7]) if row[7] is not None else False,
                    'status': row[8] if row[8] else 'unknown',
                    'last_checked': row[9],
                    'context_length': row[10],
                    'context_length_formatted': format_token_value(row[10]) if row[10] is not None else "",
                    'max_output_length': row[11],
                    'max_output_length_formatted': format_token_value(row[11]) if row[11] is not None else "",
                    'created_at': row[12]
                }
                services.append(service)

            return services
        except Exception as e:
            logger.error(f"获取所有服务配置失败: {e}")
            return []

    def update_service_status(self, service_id: int, status: str) -> bool:
        """更新服务状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE services
                SET status = ?, last_checked = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, service_id))

            conn.commit()
            conn.close()
            logger.info(f"服务状态已更新 ID: {service_id}, 状态: {status}")
            return True
        except Exception as e:
            logger.error(f"更新服务状态失败: {e}")
            return False

    def check_service_health(self, service: Dict[str, Any]) -> tuple[bool, str]:
        """检查服务健康状态"""
        try:
            if service['type'] == 'openai':
                return self._check_openai_service(service)
            elif service['type'] == 'ollama':
                return self._check_ollama_service(service)
            elif service['type'] == 'third_party_completion':
                return self._check_third_party_service(service)
            else:
                return False, f"不支持的服务类型: {service['type']}"
        except Exception as e:
            logger.error(f"检查服务健康状态失败: {e}")
            return False, f"检查失败: {str(e)}"

    def _check_openai_service(self, service: Dict[str, Any]) -> tuple[bool, str]:
        """检查OpenAI兼容服务"""
        try:
            import requests

            if not service.get('url') or not service.get('api_key'):
                return False, "缺少URL或API Key"

            headers = {
                'Authorization': f"Bearer {service['api_key']}",
                'Content-Type': 'application/json'
            }

            # 发送一个简单的模型列表请求来测试连接
            response = requests.get(
                f"{service['url'].rstrip('/')}/models",
                headers=headers,
                timeout=5
            )

            if response.status_code == 200:
                return True, "服务正常"
            elif response.status_code == 401:
                return False, "API Key无效"
            else:
                return False, f"HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "连接超时"
        except requests.exceptions.ConnectionError:
            return False, "连接失败"
        except Exception as e:
            return False, f"检查失败: {str(e)}"

    def _check_ollama_service(self, service: Dict[str, Any]) -> tuple[bool, str]:
        """检查Ollama服务"""
        try:
            import requests

            url = service.get('url', 'http://localhost:11434')

            response = requests.get(
                f"{url.rstrip('/')}/api/tags",
                timeout=5
            )

            if response.status_code == 200:
                return True, "服务正常"
            else:
                return False, f"HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            return False, "连接超时"
        except requests.exceptions.ConnectionError:
            return False, "连接失败"
        except Exception as e:
            return False, f"检查失败: {str(e)}"

    def _check_third_party_service(self, service: Dict[str, Any]) -> tuple[bool, str]:
        """检查第三方服务 - 实际发送测试请求验证连接"""
        try:
            import requests

            url = service.get('url')
            api_key = service.get('api_key')
            model = service.get('model', 'deepseek-chat')

            if not url:
                return False, "缺少URL"

            if not api_key:
                return False, "缺少API Key"

            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }

            payload = {
                'model': model,
                'messages': [
                    {'role': 'user', 'content': 'Hi'}
                ],
                'max_tokens': 5
            }

            # 发送测试请求到 chat/completions 端点
            response = requests.post(
                f'{url.rstrip("/")}/chat/completions',
                headers=headers,
                json=payload,
                timeout=10
            )

            if response.status_code == 200:
                return True, "服务正常"
            elif response.status_code == 401:
                return False, "API Key无效"
            elif response.status_code == 404:
                return False, "API端点不存在"
            else:
                return False, f"HTTP {response.status_code}: {response.text[:100]}"
        except requests.exceptions.Timeout:
            return False, "连接超时"
        except requests.exceptions.ConnectionError:
            return False, "连接失败"
        except Exception as e:
            return False, f"检查失败: {str(e)}"

    def delete_service(self, name: str) -> bool:
        """删除翻译服务配置"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('DELETE FROM services WHERE name = ?', (name,))

            conn.commit()
            conn.close()
            logger.info(f"服务配置已删除: {name}")
            return True
        except Exception as e:
            logger.error(f"删除服务配置失败: {e}")
            return False

# 全局配置管理器实例
config_manager = ConfigManager()
