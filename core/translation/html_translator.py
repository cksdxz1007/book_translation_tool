"""
HTML Translator for document translation.

Provides mono and dual translation modes with HTML structure preservation.
"""

import time
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from bs4 import BeautifulSoup
from core.chunking.token_chunker import TokenChunker

logger = logging.getLogger(__name__)


@dataclass
class TranslateConfig:
    """翻译配置"""
    api_key: str
    model: str
    base_url: str
    lang_in: str = 'en'
    lang_out: str = 'zh'
    max_tokens: int = 8000
    max_input_tokens: int = 6400  # 80% 软限制
    temperature: float = 0.3


@dataclass
class TranslatedElement:
    """翻译后的元素"""
    element_id: str
    original_text: str
    translated_text: str


class HTMLTranslator:
    """
    HTML 内容翻译器

    Features:
    - 单语模式：保留 HTML 结构，只替换文本
    - 双语模式：原文+译文依次显示
    - 智能分块：基于 token 数量分块
    - 重试机制：API 调用失败自动重试
    """

    # 可翻译的块级元素标签
    BLOCK_TAGS = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'td', 'th']

    def __init__(self, config: TranslateConfig):
        self.config = config
        self.chunker = TokenChunker(max_tokens=config.max_input_tokens)

        # 导入 API 客户端
        from .api_client import APIClient
        self.api_client = APIClient(
            api_key=config.api_key,
            model=config.model,
            base_url=config.base_url,
            max_tokens=config.max_tokens,
            temperature=config.temperature
        )

    def _parse_elements(self, html_content: str) -> List[BeautifulSoup]:
        """
        解析 HTML，收集可翻译的叶子元素

        Args:
            html_content: HTML 内容

        Returns:
            可翻译元素列表（叶子节点）
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        elements_to_translate = []

        for tag in self.BLOCK_TAGS:
            for element in soup.find_all(tag):
                # 只处理没有可翻译子元素的元素（叶子节点）
                has_translatable_child = False
                for child in element.children:
                    if child.name in self.BLOCK_TAGS and child.get_text().strip():
                        has_translatable_child = True
                        break
                if not has_translatable_child and element.get_text().strip():
                    elements_to_translate.append(element)

        # 去重
        seen = set()
        unique_elements = []
        for el in elements_to_translate:
            el_id = id(el)
            if el_id not in seen:
                seen.add(el_id)
                unique_elements.append(el)

        return unique_elements

    def _extract_text(self, elements: List[BeautifulSoup]) -> str:
        """
        提取所有元素的文本

        Args:
            elements: 元素列表

        Returns:
            合并的文本（用双换行符分隔）
        """
        texts = [el.get_text().strip() for el in elements if el.get_text().strip()]
        return '\n\n'.join(texts)

    def _translate_text(self, text: str, log_callback: Optional[Callable] = None) -> List[str]:
        """
        翻译文本（分块后翻译）

        Args:
            text: 待翻译文本
            log_callback: 日志回调

        Returns:
            翻译后的段落列表
        """
        if not text.strip():
            return []

        # 分块
        chunks = self.chunker.chunk_text(text)

        if log_callback:
            log_callback(f"分块完成，共 {len(chunks)} 个块")

        # 翻译所有块
        translated_paragraphs = []
        for i, chunk in enumerate(chunks):
            chunk_text = chunk.get('main_content', '') if isinstance(chunk, dict) else str(chunk)
            if not chunk_text.strip():
                continue

            if log_callback:
                log_callback(f"翻译块 {i+1}/{len(chunks)}...")

            result = self.api_client.translate(
                text=chunk_text,
                lang_in=self.config.lang_in,
                lang_out=self.config.lang_out,
                log_callback=log_callback
            )

            if result.success:
                # 按双换行符分割翻译结果
                parts = result.translated_text.split('\n\n')
                translated_paragraphs.extend(parts)
            else:
                if log_callback:
                    log_callback(f"翻译失败: {result.error}")
                # 保留原文作为回退
                translated_paragraphs.append(chunk_text)

        return translated_paragraphs

    def translate_mono(self, html_content: str, log_callback: Optional[Callable] = None) -> str:
        """
        单语翻译：只保留译文，保持 HTML 结构

        Args:
            html_content: HTML 内容
            log_callback: 日志回调

        Returns:
            翻译后的 HTML（只含译文）
        """
        if log_callback:
            log_callback("执行单语翻译模式...")

        soup = BeautifulSoup(html_content, 'html.parser')

        # 从 soup 中直接提取可翻译元素（而不是从 _parse_elements 创建的新 soup）
        elements = []
        for tag in self.BLOCK_TAGS:
            for element in soup.find_all(tag):
                # 只处理没有可翻译子元素的元素（叶子节点）
                has_translatable_child = False
                for child in element.children:
                    if child.name in self.BLOCK_TAGS and child.get_text().strip():
                        has_translatable_child = True
                        break
                if not has_translatable_child and element.get_text().strip():
                    elements.append(element)

        # 去重
        seen = set()
        unique_elements = []
        for el in elements:
            el_id = id(el)
            if el_id not in seen:
                seen.add(el_id)
                unique_elements.append(el)
        elements = unique_elements

        if not elements:
            if log_callback:
                log_callback("未找到可翻译的元素")
            return html_content

        if log_callback:
            log_callback(f"找到 {len(elements)} 个可翻译元素")

        # 提取文本
        all_text = self._extract_text(elements)

        # 翻译
        translated_paragraphs = self._translate_text(all_text, log_callback)

        if log_callback:
            log_callback(f"翻译完成，共 {len(translated_paragraphs)} 个段落")

        # 应用翻译（单语模式）
        para_idx = 0
        for element in elements:
            if para_idx < len(translated_paragraphs):
                # 保留元素的属性，只替换文本内容
                element.clear()
                element.string = translated_paragraphs[para_idx]
                para_idx += 1

        return str(soup)

    def translate_dual(self, html_content: str, log_callback: Optional[Callable] = None) -> str:
        """
        双语翻译：原文和译文依次显示

        Args:
            html_content: HTML 内容
            log_callback: 日志回调

        Returns:
            翻译后的 HTML（原文+译文）
        """
        if log_callback:
            log_callback("执行双语翻译模式...")

        soup = BeautifulSoup(html_content, 'html.parser')
        elements = self._parse_elements(html_content)

        if not elements:
            if log_callback:
                log_callback("未找到可翻译的元素")
            return html_content

        if log_callback:
            log_callback(f"找到 {len(elements)} 个可翻译元素")

        # 提取文本
        all_text = self._extract_text(elements)

        # 翻译
        translated_paragraphs = self._translate_text(all_text, log_callback)

        if log_callback:
            log_callback(f"翻译完成，共 {len(translated_paragraphs)} 个段落")

        # 应用翻译（双语模式）
        new_soup = BeautifulSoup('', 'html.parser')

        # 创建双语容器样式
        container_style = 'margin-bottom: 1em; padding: 0.5em; border-left: 3px solid #ccc;'
        original_style = 'color: #666; font-size: 0.9em; margin-bottom: 0.5em;'
        translated_style = 'color: #333;'

        para_idx = 0
        for element in elements:
            original_text = element.get_text().strip()
            if original_text and para_idx < len(translated_paragraphs):
                # 创建双语容器
                bilingual_div = soup.new_tag('div')
                bilingual_div['style'] = container_style

                # 原文段落
                original_p = soup.new_tag('p')
                original_p['style'] = original_style
                original_p.append(f'[{self.config.lang_in}] {original_text}')
                bilingual_div.append(original_p)

                # 译文段落
                translated_p = soup.new_tag('p')
                translated_p['style'] = translated_style
                translated_p.append(f'[{self.config.lang_out}] {translated_paragraphs[para_idx]}')
                bilingual_div.append(translated_p)

                new_soup.append(bilingual_div)
                para_idx += 1

        return str(new_soup)

    def translate(self, html_content: str, mode: str = 'mono', log_callback: Optional[Callable] = None) -> str:
        """
        通用翻译方法

        Args:
            html_content: HTML 内容
            mode: 翻译模式 ('mono' | 'dual')
            log_callback: 日志回调

        Returns:
            翻译后的 HTML
        """
        if mode == 'dual':
            return self.translate_dual(html_content, log_callback)
        else:
            return self.translate_mono(html_content, log_callback)