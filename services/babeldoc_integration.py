"""
BabelDOC 集成示例
用于将 BabelDOC 集成到现有的 Flask PDF 翻译应用中
"""

import subprocess
import os
import json
from pathlib import Path
from typing import Optional, Dict, Any

class BabelDOCTranslator:
    """BabelDOC 翻译器封装类"""
    
    def __init__(self, 
                 default_model: str = "llama3",
                 default_base_url: str = "http://localhost:11434/v1",
                 default_api_key: str = "a"):
        self.default_model = default_model
        self.default_base_url = default_base_url
        self.default_api_key = default_api_key
    
    def translate_pdf(self,
                     pdf_path: str,
                     output_dir: str = "./results",
                     pages: Optional[str] = None,
                     target_language: str = "zh",
                     model: Optional[str] = None,
                     base_url: Optional[str] = None,
                     api_key: Optional[str] = None,
                     progress_callback=None) -> Dict[str, Any]:
        """
        翻译 PDF 文件
        
        Args:
            pdf_path: PDF 文件路径
            output_dir: 输出目录
            pages: 页面范围，如 "1-5,10,15-20"
            target_language: 目标语言代码
            model: 模型名称
            base_url: API 基础 URL
            api_key: API 密钥
            progress_callback: 进度回调函数
            
        Returns:
            包含翻译结果的字典
        """
        
        # 使用默认值
        model = model or self.default_model
        base_url = base_url or self.default_base_url
        api_key = api_key or self.default_api_key
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 构建命令
        cmd = [
            "babeldoc",
            "--files", pdf_path,
            "--output", output_dir,
            "--lang-out", target_language,
            "--openai",
            "--openai-model", model,
            "--openai-base-url", base_url,
            "--openai-api-key", api_key,
            "--watermark-output-mode", "no_watermark",
            "--report-interval", "1.0"  # 1秒报告一次进度
        ]
        
        if pages:
            cmd.extend(["--pages", pages])
        
        try:
            # 启动进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 监控进度
            progress = 0
            for line in process.stdout:
                if progress_callback:
                    # 简单的进度解析（实际实现可能需要更复杂的解析）
                    if "Processing page" in line:
                        try:
                            # 提取页面信息
                            parts = line.split()
                            current_page = int(parts[2])
                            total_pages = int(parts[4])
                            progress = int((current_page / total_pages) * 100)
                            progress_callback(progress, f"正在处理第 {current_page}/{total_pages} 页")
                        except:
                            pass
                    elif "Translation complete" in line:
                        progress = 100
                        progress_callback(progress, "翻译完成")
            
            # 等待进程完成
            process.wait()
            
            if process.returncode == 0:
                # 查找生成的文件
                pdf_name = Path(pdf_path).stem
                result_files = self._find_output_files(output_dir, pdf_name)
                
                return {
                    "success": True,
                    "files": result_files,
                    "message": "翻译完成"
                }
            else:
                error_output = process.stderr.read()
                return {
                    "success": False,
                    "error": error_output,
                    "message": "翻译失败"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"执行错误: {str(e)}"
            }
    
    def _find_output_files(self, output_dir: str, pdf_name: str) -> Dict[str, str]:
        """查找输出文件"""
        files = {}
        
        # 可能的输出文件名模式
        patterns = [
            f"{pdf_name}_translated.pdf",
            f"{pdf_name}_dual.pdf",
            f"{pdf_name}_mono.pdf"
        ]
        
        for pattern in patterns:
            file_path = os.path.join(output_dir, pattern)
            if os.path.exists(file_path):
                if "dual" in pattern:
                    files["dual"] = file_path
                elif "mono" in pattern or "translated" in pattern:
                    files["translated"] = file_path
        
        return files

# Flask 集成示例
def integrate_with_flask_app():
    """展示如何集成到 Flask 应用中"""
    
    from flask import Flask, request, jsonify, send_file
    
    app = Flask(__name__)
    translator = BabelDOCTranslator()
    
    @app.route('/translate_with_babeldoc', methods=['POST'])
    def translate_with_babeldoc():
        try:
            # 获取参数
            file_path = request.form.get('file_path')
            pages = request.form.get('pages')
            target_language = request.form.get('target_language', 'zh')
            model = request.form.get('model')
            
            if not file_path or not os.path.exists(file_path):
                return jsonify({"error": "文件不存在"}), 400
            
            # 进度回调函数
            def progress_callback(progress, message):
                # 这里可以通过 WebSocket 或其他方式实时更新前端
                print(f"Progress: {progress}% - {message}")
            
            # 执行翻译
            result = translator.translate_pdf(
                pdf_path=file_path,
                pages=pages,
                target_language=target_language,
                model=model,
                progress_callback=progress_callback
            )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    return app

# 命令行工具示例
def cli_example():
    """命令行使用示例"""
    
    translator = BabelDOCTranslator()
    
    # 翻译示例
    result = translator.translate_pdf(
        pdf_path="./uploads/example.pdf",
        pages="1-5",
        target_language="zh",
        progress_callback=lambda p, m: print(f"{p}%: {m}")
    )
    
    if result["success"]:
        print("翻译成功!")
        for file_type, file_path in result["files"].items():
            print(f"{file_type}: {file_path}")
    else:
        print(f"翻译失败: {result['error']}")

if __name__ == "__main__":
    # 运行命令行示例
    cli_example()
