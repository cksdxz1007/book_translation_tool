"""
API Client for translation services.

Provides retry logic and error handling for OpenAI-compatible APIs.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class APIError(Exception):
    """API 调用错误"""
    status_code: int
    message: str
    retryable: bool = False


@dataclass
class TranslationResult:
    """翻译结果"""
    success: bool
    translated_text: str = ""
    error: Optional[str] = None
    tokens_used: int = 0
    elapsed_seconds: float = 0


class APIClient:
    """
    API 客户端，支持重试机制的翻译 API 调用

    Features:
    - 自动重试（可配置次数和退避策略）
    - 指数退避
    - 速率限制处理
    - 详细的错误日志
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        max_tokens: int = 8000,
        temperature: float = 0.3,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        timeout: int = 120
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.timeout = timeout

        # 导入 requests（假设在调用环境中可用）
        import requests
        self.requests = requests

    def translate(
        self,
        text: str,
        lang_in: str = 'en',
        lang_out: str = 'zh',
        log_callback: Optional[Callable[[str], None]] = None
    ) -> TranslationResult:
        """
        翻译文本

        Args:
            text: 待翻译文本
            lang_in: 源语言
            lang_out: 目标语言
            log_callback: 日志回调函数

        Returns:
            TranslationResult: 翻译结果
        """
        start_time = time.time()

        # 构建 prompt
        system_prompt = (
            f"You are a professional translator. Translate the following text "
            f"from {lang_in} to {lang_out}. Preserve paragraph breaks with "
            f"double newlines. Only output the translated text."
        )

        payload = {
            'model': self.model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': text}
            ],
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        # 重试逻辑
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = self.requests.post(
                    f'{self.base_url}/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    result = response.json()
                    translated_text = result['choices'][0]['message']['content']
                    elapsed = time.time() - start_time

                    if log_callback:
                        log_callback(f"翻译成功，耗时: {elapsed:.2f}秒")

                    return TranslationResult(
                        success=True,
                        translated_text=translated_text,
                        elapsed_seconds=elapsed
                    )

                elif response.status_code == 429:
                    # 速率限制 - 重试
                    last_error = APIError(
                        status_code=429,
                        message="Rate limit exceeded",
                        retryable=True
                    )
                    wait_time = self.backoff_factor ** attempt
                    if log_callback:
                        log_callback(f"速率限制，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

                elif response.status_code == 500:
                    # 服务器错误 - 重试
                    last_error = APIError(
                        status_code=500,
                        message=response.text[:200],
                        retryable=True
                    )
                    wait_time = self.backoff_factor ** attempt
                    if log_callback:
                        log_callback(f"服务器错误，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)

                else:
                    # 其他错误 - 不重试
                    return TranslationResult(
                        success=False,
                        error=f"API 返回错误: {response.status_code} - {response.text[:200]}",
                        elapsed_seconds=time.time() - start_time
                    )

            except self.requests.exceptions.Timeout:
                last_error = APIError(
                    status_code=0,
                    message="Request timeout",
                    retryable=True
                )
                wait_time = self.backoff_factor ** attempt
                if log_callback:
                    log_callback(f"请求超时，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)

            except self.requests.exceptions.RequestException as e:
                return TranslationResult(
                    success=False,
                    error=f"请求异常: {str(e)}",
                    elapsed_seconds=time.time() - start_time
                )

        # 所有重试都失败
        return TranslationResult(
            success=False,
            error=f"重试 {self.max_retries} 次后仍失败: {last_error.message if last_error else 'Unknown error'}",
            elapsed_seconds=time.time() - start_time
        )

    def translate_batch(
        self,
        texts: list,
        lang_in: str = 'en',
        lang_out: str = 'zh',
        log_callback: Optional[Callable[[str], None]] = None
    ) -> list:
        """
        批量翻译文本

        Args:
            texts: 待翻译文本列表
            lang_in: 源语言
            lang_out: 目标语言
            log_callback: 日志回调函数

        Returns:
            翻译结果列表（按顺序）
        """
        results = []
        for i, text in enumerate(texts):
            if log_callback:
                log_callback(f"翻译块 {i+1}/{len(texts)}...")

            result = self.translate(text, lang_in, lang_out, log_callback)
            results.append(result)

            if not result.success and log_callback:
                log_callback(f"警告: 块 {i+1} 翻译失败 - {result.error}")

        return results