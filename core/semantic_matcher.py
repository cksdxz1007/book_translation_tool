#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语义匹配工具

用于匹配原文和译文的对应关系
"""

import difflib
from typing import List, Tuple, Dict, Any

def match_translations(original_texts: List[str], translated_texts: List[str]) -> List[Tuple[str, str]]:
    """
    匹配原文和译文

    Args:
        original_texts: 原文列表
        translated_texts: 译文列表

    Returns:
        匹配的文本对列表
    """
    matches = []

    for orig in original_texts:
        best_match = None
        best_ratio = 0

        for trans in translated_texts:
            ratio = difflib.SequenceMatcher(None, orig, trans).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = trans

        if best_match:
            matches.append((orig, best_match))

    return matches

def calculate_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度

    Args:
        text1: 文本1
        text2: 文本2

    Returns:
        相似度 (0-1)
    """
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def find_best_match(target: str, candidates: List[str]) -> Tuple[str, float]:
    """
    在候选列表中找到最佳匹配

    Args:
        target: 目标文本
        candidates: 候选文本列表

    Returns:
        (最佳匹配文本, 相似度)
    """
    best_match = None
    best_ratio = 0

    for candidate in candidates:
        ratio = calculate_similarity(target, candidate)
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate

    return best_match, best_ratio
