#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BabelDOC PDF翻译引擎

专业PDF翻译，保持版式和格式
基于BabelDOC API文档实现
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Callable

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class BabelDocTranslator:
    """BabelDOC翻译器 - 基于官方API文档实现"""

    def __init__(self, api_key: str = None, model: str = 'deepseek-chat',
                 base_url: str = None):
        """
        初始化BabelDOC翻译器

        Args:
            api_key: API密钥，如果为None则从环境变量BABELDOC_API_KEY读取
            model: 使用的模型名称
            base_url: API基础URL，如果为None则使用默认值
        """
        self.api_key = api_key or os.getenv('BABELDOC_API_KEY')
        self.model = model
        self.base_url = base_url or os.getenv('BABELDOC_API_URL', 'https://api.deepseek.com/v1')
        self.doc_layout_model = None

    async def _load_doc_layout_model(self):
        """加载文档布局模型（ONNX）"""
        try:
            from babeldoc.docvision.doclayout import DocLayoutModel
            if self.doc_layout_model is None:
                logger.info("加载BabelDOC文档布局模型...")
                self.doc_layout_model = DocLayoutModel.load_onnx()
                logger.info("文档布局模型加载成功")
            return self.doc_layout_model
        except Exception as e:
            logger.error(f"加载文档布局模型失败: {e}")
            raise

    def _create_translator(self, lang_in: str, lang_out: str):
        """创建BabelDOC翻译器"""
        try:
            from babeldoc.translator.translator import OpenAITranslator

            translator = OpenAITranslator(
                lang_in=lang_in,
                lang_out=lang_out,
                model=self.model,
                api_key=self.api_key,
                base_url=self.base_url
            )

            return translator
        except Exception as e:
            logger.error(f"创建BabelDOC翻译器失败: {e}")
            raise

    def translate_pdf(self, pdf_path: str, output_dir: str,
                     lang_in: str = 'en', lang_out: str = 'zh',
                     progress_callback: Optional[Callable] = None,
                     **kwargs) -> Dict[str, Any]:
        """
        翻译PDF文件

        Args:
            pdf_path: 输入PDF文件路径
            output_dir: 输出目录
            lang_in: 源语言代码（如 'en', 'en-US'）
            lang_out: 目标语言代码（如 'zh', 'zh-CN'）
            progress_callback: 进度回调函数
            **kwargs: 其他配置参数

        Returns:
            包含翻译结果的字典
        """
        try:
            # 验证输入文件
            if not os.path.exists(pdf_path):
                raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")

            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)

            # 运行异步翻译
            result = asyncio.run(self._translate_pdf_async(
                pdf_path=pdf_path,
                output_dir=output_dir,
                lang_in=lang_in,
                lang_out=lang_out,
                progress_callback=progress_callback,
                **kwargs
            ))

            return result

        except Exception as e:
            logger.error(f"PDF翻译失败: {e}")
            raise

    async def _translate_pdf_async(self, pdf_path: str, output_dir: str,
                                  lang_in: str, lang_out: str,
                                  progress_callback: Optional[Callable] = None,
                                  **kwargs) -> Dict[str, Any]:
        """异步翻译PDF"""
        try:
            # 加载文档布局模型
            doc_layout_model = await self._load_doc_layout_model()

            # 创建翻译器
            translator = self._create_translator(lang_in, lang_out)

            # 创建翻译配置
            from babeldoc.format.pdf.translation_config import (
                TranslationConfig,
                WatermarkOutputMode
            )

            # 设置默认配置
            config_kwargs = {
                'input_file': pdf_path,
                'translator': translator,
                'lang_in': lang_in,
                'lang_out': lang_out,
                'doc_layout_model': doc_layout_model,
                'output_dir': output_dir,
                'qps': kwargs.get('qps', 4),
                'pool_max_workers': kwargs.get('pool_max_workers', 4),
                'watermark_output_mode': WatermarkOutputMode.NoWatermark,
                'debug': kwargs.get('debug', False),
                'report_interval': kwargs.get('report_interval', 0.1),
            }

            # 添加可选参数
            if 'pages' in kwargs:
                config_kwargs['pages'] = kwargs['pages']

            if 'no_dual' in kwargs:
                config_kwargs['no_dual'] = kwargs['no_dual']

            if 'no_mono' in kwargs:
                config_kwargs['no_mono'] = kwargs['no_mono']

            if 'ocr_workaround' in kwargs:
                config_kwargs['ocr_workaround'] = kwargs['ocr_workaround']

            if 'auto_enable_ocr_workaround' in kwargs:
                config_kwargs['auto_enable_ocr_workaround'] = kwargs['auto_enable_ocr_workaround']

            # 双语对照显示模式参数
            if 'use_alternating_pages_dual' in kwargs:
                config_kwargs['use_alternating_pages_dual'] = kwargs['use_alternating_pages_dual']

            if 'dual_translate_first' in kwargs:
                config_kwargs['dual_translate_first'] = kwargs['dual_translate_first']

            # 格式保留参数
            if 'disable_rich_text_translate' in kwargs:
                config_kwargs['disable_rich_text_translate'] = kwargs['disable_rich_text_translate']

            if 'split_short_lines' in kwargs:
                config_kwargs['split_short_lines'] = kwargs['split_short_lines']

            # 兼容性参数
            if 'skip_clean' in kwargs:
                config_kwargs['skip_clean'] = kwargs['skip_clean']

            if 'enhance_compatibility' in kwargs:
                config_kwargs['enhance_compatibility'] = kwargs['enhance_compatibility']

            config = TranslationConfig(**config_kwargs)

            # 开始翻译
            from babeldoc.format.pdf.high_level import async_translate

            logger.info(f"开始翻译PDF: {pdf_path}")
            logger.info(f"输出目录: {output_dir}")
            logger.info(f"语言: {lang_in} -> {lang_out}")

            # 记录双语对照配置
            if not config_kwargs.get('no_dual', False):
                use_alternating = config_kwargs.get('use_alternating_pages_dual', False)
                translate_first = config_kwargs.get('dual_translate_first', False)
                logger.info(f"双语对照模式: 交替页面={use_alternating}, 译文优先={translate_first}")

            # 记录格式保留配置
            disable_rich = config_kwargs.get('disable_rich_text_translate', False)
            split_short = config_kwargs.get('split_short_lines', True)
            logger.info(f"格式保留: 禁用富文本={disable_rich}, 分割短行={split_short}")

            translate_result = None
            async for event in async_translate(config):
                # 发送进度事件
                if progress_callback:
                    progress_callback(event)

                # 处理事件
                if event["type"] == "progress_update":
                    progress = event.get('overall_progress', 0)
                    stage = event.get('stage', '处理中')
                    logger.info(f"进度: {progress:.1f}% - {stage}")

                elif event["type"] == "finish":
                    translate_result = event["translate_result"]
                    logger.info("PDF翻译完成")

                elif event["type"] == "error":
                    error_msg = event.get('error', '未知错误')
                    logger.error(f"翻译错误: {error_msg}")
                    raise Exception(f"翻译失败: {error_msg}")

            # 整理结果
            if translate_result:
                result = {
                    'success': True,
                    'mono_pdf_path': str(translate_result.mono_pdf_path) if translate_result.mono_pdf_path else None,
                    'dual_pdf_path': str(translate_result.dual_pdf_path) if translate_result.dual_pdf_path else None,
                    'no_watermark_mono_pdf_path': str(translate_result.no_watermark_mono_pdf_path) if translate_result.no_watermark_mono_pdf_path else None,
                    'no_watermark_dual_pdf_path': str(translate_result.no_watermark_dual_pdf_path) if translate_result.no_watermark_dual_pdf_path else None,
                    'auto_extracted_glossary_path': str(translate_result.auto_extracted_glossary_path) if translate_result.auto_extracted_glossary_path else None,
                    'original_pdf_path': translate_result.original_pdf_path,
                    'total_seconds': translate_result.total_seconds,
                    'peak_memory_usage': translate_result.peak_memory_usage,
                    'total_valid_character_count': translate_result.total_valid_character_count,
                    'total_valid_text_token_count': translate_result.total_valid_text_token_count,
                }

                logger.info(f"翻译结果: 单语PDF={result['mono_pdf_path']}")
                logger.info(f"翻译结果: 双语PDF={result['dual_pdf_path']}")
                logger.info(f"翻译耗时: {result['total_seconds']:.2f}秒")

                return result
            else:
                raise Exception("翻译未完成，未获取到结果")

        except Exception as e:
            logger.error(f"异步PDF翻译失败: {e}")
            raise

    def is_available(self) -> bool:
        """检查BabelDOC是否可用"""
        try:
            # 检查API密钥
            if not self.api_key:
                logger.warning("BabelDOC API密钥未配置")
                return False

            # 检查BabelDOC是否安装
            try:
                import babeldoc
                logger.info(f"BabelDOC版本: {babeldoc.__version__}")
                return True
            except ImportError:
                logger.error("BabelDOC未安装")
                return False

        except Exception as e:
            logger.error(f"BabelDOC可用性检查失败: {e}")
            return False

