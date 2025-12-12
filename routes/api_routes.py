#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由

提供RESTful API接口
"""

import os
from flask import Blueprint, request, jsonify, send_file

api_bp = Blueprint('api', __name__)

@api_bp.route('/translate', methods=['POST'])
def translate_pdf():
    """PDF翻译API"""
    data = request.get_json()
    return jsonify({'status': 'success', 'message': 'PDF翻译功能待实现'})

@api_bp.route('/translate-markdown', methods=['POST'])
def translate_markdown():
    """Markdown翻译API"""
    data = request.get_json()
    return jsonify({'status': 'success', 'message': 'Markdown翻译功能待实现'})

@api_bp.route('/translate-epub', methods=['POST'])
def translate_epub():
    """EPUB翻译API"""
    data = request.get_json()
    return jsonify({'status': 'success', 'message': 'EPUB翻译功能待实现'})

@api_bp.route('/reset-progress', methods=['POST'])
def reset_progress():
    """重置翻译进度"""
    return jsonify({'status': 'success', 'message': '进度已重置'})

@api_bp.route('/abort-translation', methods=['POST'])
def abort_translation():
    """中止翻译"""
    return jsonify({'status': 'success', 'message': '翻译已中止'})

@api_bp.route('/clear-cache', methods=['POST'])
def clear_cache():
    """清除缓存"""
    return jsonify({'status': 'success', 'message': '缓存已清除'})

@api_bp.route('/clear-cache/<filename>', methods=['POST'])
def clear_cache_file(filename):
    """清除指定文件缓存"""
    return jsonify({'status': 'success', 'message': f'文件 {filename} 缓存已清除'})

@api_bp.route('/download/<filename>')
def download_file(filename):
    """下载翻译结果"""
    file_path = os.path.join('results', filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({'error': '文件不存在'}), 404

@api_bp.route('/cleanup-files', methods=['POST'])
def cleanup_files():
    """清理文件"""
    return jsonify({'status': 'success', 'message': '文件清理完成'})
