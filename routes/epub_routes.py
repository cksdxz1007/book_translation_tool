#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB路由

EPUB翻译页面和文件上传
"""

from flask import Blueprint, render_template, request, redirect, url_for

epub_bp = Blueprint('epub', __name__, url_prefix='/epub')

@epub_bp.route('/', methods=['GET', 'POST'])
def epub_index():
    """EPUB翻译页面"""
    if request.method == 'POST':
        # 处理文件上传
        pass
    return render_template('epub_translate.html')
