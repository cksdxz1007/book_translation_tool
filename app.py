import logging
logging.basicConfig(level=logging.DEBUG)

from flask import Flask, render_template, request, send_file, jsonify, Response, abort
import os
from werkzeug.utils import secure_filename
from file_handler import upload_file, get_file_format
from pdf_translator_babeldoc import translate_pdf_with_babeldoc
from text_splitter import get_pdf_page_count
from translator import translate_book, TranslationService
from result_generator import merge_translated_chunks, save_result
from config_loader import load_service_config
from epub_parser import extract_text_from_epub, get_epub_metadata
from format_preserving_parser import FormatPreservingParser
from format_preserving_generator import save_format_preserving_result
from text_splitter_enhanced import split_text_into_chunks, split_markdown_preserving_structure, estimate_optimal_chunk_size
import queue
import threading

# 导入管理界面
from admin_routes import admin_bp

app = Flask(__name__)

# 注册管理界面蓝图
app.register_blueprint(admin_bp)

UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'pdf'}
ALLOWED_EPUB_MARKDOWN_EXTENSIONS = {'epub', 'md', 'markdown', 'txt'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

progress_queue = queue.Queue()
# 全局进度状态存储
progress_state = {
    'current_translation': None,
    'messages': [],
    'status': 'idle',  # idle, in_progress, complete, error
    'result_file': None,
    'error_message': None
}

# 全局中止标志
abort_flag = False

def reset_progress_state():
    """重置进度状态"""
    global progress_state, abort_flag
    progress_state = {
        'current_translation': None,
        'messages': [],
        'status': 'idle',
        'result_file': None,
        'error_message': None
    }
    abort_flag = False

def get_default_service():
    """获取配置中的默认服务"""
    configs = load_service_config()
    if configs and 'default_service_name' in configs:
        return configs['default_service_name']
    return 'deepseek_translate_service'  # 默认回退

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_epub_markdown_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EPUB_MARKDOWN_EXTENSIONS

@app.route('/', methods=['GET'])
def main_index():
    """主页面 - 文件类型选择，检查服务配置"""
    try:
        from config.manager import ConfigManager
        config_manager = ConfigManager('data/config.db', 'data/keys')
        
        services = config_manager.list_services()
        default_service = config_manager.get_default_service()
        
        # 检查是否有服务配置
        if not services:
            return render_template('main_index.html', 
                                 no_services=True,
                                 admin_url='/admin',
                                 error_message="未配置翻译服务，请先添加服务配置")
        
        # 检查默认服务是否有API密钥
        service_warning = None
        if default_service and not default_service.get('api_key') and default_service['service_type'] not in ['ollama']:
            service_warning = f"默认服务 '{default_service['name']}' 缺少API密钥，请在管理界面配置"
        
        return render_template('main_index.html', 
                             services_count=len(services),
                             default_service=default_service['name'] if default_service else None,
                             service_warning=service_warning,
                             admin_url='/admin')
    except Exception as e:
        logger.error(f"主页加载失败: {e}")
        return render_template('main_index.html', 
                             error_message="配置系统初始化失败，请检查数据库",
                             admin_url='/admin')

@app.route('/pdf', methods=['GET', 'POST'])
def pdf_translation():
    app.logger.debug("Accessing index route")
    if request.method == 'POST':
        app.logger.debug("POST request received")
        if 'file' not in request.files:
            app.logger.error("No file part in the request")
            return jsonify({'error': 'No file part'})
        file = request.files['file']
        if file.filename == '':
            app.logger.error("No selected file")
            return jsonify({'error': 'No selected file'})
        
        # 安全检查：文件类型
        if not allowed_file(file.filename):
            app.logger.error(f"Invalid file type: {file.filename}")
            return jsonify({'error': 'Only PDF files are allowed'})
        
        # 安全检查：文件名
        filename = secure_filename(file.filename)
        if not filename:
            app.logger.error("Invalid filename after sanitization")
            return jsonify({'error': 'Invalid filename'})
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(file_path)
            app.logger.info(f"File saved: {file_path}")
            
            # 检查文件是否为有效的PDF
            try:
                total_pages = get_pdf_page_count(file_path)
                if total_pages == 0:
                    os.remove(file_path)
                    return jsonify({'error': 'Invalid PDF file'})
            except Exception as e:
                os.remove(file_path)
                app.logger.error(f"Invalid PDF file: {e}")
                return jsonify({'error': 'Invalid PDF file'})
            
            return jsonify({'filename': filename, 'total_pages': total_pages})
            
        except Exception as e:
            app.logger.error(f"File upload failed: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': 'File upload failed'})
    
    return render_template('index.html')

def translate_task(file_path, start_page, end_page, target_language, translation_service, babeldoc_options=None):
    """PDF翻译任务 - 使用BabelDOC"""
    # 重置进度状态
    reset_progress_state()
    progress_state['status'] = 'in_progress'
    
    try:
        progress_queue.put(('progress', '开始处理PDF文件...'))
        
        # 使用BabelDOC翻译PDF
        output_path = translate_pdf_with_babeldoc(
            file_path, 
            translation_service, 
            target_language,
            start_page=start_page,
            end_page=end_page,
            progress_queue=progress_queue,
            babeldoc_options=babeldoc_options
        )
        
        # 移动到结果目录
        result_filename = os.path.basename(output_path)
        final_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        
        if os.path.exists(output_path):
            import shutil
            shutil.move(output_path, final_path)
            progress_queue.put(('complete', result_filename))
            progress_state['status'] = 'complete'
            progress_state['result_file'] = result_filename
        else:
            raise Exception("翻译输出文件未找到")
            
    except Exception as e:
        error_msg = f"PDF翻译失败: {str(e)}"
        app.logger.error(error_msg)
        progress_queue.put(('error', error_msg))
        progress_state['status'] = 'error'
        progress_state['error_message'] = error_msg

def translate_task_legacy(file_path, start_page, end_page, target_language, translation_service):
    """PDF翻译任务 - 使用传统方法"""
    # 重置进度状态
    reset_progress_state()
    progress_state['status'] = 'in_progress'
    
    try:
        progress_queue.put(('progress', '开始处理PDF文件...'))
        
        # 使用传统方法翻译PDF
        translated_chunks = translate_book(
            file_path, 
            translation_service, 
            target_language,
            start_page=start_page,
            end_page=end_page,
            progress_queue=progress_queue
        )
        
        # 合并翻译结果
        progress_queue.put(('progress', '合并翻译结果...'))
        merged_content = merge_translated_chunks(translated_chunks)
        
        # 保存结果
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        result_filename = f"{base_name}_translated_{target_language}.md"
        result_path = os.path.join(app.config['RESULT_FOLDER'], result_filename)
        
        save_result(merged_content, result_path)
        
        progress_queue.put(('complete', result_filename))
        progress_state['status'] = 'complete'
        progress_state['result_file'] = result_filename
            
    except Exception as e:
        error_msg = f"PDF翻译失败: {str(e)}"
        app.logger.error(error_msg)
        progress_queue.put(('error', error_msg))
        progress_state['status'] = 'error'
        progress_state['error_message'] = error_msg

def translate_epub_markdown_task(file_path, target_language, translation_service):
    file_extension = os.path.splitext(file_path)[1].lower()
    
    # 重置进度状态
    reset_progress_state()
    progress_state['status'] = 'in_progress'
    
    try:
        progress_queue.put(('progress', '开始处理文件...'))
        
        # 使用格式保留解析器
        parser = FormatPreservingParser()
        translatable_chunks = []
        
        # 根据文件类型处理内容
        if file_extension == '.epub':
            progress_queue.put(('progress', '解析ePub文件结构...'))
            app.logger.info(f"处理ePub文件: {file_path}")
            translatable_chunks = parser.parse_epub_with_structure(file_path)
            progress_queue.put(('progress', f'ePub解析完成: 提取到 {len(translatable_chunks)} 个可翻译文本块'))
                
        elif file_extension in ['.md', '.markdown']:
            progress_queue.put(('progress', '解析Markdown文件结构...'))
            app.logger.info(f"处理Markdown文件: {file_path}")
            translatable_chunks = parser.parse_markdown_with_structure(file_path)
            progress_queue.put(('progress', f'Markdown解析完成: 提取到 {len(translatable_chunks)} 个可翻译文本块'))
            
        else:
            # 处理普通文本文件
            progress_queue.put(('progress', '读取文本文件内容...'))
            app.logger.info(f"处理文本文件: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                try:
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()
                except:
                    with open(file_path, 'r', encoding='latin-1') as f:
                        content = f.read()
            
            # 对于普通文本，创建简单的结构
            if len(content) > 5000:
                chunks = split_text_into_chunks(content, max_chunk_size=3000)
            else:
                chunks = [content]
            
            translatable_chunks = [{'text': chunk, 'type': 'paragraph', 'context': {}} for chunk in chunks]
            progress_queue.put(('progress', f'文本处理完成: {len(translatable_chunks)} 个文本块'))
        
        if not translatable_chunks:
            progress_queue.put(('error', '未找到可翻译的内容'))
            return
        
        # 翻译所有块
        translated_chunks = []
        total_chunks = len(translatable_chunks)
        
        progress_queue.put(('progress', f'开始翻译 {total_chunks} 个内容块...'))
        
        # 直接使用传入的翻译服务对象
        app.logger.info(f"使用翻译服务: {type(translation_service).__name__}")
        
        for i, chunk_data in enumerate(translatable_chunks):
            if progress_state.get('abort_requested', False):
                progress_queue.put(('error', '翻译已被用户中止'))
                return
            
            chunk_text = chunk_data['text']
            progress_queue.put(('progress', f'翻译第 {i+1}/{total_chunks} 个文本块...'))
            app.logger.info(f"翻译块 {i+1}/{total_chunks}: {chunk_text[:50]}...")
            
            try:
                translated_text = translation_service.translate_chunk(chunk_text, target_language=target_language)
                translated_chunks.append({
                    'text': translated_text,
                    'type': chunk_data['type'],
                    'context': chunk_data['context']
                })
                
                progress = int((i + 1) / total_chunks * 100)
                progress_queue.put(('progress', f'翻译进度: {progress}% ({i+1}/{total_chunks})'))
                
            except Exception as e:
                app.logger.error(f"翻译块 {i+1} 失败: {e}")
                progress_queue.put(('error', f'翻译第 {i+1} 个文本块失败: {str(e)}'))
                return
        
        # 使用格式保留生成器保存结果
        output_filename = f"{os.path.splitext(os.path.basename(file_path))[0]}_translated_{target_language}"
        base_output_path = os.path.join(app.config['RESULT_FOLDER'], output_filename + '.txt')
        
        progress_queue.put(('progress', '生成格式保留的翻译结果...'))
        
        try:
            result_files = save_format_preserving_result(parser, translated_chunks, base_output_path, file_extension)
            
            # 返回主要结果文件名
            main_result = None
            for result_file in result_files:
                if result_file.endswith(file_extension) or (file_extension == '.epub' and result_file.endswith('.epub')):
                    main_result = os.path.basename(result_file)
                    break
            
            if not main_result:
                main_result = os.path.basename(result_files[0]) if result_files else os.path.basename(base_output_path)
            
            app.logger.info(f"翻译完成，生成文件: {result_files}")
            progress_queue.put(('complete', main_result))
            
        except Exception as e:
            app.logger.error(f"保存格式保留结果失败: {e}")
            # 降级到简单文本保存
            merged_text = '\n\n'.join([chunk['text'] for chunk in translated_chunks])
            with open(base_output_path, 'w', encoding='utf-8') as f:
                f.write(merged_text)
            progress_queue.put(('complete', os.path.basename(base_output_path)))
        
    except Exception as e:
        app.logger.error(f"翻译任务失败: {e}")
        progress_queue.put(('error', f'翻译失败: {str(e)}'))

@app.route('/test', methods=['GET'])
def test():
    return jsonify({'message': 'test successful'})

@app.route('/epub-markdown', methods=['GET', 'POST'])
def epub_markdown():
    app.logger.debug("Accessing epub-markdown route")
    if request.method == 'POST':
        app.logger.debug("POST request received")
        if 'file' not in request.files:
            app.logger.error("No file part in the request")
            return jsonify({'error': 'No file part'})
        file = request.files['file']
        if file.filename == '':
            app.logger.error("No selected file")
            return jsonify({'error': 'No selected file'})
        
        # 安全检查：文件类型
        if not allowed_epub_markdown_file(file.filename):
            app.logger.error(f"Invalid file type: {file.filename}")
            return jsonify({'error': 'Only ePub, Markdown, and text files are allowed'})
        
        # 安全检查：文件名
        original_filename = file.filename
        filename = secure_filename(file.filename)
        
        # 如果secure_filename返回的文件名不包含扩展名或只是扩展名，使用时间戳作为文件名
        if not filename or '.' not in filename or len(filename.split('.')[0]) == 0:
            import time
            # 从原始文件名获取扩展名
            if '.' in original_filename:
                file_extension = original_filename.rsplit('.', 1)[1].lower()
            else:
                file_extension = 'epub'  # 默认扩展名
            filename = f"uploaded_{int(time.time())}.{file_extension}"
            app.logger.info(f"Using timestamp filename: {filename} for original: {original_filename}")
        
        if not filename:
            app.logger.error("Invalid filename after sanitization")
            return jsonify({'error': 'Invalid filename'})
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(file_path)
            app.logger.info(f"File saved: {file_path}")
            
            # 获取文件类型
            if '.' in filename:
                file_extension = filename.rsplit('.', 1)[1].lower()
            else:
                file_extension = 'unknown'
                
            file_type = {
                'epub': 'ePub',
                'md': 'Markdown',
                'markdown': 'Markdown',
                'txt': 'Text'
            }.get(file_extension, file_extension.upper())
            
            return jsonify({'filename': filename, 'file_type': file_type})
            
        except Exception as e:
            app.logger.error(f"File upload failed: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({'error': 'File upload failed'})
    
    return render_template('epub_markdown.html')

@app.route('/services', methods=['GET'])
def get_services():
    """Get available translation services from configuration"""
    try:
        # 使用新的SQLite配置系统
        from config.manager import ConfigManager
        config_manager = ConfigManager('data/config.db', 'data/keys')
        
        # 获取所有活跃的服务
        with config_manager.db.get_connection() as conn:
            cursor = conn.execute(
                'SELECT id, name, service_type, model_name, is_active FROM translation_services WHERE is_active = 1'
            )
            rows = cursor.fetchall()
            
            services = {}
            for row in rows:
                service = dict(row)
                services[service['name']] = {
                    'service_type': service.get('service_type'),
                    'model_name': service.get('model_name'),
                    'requires_api_key': True  # 假设所有服务都需要API密钥
                }
            
            return jsonify(services)
    except Exception as e:
        app.logger.error(f"Error loading services from database: {e}")
        return jsonify({})

@app.route('/translate', methods=['POST'])
def translate():
    app.logger.debug("Accessing translate route")
    data = request.json
    app.logger.debug(f"Received data: {data}")
    filename = data['filename']
    start_page = int(data['start_page'])
    end_page = int(data['end_page'])
    target_language = data['target_language']
    translation_engine = data.get('translation_engine', 'babeldoc')  # 默认使用 BabelDOC
    
    # BabelDOC 特定选项
    babeldoc_options = {}
    if translation_engine == 'babeldoc':
        babeldoc_options = {
            'output_mode': data.get('output_mode', 'both'),
            'dual_translate_first': data.get('dual_translate_first', False),
            'use_alternating_pages': data.get('use_alternating_pages', False)
        }
    
    # Service selection - support both old ollama params and new service selection
    service_name = data.get('service_name')
    ollama_url = data.get('ollama_url', 'http://localhost:11434/api/generate')
    ollama_model = data.get('ollama_model', 'qwen2.5:7b')
    
    if service_name:
        # Use configured service
        translation_service = TranslationService(service_name_from_config=service_name)
    else:
        # Fallback to default service
        default_service = get_default_service()
        translation_service = TranslationService(service_name_from_config=default_service)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        app.logger.error(f"File not found: {file_path}")
        abort(404, description="File not found")

    # 根据选择的翻译引擎启动不同的任务
    if translation_engine == 'babeldoc':
        threading.Thread(target=translate_task, args=(file_path, start_page, end_page, target_language, translation_service, babeldoc_options)).start()
    else:
        threading.Thread(target=translate_task_legacy, args=(file_path, start_page, end_page, target_language, translation_service)).start()
    
    return jsonify({'status': 'started'})

@app.route('/translate-epub-markdown', methods=['POST'])
def translate_epub_markdown():
    app.logger.debug("Accessing translate-epub-markdown route")
    data = request.json
    app.logger.debug(f"Received data: {data}")
    filename = data['filename']
    target_language = data['target_language']
    
    # Service selection - support both old ollama params and new service selection
    service_name = data.get('service_name')
    ollama_url = data.get('ollama_url', 'http://localhost:11434/api/generate')
    ollama_model = data.get('ollama_model', 'qwen2.5:7b')

    if service_name:
        # Use configured service
        translation_service = TranslationService(service_name_from_config=service_name)
    else:
        # Fallback to default service
        default_service = get_default_service()
        translation_service = TranslationService(service_name_from_config=default_service)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(file_path):
        app.logger.error(f"File not found: {file_path}")
        abort(404, description="File not found")

    threading.Thread(target=translate_epub_markdown_task, args=(file_path, target_language, translation_service)).start()

    return jsonify({'status': 'started'})

@app.route('/progress')
def progress():
    app.logger.debug("Accessing progress route")
    
    def generate():
        # 首先发送所有已存在的进度消息
        for message in progress_state['messages']:
            yield f"data: {message}\n\n"
        
        # 如果翻译已完成或出错，发送最终状态
        if progress_state['status'] == 'complete':
            yield f"data: complete:{progress_state['result_file']}\n\n"
            return
        elif progress_state['status'] == 'error':
            yield f"data: error:{progress_state['error_message']}\n\n"
            return
        
        # 然后监听新的进度消息
        while True:
            progress_msg = progress_queue.get()
            if progress_msg[0] == 'progress':
                message = progress_msg[1]
                progress_state['messages'].append(message)
                app.logger.debug(f"Sending progress: {message}")
                yield f"data: {message}\n\n"
            elif progress_msg[0] == 'complete':
                progress_state['status'] = 'complete'
                progress_state['result_file'] = progress_msg[1]
                yield f"data: complete:{progress_msg[1]}\n\n"
                break
            elif progress_msg[0] == 'error':
                progress_state['status'] = 'error'
                progress_state['error_message'] = progress_msg[1]
                yield f"data: error:{progress_msg[1]}\n\n"
                break
            elif progress_msg[0] == 'aborted':
                progress_state['status'] = 'error'
                progress_state['error_message'] = progress_msg[1]
                yield f"data: aborted:{progress_msg[1]}\n\n"
                break

    return Response(generate(), mimetype='text/event-stream')

@app.route('/progress-status')
def progress_status():
    """获取当前进度状态"""
    return jsonify(progress_state)

@app.route('/reset-progress', methods=['POST'])
def reset_progress():
    """重置进度状态"""
    reset_progress_state()
    return jsonify({'status': 'reset'})

@app.route('/abort-translation', methods=['POST'])
def abort_translation():
    """中止当前翻译任务"""
    global abort_flag, progress_state
    abort_flag = True
    app.logger.info("用户请求中止翻译")
    
    # 更新进度状态
    progress_state['status'] = 'error'
    progress_state['error_message'] = '用户中止了翻译任务'
    progress_state['messages'].append('用户中止了翻译任务')
    
    progress_queue.put(('aborted', '用户中止了翻译任务'))
    return jsonify({'status': 'aborted'})

@app.route('/download/<filename>')
def download_file(filename):
    app.logger.debug(f"Accessing download route for file: {filename}")
    file_path = os.path.join(app.config['RESULT_FOLDER'], filename)
    if not os.path.exists(file_path):
        app.logger.error(f"File not found: {file_path}")
        abort(404, description="File not found")
    return send_file(file_path, as_attachment=True, download_name=secure_filename(filename))

@app.errorhandler(403)
def forbidden_error(error):
    app.logger.error('403 错误: %s', error)
    return jsonify(error=str(error)), 403

@app.errorhandler(404)
def not_found_error(error):
    app.logger.error('404 错误: %s', error)
    return jsonify(error=str(error)), 404

@app.errorhandler(500)
def internal_error(error):
    app.logger.error('500 错误: %s', error)
    return jsonify(error=str(error)), 500

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESULT_FOLDER, exist_ok=True)
    app.run(host='0.0.0.0', port=5001, debug=False)