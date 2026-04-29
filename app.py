#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Flask翻译应用主文件

支持多格式文档翻译：PDF、EPUB、Markdown
多翻译引擎支持：OpenAI、Ollama、BabelDOC
"""

import os
import logging
from flask import Flask, render_template, request, jsonify, Response, send_file, abort
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_FILE_SIZE', 52428800))  # 50MB

# 注册蓝图
try:
    from routes.api_routes import api_bp
    from routes.pdf_routes import pdf_bp

    # 注册API蓝图
    app.register_blueprint(api_bp, url_prefix='/api')

    # 注册PDF蓝图
    app.register_blueprint(pdf_bp)

    logger.info("蓝图注册成功")
except ImportError as e:
    logger.warning(f"蓝图模块导入失败: {e}")

# 注册管理蓝图
try:
    from admin_routes import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    logger.info("管理蓝图注册成功")
except ImportError as e:
    logger.warning(f"管理蓝图导入失败: {e}")

# 缓存控制中间件
@app.after_request
def apply_cache_control(response):
    """应用缓存控制头，防止浏览器缓存"""
    if (response.mimetype in ['text/html', 'application/json'] or
        '/api/' in request.path):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Surrogate-Control'] = 'no-store'
    return response

# 主页路由
@app.route('/')
def index():
    """应用主页 - 统一翻译页面"""
    return render_template('unified_translate.html')

# 翻译结果页面
@app.route('/results')
def results_page():
    """翻译结果列表页面"""
    return render_template('results.html')

# 静态文件服务（如果需要）
@app.route('/static/<path:filename>')
def static_files(filename):
    """提供静态文件服务"""
    return send_from_directory('static', filename)

# 健康检查端点
@app.route('/health')
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'message': 'Flask翻译应用运行正常',
        'version': '2.0.0'
    })

# 错误处理
@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'API端点不存在'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"内部服务器错误: {error}")
    if request.path.startswith('/api/'):
        return jsonify({'error': '内部服务器错误'}), 500
    return render_template('500.html'), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    """文件过大错误处理"""
    logger.warning(f"文件过大: {error}")
    if request.path.startswith('/api/'):
        return jsonify({'error': '文件大小超出限制'}), 413
    return render_template('413.html', max_size=app.config['MAX_CONTENT_LENGTH']), 413

# 初始化函数
def init_app():
    """初始化应用"""
    logger.info("初始化Flask翻译应用...")

    # 创建必要的目录
    directories = ['uploads', 'results', 'data', 'data/keys']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"目录已创建: {directory}")

    # 创建.gitkeep文件
    for directory in ['uploads', 'results']:
        gitkeep_path = os.path.join(directory, '.gitkeep')
        if not os.path.exists(gitkeep_path):
            open(gitkeep_path, 'w').close()

    logger.info("应用初始化完成")

# 主函数
def main():
    """主函数"""
    init_app()

    # 获取配置
    host = os.getenv('APP_HOST', '127.0.0.1')
    port = int(os.getenv('APP_PORT', 5001))
    debug = os.getenv('FLASK_DEBUG', '0') == '1'

    # 启动应用
    logger.info(f"启动Flask应用...")
    logger.info(f"访问地址: http://{host}:{port}")
    logger.info(f"调试模式: {'开启' if debug else '关闭'}")

    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    main()
