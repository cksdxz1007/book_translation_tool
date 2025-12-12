#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译服务抽象层

支持多种翻译引擎：
- OpenAI兼容API
- Ollama本地模型
- 自定义API

统一接口，简化调用
"""

import os
import json
import logging
from typing import Dict, Optional, Any, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class TranslationService(ABC):
    """翻译服务抽象基类"""

    @abstractmethod
    def translate(self, text: str, target_language: str, source_language: str = 'auto') -> str:
        """翻译文本"""
        pass

    @abstractmethod
    def translate_batch(self, texts: List[str], target_language: str, source_language: str = 'auto') -> List[str]:
        """批量翻译"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """测试连接"""
        pass

class OpenAITranslationService(TranslationService):
    """OpenAI兼容翻译服务"""

    def __init__(self, api_key: str, base_url: str = None, model: str = 'gpt-3.5-turbo'):
        self.api_key = api_key
        self.base_url = base_url or 'https://api.openai.com/v1'
        self.model = model
        self.client = None

    def translate(self, text: str, target_language: str, source_language: str = 'auto') -> str:
        """翻译单个文本"""
        try:
            # TODO: 实现OpenAI翻译逻辑
            logger.info(f"翻译文本到{target_language}")
            return text
        except Exception as e:
            logger.error(f"翻译失败: {e}")
            raise

    def translate_batch(self, texts: List[str], target_language: str, source_language: str = 'auto') -> List[str]:
        """批量翻译"""
        try:
            # TODO: 实现批量翻译逻辑
            logger.info(f"批量翻译{len(texts)}个文本")
            return texts
        except Exception as e:
            logger.error(f"批量翻译失败: {e}")
            raise

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            # TODO: 实现连接测试
            return True
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False

class OllamaTranslationService(TranslationService):
    """Ollama本地翻译服务"""

    def __init__(self, host: str = 'http://localhost:11434', model: str = 'llama2'):
        self.host = host
        self.model = model

    def translate(self, text: str, target_language: str, source_language: str = 'auto') -> str:
        """翻译单个文本"""
        try:
            # TODO: 实现Ollama翻译逻辑
            logger.info(f"使用Ollama翻译到{target_language}")
            return text
        except Exception as e:
            logger.error(f"Ollama翻译失败: {e}")
            raise

    def translate_batch(self, texts: List[str], target_language: str, source_language: str = 'auto') -> List[str]:
        """批量翻译"""
        try:
            # TODO: 实现批量翻译逻辑
            logger.info(f"使用Ollama批量翻译{len(texts)}个文本")
            return texts
        except Exception as e:
            logger.error(f"Ollama批量翻译失败: {e}")
            raise

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            # TODO: 实现连接测试
            return True
        except Exception as e:
            logger.error(f"Ollama连接测试失败: {e}")
            return False

class TranslationEngine:
    """翻译引擎管理器"""

    def __init__(self):
        self.services: Dict[str, TranslationService] = {}
        self.current_service: Optional[TranslationService] = None

    def register_service(self, name: str, service: TranslationService):
        """注册翻译服务"""
        self.services[name] = service
        logger.info(f"注册翻译服务: {name}")

    def set_default_service(self, name: str):
        """设置默认翻译服务"""
        if name in self.services:
            self.current_service = self.services[name]
            logger.info(f"设置默认翻译服务: {name}")
        else:
            raise ValueError(f"服务 {name} 不存在")

    def translate(self, text: str, target_language: str, source_language: str = 'auto') -> str:
        """使用默认服务翻译"""
        if not self.current_service:
            raise ValueError("未设置默认翻译服务")
        return self.current_service.translate(text, target_language, source_language)

    def translate_batch(self, texts: List[str], target_language: str, source_language: str = 'auto') -> List[str]:
        """使用默认服务批量翻译"""
        if not self.current_service:
            raise ValueError("未设置默认翻译服务")
        return self.current_service.translate_batch(texts, target_language, source_language)

    def test_all_connections(self) -> Dict[str, bool]:
        """测试所有服务连接"""
        results = {}
        for name, service in self.services.items():
            results[name] = service.test_connection()
        return results

# 全局翻译引擎实例
translation_engine = TranslationEngine()

def init_translation_services():
    """初始化翻译服务"""
    # 从环境变量或配置文件读取服务配置
    # 这里先添加默认配置

    # OpenAI服务
    if os.getenv('OPENAI_API_KEY'):
        openai_service = OpenAITranslationService(
            api_key=os.getenv('OPENAI_API_KEY'),
            base_url=os.getenv('OPENAI_BASE_URL'),
            model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        )
        translation_engine.register_service('openai', openai_service)

    # Ollama服务
    ollama_service = OllamaTranslationService(
        host=os.getenv('OLLAMA_HOST', 'http://localhost:11434'),
        model=os.getenv('OLLAMA_MODEL', 'llama2')
    )
    translation_engine.register_service('ollama', ollama_service)

    # 设置默认服务
    default_service = os.getenv('DEFAULT_SERVICE', 'openai')
    try:
        translation_engine.set_default_service(default_service)
    except ValueError as e:
        logger.warning(f"设置默认服务失败: {e}")

    logger.info("翻译服务初始化完成")

# 便捷函数
def translate_text(text: str, target_language: str, source_language: str = 'auto') -> str:
    """翻译文本的便捷函数"""
    return translation_engine.translate(text, target_language, source_language)

def translate_texts(texts: List[str], target_language: str, source_language: str = 'auto') -> List[str]:
    """批量翻译文本的便捷函数"""
    return translation_engine.translate_batch(texts, target_language, source_language)

if __name__ == '__main__':
    # 测试代码
    init_translation_services()

    # 测试连接
    results = translation_engine.test_all_connections()
    print("服务连接测试结果:")
    for name, status in results.items():
        print(f"  {name}: {'✅' if status else '❌'}")