def translate_pdf_with_babeldoc(pdf_path: str, output_dir: str,
                               lang_in: str = 'en', lang_out: str = 'zh',
                               api_key: str = None,
                               progress_callback: Optional[Callable] = None,
                               **kwargs) -> Dict[str, Any]:
    """
    翻译PDF文件的便捷函数

    Args:
        pdf_path: 输入PDF路径
        output_dir: 输出目录
        lang_in: 源语言代码
        lang_out: 目标语言代码
        api_key: API密钥
        progress_callback: 进度回调函数
        **kwargs: 其他配置参数

    Returns:
        翻译结果字典
    """
    translator = BabelDocTranslator(api_key=api_key)
    return translator.translate_pdf(
        pdf_path=pdf_path,
        output_dir=output_dir,
        lang_in=lang_in,
        lang_out=lang_out,
        progress_callback=progress_callback,
        **kwargs
    )

# 语言代码映射
LANGUAGE_CODES = {
    'zh': 'zh-CN',
    'en': 'en-US',
    'ja': 'ja-JP',
    'ko': 'ko-KR',
    'fr': 'fr-FR',
    'de': 'de-DE',
    'es': 'es-ES',
}

def normalize_language_code(lang_code: str) -> str:
    """规范化语言代码"""
    return LANGUAGE_CODES.get(lang_code, lang_code)

if __name__ == '__main__':
    # 测试代码
    import tempfile

    # 配置日志
    logging.basicConfig(level=logging.INFO)

    # 测试可用性
    translator = BabelDocTranslator()
    if translator.is_available():
        print("✅ BabelDOC可用")
    else:
        print("❌ BabelDOC不可用")
