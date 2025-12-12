#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
应用配置

统一的配置管理
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class AppConfig:
    """应用配置类"""

    # Flask配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_FILE_SIZE', 52428800))  # 50MB

    # 服务器配置
    HOST = os.getenv('APP_HOST', '127.0.0.1')
    PORT = int(os.getenv('APP_PORT', 5001))
    DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'

    # 翻译服务配置
    DEFAULT_SERVICE = os.getenv('DEFAULT_SERVICE', 'openai')

    # OpenAI配置
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

    # Ollama配置
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama2')

    # BabelDOC配置
    BABELDOC_API_URL = os.getenv('BABELDOC_API_URL', 'https://api.deepseek.com')
    BABELDOC_API_KEY = os.getenv('BABELDOC_API_KEY')

    # 数据库配置
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/config.db')
    ENCRYPTION_KEY_PATH = os.getenv('ENCRYPTION_KEY_PATH', 'data/keys/master.key')

    # 管理员配置
    ADMIN_ACCESS_KEY = os.getenv('ADMIN_ACCESS_KEY')

    @classmethod
    def get_flask_config(cls) -> Dict[str, Any]:
        """获取Flask配置字典"""
        return {
            'SECRET_KEY': cls.SECRET_KEY,
            'MAX_CONTENT_LENGTH': cls.MAX_CONTENT_LENGTH,
            'DEBUG': cls.DEBUG
        }

    @classmethod
    def get_translation_config(cls) -> Dict[str, Any]:
        """获取翻译配置字典"""
        return {
            'default_service': cls.DEFAULT_SERVICE,
            'openai': {
                'api_key': cls.OPENAI_API_KEY,
                'base_url': cls.OPENAI_BASE_URL,
                'model': cls.OPENAI_MODEL
            },
            'ollama': {
                'host': cls.OLLAMA_HOST,
                'model': cls.OLLAMA_MODEL
            },
            'babeldoc': {
                'api_url': cls.BABELDOC_API_URL,
                'api_key': cls.BABELDOC_API_KEY
            }
        }

    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """获取数据库配置字典"""
        return {
            'database_path': cls.DATABASE_PATH,
            'encryption_key_path': cls.ENCRYPTION_KEY_PATH
        }
