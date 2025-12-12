#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown路由

Markdown翻译页面和文件上传
"""

from flask import Blueprint, render_template, request, redirect, url_for

markdown_bp = Blueprint('markdown', __name__, url_prefix='/markdown')

@markdown_bp.route('/', methods=['GET', 'POST'])
def markdown_index():
    """Markdown翻译页面"""
    if request.method == 'POST':
        # 处理文件上传
        pass
    return render_template('markdown_translate.html')
