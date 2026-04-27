#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF翻译Blueprint路由

独立的PDF翻译页面和文件上传处理
符合Docs/PROJECT_STRUCTURE.md规范
"""

from flask import Blueprint, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename
import os
import logging

logger = logging.getLogger(__name__)

# 创建PDF Blueprint
pdf_bp = Blueprint('pdf', __name__)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@pdf_bp.route('/pdf', methods=['GET', 'POST'])
def pdf_translate():
    """
    PDF翻译页面路由

    GET: 返回PDF翻译页面
    POST: 处理PDF文件上传
    """
    if request.method == 'POST':
        try:
            # 检查是否有文件
            if 'file' not in request.files:
                return jsonify({'error': '没有文件'}), 400

            file = request.files['file']

            # 检查文件名
            if file.filename == '':
                return jsonify({'error': '没有选择文件'}), 400

            # 检查文件类型
            if not allowed_file(file.filename):
                return jsonify({'error': '不支持的文件格式'}), 400

            # 保存文件
            filename = secure_filename(file.filename)
            uploads_dir = 'uploads'
            os.makedirs(uploads_dir, exist_ok=True)

            file_path = os.path.join(uploads_dir, filename)
            file.save(file_path)

            logger.info(f"PDF文件已保存: {file_path}")

            # 返回成功响应
            return jsonify({
                'status': 'success',
                'message': '文件上传成功',
                'filename': filename,
                'file_path': file_path
            })

        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return jsonify({'error': f'文件上传失败: {str(e)}'}), 500

    # GET请求：返回PDF翻译页面（使用统一模板）
    return render_template('unified_translate.html')

@pdf_bp.route('/pdf/health', methods=['GET'])
def pdf_health():
    """PDF模块健康检查"""
    return jsonify({
        'status': 'healthy',
        'module': 'pdf',
        'message': 'PDF翻译模块运行正常'
    })

# Blueprint信息
pdf_bp.info = {
    'name': 'pdf',
    'description': 'PDF翻译Blueprint',
    'version': '1.0.0',
    'routes': [
        {'path': '/pdf', 'methods': ['GET', 'POST'], 'description': 'PDF翻译页面和文件上传'},
        {'path': '/pdf/health', 'methods': ['GET'], 'description': 'PDF模块健康检查'}
    ]
}
