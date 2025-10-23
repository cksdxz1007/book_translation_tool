"""
简单的管理界面路由
"""
import os
from functools import wraps
from flask import Blueprint, render_template_string, request, jsonify, redirect, url_for, session
from config.manager import ConfigManager

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
config_manager = ConfigManager('data/config.db', 'data/keys')

# 从环境变量获取管理员密钥，如果没有设置则使用安全的默认值
ADMIN_ACCESS_KEY = os.getenv('ADMIN_ACCESS_KEY', '9AD43ELSUdAgnpKyCcsNRx/6AOPfjsQ6jE8J3naY5jc=')

def require_admin_auth(f):
    """
    管理员认证装饰器
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查是否已登录
        if session.get('admin_authenticated'):
            return f(*args, **kwargs)

        # 检查URL参数中的密钥
        access_key = request.args.get('key')
        if access_key == ADMIN_ACCESS_KEY:
            session['admin_authenticated'] = True
            return f(*args, **kwargs)

        # 显示登录页面
        return render_template_string("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>管理员登录</title>
            <meta charset="utf-8">
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; max-width: 400px; }
                .login-form { border: 1px solid #ddd; padding: 30px; border-radius: 5px; }
                .form-group { margin-bottom: 20px; }
                label { display: block; margin-bottom: 5px; font-weight: bold; }
                input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }
                .btn { padding: 10px 20px; background-color: #007bff; color: white; border: none; border-radius: 3px; cursor: pointer; }
                .error { color: #dc3545; margin-top: 10px; }
            </style>
        </head>
        <body>
            <h1>🔐 管理员登录</h1>
            <div class="login-form">
                <form method="GET">
                    <div class="form-group">
                        <label for="key">访问密钥:</label>
                        <input type="password" id="key" name="key" placeholder="请输入管理员密钥" required>
                    </div>
                    <button type="submit" class="btn">🔑 登录</button>
                </form>
                {% if error %}
                <div class="error">{{ error }}</div>
                {% endif %}
            </div>
        </body>
        </html>
        """, error=request.args.get('error'))

    return decorated_function

