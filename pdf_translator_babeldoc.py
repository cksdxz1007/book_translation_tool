import os
import subprocess
import logging
from pathlib import Path
from translator import TranslationService

logger = logging.getLogger(__name__)

class PDFTranslatorBabelDoc:
    def __init__(self, translation_service: TranslationService):
        self.translation_service = translation_service
        
    def translate_pdf(self, pdf_path, target_language, start_page=None, end_page=None, progress_queue=None, babeldoc_options=None):
        """
        使用BabelDOC翻译PDF文件
        
        Args:
            pdf_path: PDF文件路径
            target_language: 目标语言
            start_page: 起始页码（1-based）
            end_page: 结束页码（1-based）
            progress_queue: 进度队列
            
        Returns:
            翻译后的PDF文件路径
        """
        try:
            if progress_queue:
                progress_queue.put(('progress', '初始化BabelDOC翻译...'))

            # 预测试API服务连接
            if progress_queue:
                progress_queue.put(('progress', '正在测试翻译服务连接...'))

            success, message = self.translation_service.test_connection()
            if not success:
                error_msg = f"翻译服务连接测试失败: {message}"
                logger.error(error_msg)
                if progress_queue:
                    progress_queue.put(('error', error_msg))
                raise Exception(error_msg)

            if progress_queue:
                progress_queue.put(('progress', f'服务连接测试成功: {message}'))

            # 准备输出目录
            output_dir = os.path.join(os.path.dirname(pdf_path), 'results')
            os.makedirs(output_dir, exist_ok=True)

            # 获取正确的 base_url 和 API key
            base_url = self.translation_service.openai_compatible_base_url
            api_key = self.translation_service.api_key
            model_name = self.translation_service.model_name

            if not base_url:
                raise Exception("未配置翻译服务的 base_url")
            if not api_key:
                raise Exception("未配置翻译服务的 API key")
            
            # 构建BabelDOC命令
            cmd = [
                "/opt/homebrew/Caskroom/miniconda/base/envs/books_venv/bin/babeldoc",
                "--files", pdf_path,
                "--output", output_dir,
                "--lang-out", target_language,
                "--openai",
                "--openai-model", model_name,
                "--openai-base-url", base_url,
                "--openai-api-key", api_key,
                "--watermark-output-mode", "no_watermark",
                "--report-interval", "1.0",  # 更频繁的进度报告
                "--auto-enable-ocr-workaround",  # 自动处理扫描文档
                "--pool-max-workers", "8",  # 增加工作线程数
                "--qps", "4",  # 明确设置QPS限制
                "--no-auto-extract-glossary"  # 禁用自动术语提取以提高性能
            ]
            
            # 处理 BabelDOC 特定选项
            if babeldoc_options:
                output_mode = babeldoc_options.get('output_mode', 'both')
                
                # 根据输出模式添加参数
                if output_mode == 'dual-only':
                    cmd.append('--no-mono')  # 不生成单语PDF
                elif output_mode == 'mono-only':
                    cmd.append('--no-dual')  # 不生成双语PDF
                # 'both' 模式不需要额外参数
                
                # 双语模式选项
                if babeldoc_options.get('dual_translate_first', False):
                    cmd.append('--dual-translate-first')
                
                if babeldoc_options.get('use_alternating_pages', False):
                    cmd.append('--use-alternating-pages-dual')
            
            # 添加页面范围参数
            if start_page is not None or end_page is not None:
                pages_str = f"{start_page or 1}-{end_page or ''}"
                cmd.extend(["--pages", pages_str])
                if progress_queue:
                    progress_queue.put(('progress', f'设置翻译页面范围: {pages_str}'))
            
            if progress_queue:
                progress_queue.put(('progress', '启动BabelDOC翻译进程...'))
            
            # 启动BabelDOC进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 监控进度
            current_page = 0
            total_pages = 0
            
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                    
                if progress_queue:
                    # 解析进度信息
                    if "Processing page" in line or "页" in line:
                        try:
                            # 尝试提取页面信息
                            if "/" in line:
                                parts = line.split("/")
                                if len(parts) >= 2:
                                    current_page = int(''.join(filter(str.isdigit, parts[0])))
                                    total_pages = int(''.join(filter(str.isdigit, parts[1])))
                                    progress = int((current_page / total_pages) * 100) if total_pages > 0 else 0
                                    progress_queue.put(('progress', f'正在处理第 {current_page}/{total_pages} 页 ({progress}%)'))
                        except:
                            pass
                    elif "Translation complete" in line or "完成" in line:
                        progress_queue.put(('progress', '翻译完成，正在生成文件...'))
                    else:
                        # 显示其他进度信息
                        progress_queue.put(('progress', line))
            
            # 等待进程完成
            process.wait()
            
            if process.returncode == 0:
                # 查找生成的文件
                pdf_name = Path(pdf_path).stem
                result_files = self._find_output_files(output_dir, pdf_name)
                
                if result_files:
                    # 返回主要的翻译文件
                    main_file = result_files.get('translated') or result_files.get('dual')
                    if progress_queue:
                        progress_queue.put(('progress', f'翻译完成！文件保存至: {os.path.basename(main_file)}'))
                    return main_file
                else:
                    raise Exception("未找到翻译输出文件")
            else:
                error_output = process.stderr.read()
                raise Exception(f"BabelDOC执行失败: {error_output}")
                
        except Exception as e:
            error_msg = f"BabelDOC翻译失败: {str(e)}"
            logger.error(error_msg)
            if progress_queue:
                progress_queue.put(('error', error_msg))
            raise
    
    def _find_output_files(self, output_dir: str, pdf_name: str):
        """查找输出文件"""
        files = {}
        
        # 遍历输出目录查找文件
        for file_path in Path(output_dir).glob("*.pdf"):
            file_name = file_path.name.lower()
            if pdf_name.lower() in file_name:
                if "dual" in file_name:
                    files["dual"] = str(file_path)
                elif "translated" in file_name or "mono" in file_name:
                    files["translated"] = str(file_path)
        
        return files

def translate_pdf_with_babeldoc(pdf_path, translation_service, target_language, 
                               start_page=None, end_page=None, progress_queue=None, babeldoc_options=None):
    """
    便捷函数：使用BabelDoc翻译PDF
    """
    translator = PDFTranslatorBabelDoc(translation_service)
    return translator.translate_pdf(
        pdf_path, target_language, start_page, end_page, progress_queue, babeldoc_options
    )
