#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF路由

PDF翻译页面和文件上传
"""

from flask import Blueprint, render_template, request, redirect, url_for

pdf_bp = Blueprint('pdf', __name__, url_prefix='/pdf')

@pdf_bp.route('/', methods=['GET', 'POST'])
def pdf_index():
    """PDF翻译页面"""
    if request.method == 'POST':
        # 处理文件上传
        pass
    return render_template('pdf_translate.html')