@admin_bp.route('/')
@require_admin_auth
def dashboard():
    """管理首页"""
    services = config_manager.list_services()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>翻译服务管理</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .service { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .service.default { border-color: #007bff; background-color: #f8f9fa; }
            .btn { padding: 8px 16px; margin: 5px; text-decoration: none; border-radius: 3px; }
            .btn-primary { background-color: #007bff; color: white; }
            .btn-success { background-color: #28a745; color: white; }
            .btn-danger { background-color: #dc3545; color: white; }
            .status { padding: 3px 8px; border-radius: 3px; font-size: 12px; }
            .status.success { background-color: #d4edda; color: #155724; }
            .status.failed { background-color: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <h1>🔧 翻译服务管理</h1>
        
        <div style="margin-bottom: 20px;">
            <a href="/admin/add" class="btn btn-primary">➕ 添加新服务</a>
            <a href="/" class="btn">🏠 返回主页</a>
            <a href="/admin/logout" class="btn" style="background-color: #dc3545; color: white;">🚪 退出登录</a>
        </div>
        
        <h2>📋 服务列表 ({{ services|length }} 个)</h2>
        
        {% for service in services %}
        <div class="service {% if service.is_default %}default{% endif %}">
            <h3>
                {{ service.name }}
                {% if service.is_default %}
                    <span class="status success">默认</span>
                {% endif %}
                {% if service.test_status == 'success' %}
                    <span class="status success">✓ 连接正常</span>
                {% elif service.test_status == 'failed' %}
                    <span class="status failed">✗ 连接失败</span>
                {% endif %}
            </h3>
            
            <p><strong>类型:</strong> {{ service.service_type }}</p>
            <p><strong>地址:</strong> {{ service.base_url }}</p>
            <p><strong>模型:</strong> {{ service.model_name }}</p>
            <p><strong>描述:</strong> {{ service.description or '无' }}</p>
            
            <div>
                <a href="/admin/test/{{ service.id }}" class="btn btn-success">🔍 测试连接</a>
                <a href="/admin/edit/{{ service.id }}" class="btn btn-primary">✏️ 编辑</a>
                {% if not service.is_default %}
                    <a href="/admin/set_default/{{ service.id }}" class="btn">⭐ 设为默认</a>
                {% endif %}
            </div>
        </div>
        {% endfor %}
        
        {% if not services %}
        <p>暂无服务配置，<a href="/admin/add">点击添加</a>第一个服务。</p>
        {% endif %}
        
    </body>
    </html>
    """
    
    return render_template_string(html, services=services)

@admin_bp.route('/test/<service_id>')
@require_admin_auth
def test_service(service_id):
    """测试服务连接"""
    try:
        result = config_manager.test_service_connection(service_id)
        
        if result['success']:
            return f"<script>alert('连接测试成功！'); window.location.href='/admin';</script>"
        else:
            return f"<script>alert('连接测试失败: {result.get('error', '未知错误')}'); window.location.href='/admin';</script>"
    except Exception as e:
        return f"<script>alert('测试出错: {str(e)}'); window.location.href='/admin';</script>"

@admin_bp.route('/edit/<service_id>')
@require_admin_auth
def edit_service(service_id):
    """编辑服务页面"""
    try:
        service = config_manager.get_service(service_id)
        if not service:
            return f"<script>alert('服务不存在'); window.location.href='/admin';</script>"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>编辑翻译服务</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; max-width: 600px; }}
                .form-group {{ margin-bottom: 15px; }}
                label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
                input, select, textarea {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px; }}
                .btn {{ padding: 10px 20px; margin: 5px; border: none; border-radius: 3px; cursor: pointer; }}
                .btn-primary {{ background-color: #007bff; color: white; }}
                .btn-secondary {{ background-color: #6c757d; color: white; }}
            </style>
        </head>
        <body>
            <h1>✏️ 编辑翻译服务</h1>
            
            <form method="POST" action="/admin/update/{service_id}">
                <div class="form-group">
                    <label>服务名称:</label>
                    <input type="text" name="name" required value="{service['name']}">
                </div>
                
                <div class="form-group">
                    <label>服务类型:</label>
                    <select name="service_type" required>
                        <option value="openai" {'selected' if service['service_type'] == 'openai' else ''}>OpenAI 兼容</option>
                        <option value="deepseek" {'selected' if service['service_type'] == 'deepseek' else ''}>DeepSeek</option>
                        <option value="ollama" {'selected' if service['service_type'] == 'ollama' else ''}>Ollama 本地</option>
                        <option value="custom" {'selected' if service['service_type'] == 'custom' else ''}>自定义</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>API 地址:</label>
                    <input type="url" name="base_url" required value="{service['base_url']}">
                </div>
                
                <div class="form-group">
                    <label>API 密钥:</label>
                    <input type="password" name="api_key" placeholder="留空保持原密钥不变" value="">
                    <small>当前密钥: {'已设置' if service.get('api_key') else '未设置'}</small>
                </div>
                
                <div class="form-group">
                    <label>模型名称:</label>
                    <input type="text" name="model_name" required value="{service['model_name']}">
                </div>
                
                <div class="form-group">
                    <label>描述:</label>
                    <textarea name="description" rows="3">{service.get('description', '')}</textarea>
                </div>
                
                <div>
                    <button type="submit" class="btn btn-primary">💾 保存</button>
                    <a href="/admin" class="btn btn-secondary">❌ 取消</a>
                </div>
            </form>
        </body>
        </html>
        """
        return html
        
    except Exception as e:
        return f"<script>alert('加载编辑页面失败: {str(e)}'); window.location.href='/admin';</script>"

@admin_bp.route('/update/<service_id>', methods=['POST'])
@require_admin_auth
def update_service(service_id):
    """更新服务"""
    try:
        # 获取现有服务
        existing_service = config_manager.get_service(service_id)
        if not existing_service:
            return f"<script>alert('服务不存在'); window.location.href='/admin';</script>"
        
        # 准备更新数据
        config = {
            'name': request.form['name'],
            'service_type': request.form['service_type'],
            'base_url': request.form['base_url'],
            'model_name': request.form['model_name'],
            'description': request.form.get('description', '')
        }
        
        # 处理API密钥 - 如果为空则保持原有密钥
        new_api_key = request.form.get('api_key', '').strip()
        if new_api_key:
            config['api_key'] = new_api_key
        else:
            config['api_key'] = existing_service.get('api_key', '')
        
        # 更新服务
        success = config_manager.update_service(service_id, config)
        
        if success:
            return f"<script>alert('服务更新成功！'); window.location.href='/admin';</script>"
        else:
            return f"<script>alert('服务更新失败'); window.location.href='/admin';</script>"
        
    except Exception as e:
        return f"<script>alert('更新失败: {str(e)}'); window.history.back();</script>"

@admin_bp.route('/set_default/<service_id>')
@require_admin_auth
def set_default(service_id):
    """设置默认服务"""
    config_manager.set_default_service(service_id)
    return redirect('/admin')

@admin_bp.route('/add')
@require_admin_auth
def add_service():
    """添加服务页面"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>添加翻译服务</title>
        <meta charset="utf-8">
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; max-width: 600px; }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select, textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px; }
            .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 3px; cursor: pointer; }
            .btn-primary { background-color: #007bff; color: white; }
            .btn-secondary { background-color: #6c757d; color: white; }
        </style>
    </head>
    <body>
        <h1>➕ 添加翻译服务</h1>
        
        <form method="POST" action="/admin/create">
            <div class="form-group">
                <label>服务名称:</label>
                <input type="text" name="name" required placeholder="例如: GPT-4 翻译服务">
            </div>
            
            <div class="form-group">
                <label>服务类型:</label>
                <select name="service_type" required>
                    <option value="openai">OpenAI 兼容</option>
                    <option value="ollama">Ollama 本地</option>
                    <option value="custom">自定义</option>
                </select>
            </div>
            
            <div class="form-group">
                <label>API 地址:</label>
                <input type="url" name="base_url" required placeholder="https://api.openai.com/v1">
            </div>
            
            <div class="form-group">
                <label>API 密钥:</label>
                <input type="password" name="api_key" placeholder="留空表示无需密钥">
            </div>
            
            <div class="form-group">
                <label>模型名称:</label>
                <input type="text" name="model_name" required placeholder="gpt-3.5-turbo">
            </div>
            
            <div class="form-group">
                <label>描述:</label>
                <textarea name="description" rows="3" placeholder="服务描述（可选）"></textarea>
            </div>
            
            <div>
                <button type="submit" class="btn btn-primary">💾 保存</button>
                <a href="/admin" class="btn btn-secondary">❌ 取消</a>
            </div>
        </form>
    </body>
    </html>
    """
    return render_template_string(html)

@admin_bp.route('/create', methods=['POST'])
@require_admin_auth
def create_service():
    """创建服务"""
    try:
        config = {
            'name': request.form['name'],
            'service_type': request.form['service_type'],
            'base_url': request.form['base_url'],
            'api_key': request.form.get('api_key', ''),
            'model_name': request.form['model_name'],
            'description': request.form.get('description', '')
        }

        service_id = config_manager.create_service(config)
        return f"<script>alert('服务创建成功！ID: {service_id}'); window.location.href='/admin';</script>"

    except Exception as e:
        return f"<script>alert('创建失败: {str(e)}'); window.history.back();</script>"

@admin_bp.route('/logout')
def logout():
    """退出登录"""
    session.pop('admin_authenticated', None)
    return redirect('/admin')
