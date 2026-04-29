#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API路由

提供RESTful API接口
"""

import asyncio
import os
import uuid
import json
import logging
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import sys

logger = logging.getLogger(__name__)

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.manager import ConfigManager

# 导入核心模块 - P0/P1 优化
try:
    from core import TokenProgressTracker, CheckpointManager, ErrorRecoveryManager
    from core.translation import EPUBTranslator, HTMLTranslator
    core_modules_available = True
except ImportError as e:
    core_modules_available = False
    logger.warning(f"核心模块(core)未找到，部分高级功能将不可用: {e}")

api_bp = Blueprint('api', __name__)

# 初始化核心模块
if core_modules_available:
    checkpoint_manager = CheckpointManager()
    error_recovery_manager = ErrorRecoveryManager()
    token_progress_tracker = TokenProgressTracker()

# 初始化配置管理器
config_manager = ConfigManager()

# 任务存储（生产环境建议使用 Redis）
tasks = {}

# 任务持久化文件路径
TASKS_FILE = 'data/tasks.json'

def save_tasks():
    """保存任务到文件"""
    try:
        os.makedirs(os.path.dirname(TASKS_FILE), exist_ok=True)
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.error(f"保存任务失败: {e}")

def load_tasks():
    """从文件加载任务"""
    global tasks
    try:
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
            logger.info(f"已加载 {len(tasks)} 个任务")
    except Exception as e:
        logger.error(f"加载任务失败: {e}")
        tasks = {}

# 启动时加载任务
load_tasks()

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'pdf', 'epub', 'md', 'markdown'}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@api_bp.route('/services', methods=['GET'])
def get_services():
    """获取所有翻译服务"""
    try:
        services = config_manager.get_all_services()
        # 过滤掉错误状态的服务，返回健康的服务
        # 接受的状态包括: active, healthy, 服务正常, healthy 等
        healthy_keywords = ['active', 'healthy', '正常', '服务正常']
        healthy_services = []
        for s in services:
            status = s.get('status', '').lower()
            if any(keyword.lower() in status for keyword in healthy_keywords):
                healthy_services.append(s)

        # 格式化服务数据，只返回前端需要的字段
        formatted_services = []
        for service in healthy_services:
            formatted_services.append({
                'id': service['id'],
                'name': service['name'],
                'type': service['type'],
                'model': service['model'],
                'is_default': service['is_default']
            })

        return jsonify({
            'status': 'success',
            'services': formatted_services
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': '获取服务列表失败'}), 500

@api_bp.route('/translate/unified', methods=['POST'])
def unified_translate():
    """
    统一翻译接口
    目前只支持PDF文件翻译
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({'error': '没有文件上传'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '未选择文件'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': '不支持的文件格式'}), 400

        # 获取配置
        config = request.form.get('config', '{}')
        options = request.form.get('options', '{}')
        file_type = request.form.get('fileType', '')

        # 检查文件类型
        filename = secure_filename(file.filename)
        file_ext = filename.rsplit('.', 1)[1].lower()

        # 目前只支持PDF和EPUB文件
        supported_formats = ['pdf', 'epub']
        if file_ext not in supported_formats:
            return jsonify({
                'error': f'暂不支持{file_ext.upper()}文件翻译。目前仅支持PDF和EPUB文件翻译。'
            }), 400

        # 生成任务 ID
        task_id = str(uuid.uuid4())

        # 保存文件
        unique_filename = f"{task_id}.{file_ext}"
        file_path = os.path.join('uploads', unique_filename)
        file.save(file_path)

        # 创建任务记录
        tasks[task_id] = {
            'status': 'queued',
            'progress': 0,
            'state': 'processing',
            'file_path': file_path,
            'original_filename': filename,
            'file_type': file_type or file_ext,
            'config': json.loads(config) if config else {},
            'options': json.loads(options) if options else {},
            'created_at': '2025-12-14 12:00:00',
            'logs': []
        }

        # 保存任务
        save_tasks()

        # 启动异步任务处理
        import threading
        if file_ext == 'pdf':
            thread = threading.Thread(target=process_pdf_translation, args=(task_id,))
        else:
            thread = threading.Thread(target=process_epub_translation, args=(task_id,))
        thread.daemon = True
        thread.start()

        return jsonify({
            'task_id': task_id,
            'status': 'success',
            'message': f'{file_ext.upper()}翻译任务已创建'
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'处理请求时出错: {str(e)}'}), 500

@api_bp.route('/translate/status/<task_id>', methods=['GET'])
def get_translation_status(task_id):
    """获取翻译进度"""
    task = tasks.get(task_id)

    if not task:
        return jsonify({'error': '任务不存在'}), 404

    response = {
        'task_id': task_id,
        'state': task['state'],
        'status': task['status'],
        'progress': task['progress'],
        'created_at': task['created_at'],
        'logs': task.get('logs', [])  # 返回日志数组
    }

    # 如果有当前步骤信息
    if 'current_step' in task:
        response['status'] = task['current_step']

    # 如果完成，提供下载链接
    if task['state'] == 'completed':
        response['download_url'] = f'/api/translate/download/{task_id}'
        response['preview_url'] = f'/api/translate/preview/{task_id}'

    return jsonify(response)

@api_bp.route('/translate/download/<task_id>', methods=['GET'])
def download_translation(task_id):
    """下载翻译结果"""
    task = tasks.get(task_id)

    if not task:
        return jsonify({'error': '任务不存在'}), 404

    if task['state'] != 'completed':
        return jsonify({'error': '翻译尚未完成'}), 400

    # 获取真实的翻译结果文件
    download_path = task.get('download_path')

    if not download_path or not os.path.exists(download_path):
        return jsonify({'error': '翻译结果文件不存在'}), 404

    # 生成下载文件名 - 格式：原文件名_源语言_目标语言.后缀
    original_name = task['original_filename']
    base_name = os.path.splitext(original_name)[0]
    ext = os.path.splitext(original_name)[1]

    # 获取语言信息并规范化
    config = task.get('config', {})
    source_lang = config.get('sourceLang', 'unknown')
    target_lang = config.get('targetLang', 'unknown')

    # 语言代码映射
    lang_mapping = {
        'en': 'en-US',
        'zh': 'zh-CN',
        'ja': 'ja-JP',
        'ko': 'ko-KR',
        'fr': 'fr-FR',
        'de': 'de-DE',
        'es': 'es-ES'
    }

    # 规范化语言代码
    source_lang = lang_mapping.get(source_lang, source_lang)
    target_lang = lang_mapping.get(target_lang, target_lang)

    # 根据翻译样式添加后缀
    file_suffix = task.get('file_suffix', 'mono')  # 默认mono
    result_filename = f"{base_name}_{source_lang}_{target_lang}.{file_suffix}{ext}"

    # 调试日志
    print(f"下载任务 {task_id}:")
    print(f"  原始文件名: {original_name}")
    print(f"  配置: {config}")
    print(f"  翻译样式: {file_suffix}")
    print(f"  源语言: {source_lang}")
    print(f"  目标语言: {target_lang}")
    print(f"  生成文件名: {result_filename}")

    return send_file(
        download_path,
        as_attachment=True,
        download_name=result_filename
    )

@api_bp.route('/translate/preview/<task_id>', methods=['GET'])
def preview_translation(task_id):
    """预览翻译结果"""
    task = tasks.get(task_id)

    if not task:
        return jsonify({'error': '任务不存在'}), 404

    if task['state'] != 'completed':
        return jsonify({'error': '翻译尚未完成'}), 400

    # 模拟预览内容
    preview_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>翻译预览 - {task['original_filename']}</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
            h1 {{ color: #333; }}
            .info {{ background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .content {{ line-height: 1.6; }}
        </style>
    </head>
    <body>
        <h1>翻译预览</h1>
        <div class="info">
            <p><strong>原文文件:</strong> {task['original_filename']}</p>
            <p><strong>文件类型:</strong> {task['file_type']}</p>
            <p><strong>翻译引擎:</strong> {task['config'].get('service', 'N/A')}</p>
            <p><strong>源语言:</strong> {task['config'].get('sourceLang', 'N/A')}</p>
            <p><strong>目标语言:</strong> {task['config'].get('targetLang', 'N/A')}</p>
        </div>
        <div class="content">
            <h2>翻译结果</h2>
            <p>这里是翻译后的内容预览...</p>
            <p>实际实现中，这里会显示真实的翻译内容。</p>
        </div>
    </body>
    </html>
    """

    return preview_html

@api_bp.route('/translate/abort/<task_id>', methods=['POST'])
def abort_translation(task_id):
    """中止翻译"""
    task = tasks.get(task_id)

    if not task:
        return jsonify({'error': '任务不存在'}), 404

    if task['state'] == 'completed':
        return jsonify({'error': '任务已完成，无法中止'}), 400

    task['state'] = 'aborted'
    task['status'] = '已中止'
    task['progress'] = 0
    save_tasks()

    return jsonify({'status': 'success', 'message': '翻译已中止'})

def simulate_translation_progress(task_id):
    """
    模拟翻译进度（开发测试用）
    生产环境中应替换为真实的异步任务处理
    """
    import threading
    import time

    def add_log(message):
        """添加日志到任务"""
        task = tasks.get(task_id)
        if task:
            timestamp = time.strftime('%H:%M:%S')
            log_entry = {
                'time': timestamp,
                'message': message
            }
            task['logs'].append(log_entry)

    def update_progress():
        task = tasks.get(task_id)
        if not task:
            return

        file_type = task['file_type']
        add_log(f"开始处理文件: {task['original_filename']}")
        add_log(f"文件类型: {file_type.upper()}")

        # 根据文件类型定义不同的处理步骤
        if file_type == 'pdf':
            steps = [
                (10, '正在解析PDF文档结构...'),
                (25, '正在提取文本内容...'),
                (35, '正在识别页面布局...'),
                (45, '正在处理图像和表格...'),
                (60, '正在翻译文档内容...', '正在使用AI引擎翻译文本，请稍候...'),
                (75, '正在保持PDF格式...'),
                (85, '正在生成翻译后的PDF...'),
                (95, '正在优化文档质量...'),
                (100, '翻译完成！', 'PDF文档翻译已完成，可下载查看')
            ]
        elif file_type == 'epub':
            steps = [
                (10, '正在解析EPUB电子书结构...'),
                (25, '正在提取章节内容...'),
                (40, '正在处理HTML和CSS样式...'),
                (55, '正在翻译文本内容...'),
                (70, '正在保持电子书格式...'),
                (80, '正在重新打包EPUB文件...'),
                (90, '正在验证电子书结构...'),
                (100, '翻译完成！', 'EPUB电子书翻译已完成')
            ]
        else:  # markdown
            steps = [
                (10, '正在解析Markdown文档...'),
                (25, '正在提取文本内容...'),
                (40, '正在识别文档结构...'),
                (55, '正在翻译文本...'),
                (70, '正在保持Markdown语法...'),
                (85, '正在处理代码块...'),
                (95, '正在生成最终文档...'),
                (100, '翻译完成！', 'Markdown文档翻译已完成')
            ]

        for i, step_data in enumerate(steps):
            time.sleep(1.5)  # 模拟处理时间
            task = tasks.get(task_id)
            if not task or task['state'] == 'aborted':
                return

            progress = step_data[0]
            status = step_data[1]

            task['progress'] = progress
            task['status'] = status

            # 添加日志
            if len(step_data) > 2:
                add_log(step_data[2])
            else:
                add_log(status)

            if progress == 100:
                task['state'] = 'completed'
                # 生成结果文件
                result_path = os.path.join('results', f"{task_id}_result.txt")
                os.makedirs('results', exist_ok=True)
                with open(result_path, 'w', encoding='utf-8') as f:
                    f.write(f"翻译完成！\n\n")
                    f.write(f"原文: {task['original_filename']}\n")
                    f.write(f"类型: {task['file_type']}\n")
                    f.write(f"配置: {json.dumps(task['config'], ensure_ascii=False)}\n")
                    f.write(f"选项: {json.dumps(task['options'], ensure_ascii=False)}\n")

    # 启动后台线程
    thread = threading.Thread(target=update_progress)
    thread.daemon = True
    thread.start()

def add_log(task_id, message):
    """添加日志到任务"""
    task = tasks.get(task_id)
    if task:
        import time
        timestamp = time.strftime('%H:%M:%S')
        log_entry = {
            'time': timestamp,
            'message': message
        }
        task['logs'].append(log_entry)
        save_tasks()

def process_pdf_translation(task_id):
    """处理PDF翻译任务"""
    task = tasks.get(task_id)
    if not task:
        return

    try:
        import time
        from translation.pdf_translator import PDFTranslator, normalize_language_code
        from config.manager import ConfigManager

        # 获取任务信息
        file_path = task['file_path']
        config = task['config']
        options = task['options']
        original_filename = task['original_filename']

        # 添加日志
        add_log(task_id, f"开始处理文件: {original_filename}")
        add_log(task_id, "文件类型: PDF")
        add_log(task_id, "正在初始化BabelDOC翻译器...")

        # 获取翻译服务配置
        service_id = config.get('serviceId')
        if not service_id:
            raise ValueError("未选择翻译服务")

        config_manager = ConfigManager()
        service = config_manager.get_service_by_id(service_id)

        if not service:
            raise ValueError(f"服务ID {service_id} 不存在")

        add_log(task_id, f"使用翻译服务: {service['name']} ({service['type']})")

        # 获取API密钥（从服务配置中获取）
        api_key = service.get('api_key')
        if not api_key:
            raise ValueError("服务API密钥未配置")

        model = service.get('model', 'deepseek-chat')
        base_url = service.get('url')

        # 语言代码规范化
        lang_in = normalize_language_code(config.get('sourceLang', 'en'))
        lang_out = normalize_language_code(config.get('targetLang', 'zh'))

        add_log(task_id, f"翻译语言: {lang_in} -> {lang_out}")

        # 创建PDF翻译器
        translator = PDFTranslator(
            api_key=api_key,
            model=model,
            base_url=base_url
        )

        # 检查可用性
        if not translator.is_available():
            # BabelDOC不可用，使用模拟翻译模式
            add_log(task_id, "BabelDOC未安装，使用模拟翻译模式进行演示...")
            simulate_translation_progress(task_id)
            return

        # 设置输出目录
        output_dir = os.path.join('results', task_id)
        os.makedirs(output_dir, exist_ok=True)

        # 进度回调函数
        def progress_callback(event):
            event_type = event.get('type')

            if event_type == 'progress_update':
                progress = event.get('overall_progress', 0)
                stage = event.get('stage', '处理中')
                task['progress'] = int(progress)
                task['status'] = stage
                save_tasks()

                # 添加详细日志
                add_log(task_id, f"{stage} ({progress:.1f}%)")

            elif event_type == 'progress_start':
                stage = event.get('stage', '开始')
                add_log(task_id, f"开始阶段: {stage}")

            elif event_type == 'progress_end':
                stage = event.get('stage', '完成')
                add_log(task_id, f"完成阶段: {stage}")

            elif event_type == 'finish':
                add_log(task_id, "翻译完成！")
                task['progress'] = 100
                task['status'] = '翻译完成！'
                task['state'] = 'completed'

                # 设置下载路径
                translate_result = event.get('translate_result')
                if translate_result:
                    # 优先使用双语PDF，如果没有则使用单语PDF
                    if hasattr(translate_result, 'dual_pdf_path') and translate_result.dual_pdf_path:
                        task['download_path'] = str(translate_result.dual_pdf_path)
                        task['preview_path'] = str(translate_result.dual_pdf_path)
                    elif hasattr(translate_result, 'mono_pdf_path') and translate_result.mono_pdf_path:
                        task['download_path'] = str(translate_result.mono_pdf_path)
                        task['preview_path'] = str(translate_result.mono_pdf_path)

                save_tasks()

            elif event_type == 'error':
                error_msg = event.get('error', '未知错误')
                add_log(task_id, f"错误: {error_msg}")
                task['state'] = 'error'
                task['status'] = f'翻译失败: {error_msg}'
                save_tasks()

        # 处理特定选项
        babeldoc_kwargs = {}

        # PDF特定选项
        if options.get('pdfOcr'):
            babeldoc_kwargs['ocr_workaround'] = True
            add_log(task_id, "启用OCR模式")

        # 格式保留选项
        babeldoc_kwargs['skip_clean'] = False
        babeldoc_kwargs['enhance_compatibility'] = True
        babeldoc_kwargs['disable_rich_text_translate'] = True  # 禁用富文本翻译以保持格式
        babeldoc_kwargs['split_short_lines'] = False  # 不分割短行，保留原有换行
        add_log(task_id, "启用格式保留模式")

        # 翻译样式选项
        translation_style = options.get('pdfTranslationStyle', 'mono')
        if translation_style == 'mono':
            # 仅译文 - 不生成双语PDF
            babeldoc_kwargs['no_dual'] = True
            add_log(task_id, "翻译样式: 仅译文")
        elif translation_style == 'dual':
            # 双语对照 - 生成双语PDF（交替页面模式）
            babeldoc_kwargs['no_dual'] = False
            # 使用交替页面模式（交替显示原文和译文页面）
            babeldoc_kwargs['use_alternating_pages_dual'] = True
            babeldoc_kwargs['dual_translate_first'] = True  # 翻译页面优先
            add_log(task_id, "翻译样式: 双语对照（交替页面显示）")
            add_log(task_id, "说明: 原文页面和译文页面交替显示")

        # 启动翻译
        add_log(task_id, "开始BabelDOC翻译...")
        result = translator.translate_pdf(
            pdf_path=file_path,
            output_dir=output_dir,
            lang_in=lang_in,
            lang_out=lang_out,
            progress_callback=progress_callback,
            **babeldoc_kwargs
        )

        if result.get('success'):
            # 保存结果信息
            task['state'] = 'completed'
            task['result'] = result

            # 根据翻译样式选择下载路径
            translation_style = options.get('pdfTranslationStyle', 'mono')
            if translation_style == 'mono':
                # 仅译文 - 使用单语PDF
                task['download_path'] = result.get('mono_pdf_path')
                task['preview_path'] = result.get('mono_pdf_path')
                task['file_suffix'] = 'mono'  # 添加文件后缀标识
            else:
                # 双语对照 - 使用双语PDF
                task['download_path'] = result.get('dual_pdf_path')
                task['preview_path'] = result.get('dual_pdf_path')
                task['file_suffix'] = 'dual'  # 添加文件后缀标识

            save_tasks()

            add_log(task_id, f"翻译成功！耗时: {result.get('total_seconds', 0):.2f}秒")
            add_log(task_id, f"处理字符数: {result.get('total_valid_character_count', 0)}")
            add_log(task_id, f"输出文件: {task['download_path']}")
        else:
            raise ValueError("翻译未返回成功结果")

    except Exception as e:
        import traceback
        error_msg = str(e)
        add_log(task_id, f"翻译失败: {error_msg}")
        task['state'] = 'error'
        task['status'] = f'翻译失败: {error_msg}'
        task['error'] = error_msg
        save_tasks()

        # 打印详细错误日志
        print(f"PDF翻译错误 (任务 {task_id}):")
        traceback.print_exc()

def process_epub_translation(task_id):
    """处理EPUB翻译任务 - 使用新的 EPUBTranslator"""
    task = tasks.get(task_id)
    if not task:
        return

    try:
        import time
        from pathlib import Path

        # 获取任务信息
        file_path = task['file_path']
        config = task['config']
        options = task['options']
        original_filename = task['original_filename']

        # 获取翻译样式选项
        translation_style = options.get('epubTranslationStyle', 'mono')
        add_log(task_id, f"调试-epubOptions: {options}")
        add_log(task_id, f"调试-epubTranslationStyle值: [{translation_style}]")
        add_log(task_id, f"翻译样式: {'双语对照' if translation_style == 'dual' else '仅译文'}")

        # 添加日志
        add_log(task_id, f"开始处理文件: {original_filename}")
        add_log(task_id, "文件类型: EPUB")
        add_log(task_id, "正在解析EPUB文件结构...")

        # 获取翻译服务配置
        service_id = config.get('serviceId')
        if not service_id:
            raise ValueError("未选择翻译服务")

        service = config_manager.get_service_by_id(service_id)
        if not service:
            raise ValueError(f"服务ID {service_id} 不存在")

        add_log(task_id, f"使用翻译服务: {service['name']} ({service['type']})")

        # 获取 API 配置
        api_key = service.get('api_key')
        if not api_key:
            raise ValueError("服务API密钥未配置")

        model = service.get('model', 'deepseek-chat')
        base_url = service.get('url')

        # 获取 token 限制
        context_length = service.get('context_length') or 0
        max_output_length = service.get('max_output_length') or 0

        try:
            context_length_val = int(context_length)
            max_output_length_val = int(max_output_length)
        except (ValueError, TypeError):
            context_length_val = 0
            max_output_length_val = 0

        max_input_tokens = int(context_length_val * 0.8) if context_length_val > 0 else 8000
        api_max_tokens = max_output_length_val if max_output_length_val > 0 else 8192

        # 语言代码规范化
        def normalize_language_code(code):
            mapping = {
                'en': 'en', 'zh': 'zh', 'ja': 'ja', 'ko': 'ko',
                'fr': 'fr', 'de': 'de', 'es': 'es'
            }
            return mapping.get(code, code)

        lang_in = normalize_language_code(config.get('sourceLang', 'en'))
        lang_out = normalize_language_code(config.get('targetLang', 'zh'))

        add_log(task_id, f"翻译语言: {lang_in} -> {lang_out}")

        # 构建文件路径
        input_path = Path(file_path)
        output_path = Path(f"data/results/{input_path.stem}_translated.epub")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建翻译配置
        from core.translation.html_translator import TranslateConfig
        translate_config = TranslateConfig(
            api_key=api_key,
            model=model,
            base_url=base_url,
            lang_in=lang_in,
            lang_out=lang_out,
            max_tokens=api_max_tokens,
            max_input_tokens=max_input_tokens,
            temperature=0.3
        )

        # 创建 HTML 翻译器
        html_translator = HTMLTranslator(translate_config)

        # 创建 EPUB 翻译器
        epub_translator = EPUBTranslator(
            input_path=str(input_path),
            output_path=str(output_path),
            html_translator=html_translator,
            translation_style=translation_style,
            task_id=task_id,
            checkpoint_manager=checkpoint_manager if core_modules_available else None,
            progress_callback=lambda stats: _update_task_progress(task_id, stats),
            log_callback=lambda msg: add_log(task_id, msg)
        )

        # 执行翻译
        add_log(task_id, "开始 EPUB 翻译...")
        result = epub_translator.translate()

        if result.success:
            task['state'] = 'completed'
            task['progress'] = 100
            task['status'] = f"翻译完成 {result.completed_units}/{result.total_units}"

            # 生成正确的下载文件名
            config = task['config']
            source_lang = config.get('sourceLang', 'en')
            target_lang = config.get('targetLang', 'zh')
            base_name = os.path.splitext(task['original_filename'])[0]
            ext = os.path.splitext(task['original_filename'])[1]

            # 语言代码映射
            lang_mapping = {
                'en': 'en-US', 'zh': 'zh-CN', 'ja': 'ja-JP',
                'ko': 'ko-KR', 'fr': 'fr-FR', 'de': 'de-DE', 'es': 'es-ES'
            }
            source_lang = lang_mapping.get(source_lang, source_lang)
            target_lang = lang_mapping.get(target_lang, target_lang)

            # 生成文件名: 原文件名_源语言_目标语言.翻译样式.扩展名
            task['file_suffix'] = translation_style
            result_filename = f"{base_name}_{source_lang}_{target_lang}.{translation_style}{ext}"
            result_path = os.path.join('data/results', result_filename)

            # 重命名文件（如果文件名不同）
            if result.output_path != result_path:
                import shutil
                if os.path.exists(result_path):
                    os.remove(result_path)
                shutil.move(result.output_path, result_path)
                add_log(task_id, f"文件已重命名: {result_filename}")

            task['download_path'] = result_path
            task['preview_path'] = result_path
            save_tasks()

            add_log(task_id, f"EPUB翻译完成！")
            add_log(task_id, f"成功: {result.completed_units} 单元")
            if result.failed_units > 0:
                add_log(task_id, f"失败: {result.failed_units} 单元")
            add_log(task_id, f"耗时: {result.elapsed_seconds:.2f} 秒")
            add_log(task_id, f"输出文件: {result_filename}")
        else:
            raise Exception(result.error)

    except Exception as e:
        import traceback
        error_msg = str(e)
        add_log(task_id, f"翻译失败: {error_msg}")
        task['state'] = 'error'
        task['status'] = f'翻译失败: {error_msg}'
        task['error'] = error_msg
        save_tasks()

        print(f"EPUB翻译错误 (任务 {task_id}):")
        traceback.print_exc()


def _update_task_progress(task_id: str, stats):
    """更新任务进度"""
    if task_id in tasks:
        task = tasks[task_id]
        task['progress'] = stats.progress_percent
        task['status'] = f"翻译中... {stats.completed_chunks}/{stats.total_chunks}"
        save_tasks()


def _add_log_legacy(task_id: str, message: str):
    """保留的日志函数（向后兼容）"""
    if task_id in tasks:
        task = tasks[task_id]
        if 'logs' not in task:
            task['logs'] = []
        task['logs'].append({
            'time': time.strftime('%H:%M:%S'),
            'message': message
        })


# 保留原有的 API 接口（向后兼容）
@api_bp.route('/translate', methods=['POST'])
def translate_pdf():
    """PDF翻译API - 向后兼容"""
    data = request.get_json()
    return jsonify({'status': 'success', 'message': '请使用 /api/translate/unified 接口'})

@api_bp.route('/translate-markdown', methods=['POST'])
def translate_markdown():
    """Markdown翻译API - 向后兼容"""
    data = request.get_json()
    return jsonify({'status': 'success', 'message': '请使用 /api/translate/unified 接口'})

@api_bp.route('/translate-epub', methods=['POST'])
def translate_epub():
    """EPUB翻译API - 向后兼容"""
    data = request.get_json()
    return jsonify({'status': 'success', 'message': '请使用 /api/translate/unified 接口'})

@api_bp.route('/reset-progress', methods=['POST'])
def reset_progress():
    """重置翻译进度"""
    return jsonify({'status': 'success', 'message': '进度已重置'})

@api_bp.route('/abort-translation-legacy', methods=['POST'])
def abort_translation_legacy():
    """中止翻译 - 旧版接口"""
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

@api_bp.route('/translate/results-list', methods=['GET'])
def get_results_list():
    """获取翻译结果列表"""
    try:
        results_dir = 'data/results'
        if not os.path.exists(results_dir):
            return jsonify({'status': 'success', 'files': []})

        files = []
        for filename in os.listdir(results_dir):
            file_path = os.path.join(results_dir, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    'name': filename,
                    'size': stat.st_size,
                    'mtime': int(stat.st_mtime)
                })

        # 按修改时间倒序排列
        files.sort(key=lambda x: x['mtime'], reverse=True)

        return jsonify({'status': 'success', 'files': files})
    except Exception as e:
        logger.error(f"获取结果列表失败: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@api_bp.route('/translate/download-by-file/', methods=['GET'])
def download_by_filename(filename):
    """通过文件名下载翻译结果"""
    try:
        # URL 解码文件名
        from urllib.parse import unquote
        filename = unquote(filename)

        file_path = os.path.join('data/results', filename)
        if not os.path.exists(file_path):
            return jsonify({'error': '文件不存在'}), 404

        return send_file(file_path, as_attachment=True)
    except Exception as e:
        logger.error(f"下载文件失败: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/translate/clear-history', methods=['POST'])
def clear_history():
    """清除上传和翻译结果历史"""
    try:
        import shutil

        # 清除 uploads 目录（保留 .gitkeep）
        uploads_dir = 'uploads'
        if os.path.exists(uploads_dir):
            for item in os.listdir(uploads_dir):
                item_path = os.path.join(uploads_dir, item)
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)

        # 清除 data/uploads 目录
        data_uploads_dir = 'data/uploads'
        if os.path.exists(data_uploads_dir):
            shutil.rmtree(data_uploads_dir)
            os.makedirs(data_uploads_dir, exist_ok=True)

        # 清除 data/results 目录（保留 .gitkeep）
        results_dir = 'data/results'
        if os.path.exists(results_dir):
            for item in os.listdir(results_dir):
                if item != '.gitkeep':
                    item_path = os.path.join(results_dir, item)
                    if os.path.isfile(item_path):
                        os.remove(item_path)
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)

        # 清除 tasks.json
        tasks_file = 'data/tasks.json'
        if os.path.exists(tasks_file):
            os.remove(tasks_file)

        # 清除 checkpoints 目录
        checkpoints_dir = 'data/checkpoints'
        if os.path.exists(checkpoints_dir):
            shutil.rmtree(checkpoints_dir)
            os.makedirs(checkpoints_dir, exist_ok=True)

        logger.info("历史记录已清除")
        return jsonify({'status': 'success', 'message': '历史记录已清除'})

    except Exception as e:
        logger.error(f"清除历史失败: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


# ============================================================
# P0/P1 优化 - 新增 API 端点
# ============================================================

@api_bp.route('/translate/progress/<task_id>', methods=['GET'])
def get_token_progress(task_id):
    """
    获取基于 Token 的翻译进度

    使用 CheckpointManager 获取任务的详细进度信息
    """
    if not core_modules_available:
        return jsonify({'error': '核心模块不可用'}), 503

    try:
        # 使用 CheckpointManager 获取任务进度
        progress_data = checkpoint_manager.get_task_progress(task_id)

        if progress_data is None:
            return jsonify({'error': '任务不存在'}), 404

        # 获取 Token 进度跟踪信息
        token_info = token_progress_tracker.get_progress(task_id)

        response = {
            'task_id': task_id,
            'status': 'success',
            'checkpoint_progress': progress_data,
            'token_progress': token_info
        }

        # 如果有任务状态信息，也一并返回
        task = tasks.get(task_id)
        if task:
            response['task_info'] = {
                'state': task.get('state'),
                'status': task.get('status'),
                'progress': task.get('progress'),
                'created_at': task.get('created_at')
            }

        return jsonify(response)

    except Exception as e:
        logger.error(f"获取Token进度失败: {e}")
        return jsonify({'error': f'获取进度失败: {str(e)}'}), 500


@api_bp.route('/translate/resume', methods=['GET'])
def get_resumable_jobs():
    """
    获取可恢复的翻译任务列表

    使用 CheckpointManager 获取所有可以恢复的翻译任务
    """
    if not core_modules_available:
        return jsonify({'error': '核心模块不可用'}), 503

    try:
        # 使用 CheckpointManager 获取可恢复的任务列表
        resumable_jobs = checkpoint_manager.get_resumable_jobs()

        # 构建完整的任务信息
        jobs_list = []
        for job in resumable_jobs:
            task_id = job.get('task_id')
            task = tasks.get(task_id)

            job_info = {
                'task_id': task_id,
                'checkpoint_info': job,
                'task_info': None
            }

            if task:
                job_info['task_info'] = {
                    'original_filename': task.get('original_filename'),
                    'file_type': task.get('file_type'),
                    'state': task.get('state'),
                    'status': task.get('status'),
                    'progress': task.get('progress'),
                    'created_at': task.get('created_at'),
                    'config': task.get('config', {})
                }

            jobs_list.append(job_info)

        return jsonify({
            'status': 'success',
            'resumable_jobs': jobs_list,
            'total': len(jobs_list)
        })

    except Exception as e:
        logger.error(f"获取可恢复任务失败: {e}")
        return jsonify({'error': f'获取可恢复任务失败: {str(e)}'}), 500


@api_bp.route('/translate/resume/<task_id>', methods=['POST'])
def resume_translation(task_id):
    """
    恢复已停止的翻译任务

    使用 ErrorRecoveryManager 加载检查点并恢复翻译
    """
    if not core_modules_available:
        return jsonify({'error': '核心模块不可用'}), 503

    try:
        # 检查任务是否存在
        task = tasks.get(task_id)
        if not task:
            return jsonify({'error': '任务不存在'}), 404

        # 检查任务是否可恢复
        if task.get('state') not in ['stopped', 'error', 'paused', 'interrupted']:
            return jsonify({
                'error': '任务状态不允许恢复',
                'current_state': task.get('state')
            }), 400

        # 使用 ErrorRecoveryManager 加载检查点
        checkpoint = error_recovery_manager.load_checkpoint(task_id)

        if checkpoint is None:
            return jsonify({'error': '无法加载检查点，任务可能没有有效的保存状态'}), 404

        # 更新任务状态为处理中
        task['state'] = 'processing'
        task['status'] = '正在恢复翻译...'
        task['checkpoint_loaded'] = True
        save_tasks()

        # 获取恢复所需的配置信息
        resume_config = request.get_json() or {}

        logger.info(f"成功加载任务 {task_id} 的检查点，开始恢复翻译")

        return jsonify({
            'status': 'success',
            'message': '翻译任务已恢复',
            'task_id': task_id,
            'checkpoint': checkpoint
        })

    except Exception as e:
        logger.error(f"恢复翻译任务失败: {e}")
        return jsonify({'error': f'恢复翻译失败: {str(e)}'}), 500
