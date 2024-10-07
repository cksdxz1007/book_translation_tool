import logging
logging.basicConfig(level=logging.DEBUG)

from flask import Flask, render_template, request, send_file, jsonify, Response, abort
import os
from werkzeug.utils import secure_filename
from file_handler import upload_file, get_file_format
from text_splitter import split_pdf, get_pdf_page_count
from translator import translate_book, TranslationService
from result_generator import merge_translated_chunks, save_result
import queue
import threading

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULT_FOLDER'] = RESULT_FOLDER

progress_queue = queue.Queue()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def index():
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
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            app.logger.info(f"File saved: {file_path}")
            total_pages = get_pdf_page_count(file_path)
            return jsonify({'filename': filename, 'total_pages': total_pages})
    return render_template('index.html')

def translate_task(file_path, start_page, end_page, target_language, translation_service):
    chunks = split_pdf(file_path, start_page=start_page, end_page=end_page)
    translated_chunks = translate_book(chunks, translation_service, target_language=target_language, progress_queue=progress_queue)
    merged_text = merge_translated_chunks(translated_chunks)
    output_filename = f"{os.path.splitext(os.path.basename(file_path))[0]}_translated_{target_language}"
    output_path = os.path.join(app.config['RESULT_FOLDER'], output_filename)
    txt_path, pdf_path = save_result(merged_text, output_path)
    progress_queue.put(('complete', os.path.basename(pdf_path)))

@app.route('/translate', methods=['POST'])
def translate():
    app.logger.debug("Accessing translate route")
    data = request.json
    app.logger.debug(f"Received data: {data}")
    filename = data['filename']
    start_page = int(data['start_page'])
    end_page = int(data['end_page'])
    target_language = data['target_language']
    ollama_url = data.get('ollama_url', 'http://localhost:11434/api/generate')
    ollama_model = data.get('ollama_model', 'qwen2.5:7b')  # 允许用户指定模型名称

    translation_service = TranslationService('ollama', ollama_url=ollama_url, model_name=ollama_model)

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if not os.path.exists(file_path):
        app.logger.error(f"File not found: {file_path}")
        abort(404, description="File not found")

    threading.Thread(target=translate_task, args=(file_path, start_page, end_page, target_language, translation_service)).start()
    
    return jsonify({'status': 'started'})

@app.route('/progress')
def progress():
    app.logger.debug("Accessing progress route")
    def generate():
        while True:
            progress = progress_queue.get()
            if progress[0] == 'progress':
                yield f"data: {progress[1]}\n\n"
            elif progress[0] == 'complete':
                yield f"data: complete:{progress[1]}\n\n"
                break

    return Response(generate(), mimetype='text/event-stream')

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
    app.run(debug=True)