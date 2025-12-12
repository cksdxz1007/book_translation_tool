#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本处理工具

提供文本分块、清洗、格式化等功能
"""

import re
from typing import List, Tuple, Dict, Any

def split_text_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
    """
    将文本分块

    Args:
        text: 输入文本
        chunk_size: 块大小
        overlap: 重叠大小

    Returns:
        文本块列表
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        # 尝试在句号处分割
        if end < len(text):
            last_period = chunk.rfind('。')
            last_newline = chunk.rfind('\n')
            split_pos = max(last_period, last_newline)

            if split_pos > chunk_size * 0.5:
                chunk = text[start:start + split_pos + 1]
                end = start + split_pos + 1

        chunks.append(chunk)
        start = end - overlap if end - overlap > start else end

    return chunks

def clean_text(text: str) -> str:
    """
    清洗文本

    Args:
        text: 输入文本

    Returns:
        清洗后的文本
    """
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text)
    # 移除首尾空白
    text = text.strip()
    return text

def format_translation_text(original: str, translated: str) -> str:
    """
    格式化翻译文本

    Args:
        original: 原文
        translated: 译文

    Returns:
        格式化的文本
    """
    return f"{translated}\n\n原文: {original}"

def extract_markdown_structure(text: str) -> Dict[str, Any]:
    """
    提取Markdown结构

    Args:
        text: Markdown文本

    Returns:
        结构信息
    """
    headers = re.findall(r'^(#{1,6})\s+(.+)$', text, re.MULTILINE)
    lists = re.findall(r'^\s*[-*+]\s+(.+)$', text, re.MULTILINE)

    return {
        'headers': [{'level': len(h[0]), 'text': h[1]} for h in headers],
        'lists': [item for item in lists],
        'total_lines': len(text.splitlines())
    }
