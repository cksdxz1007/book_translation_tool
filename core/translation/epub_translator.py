"""
EPUB Translator for document translation.

Manages the complete EPUB translation workflow with checkpoint and progress tracking.
"""

import os
import time
import asyncio
import logging
import zipfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field

from core.checkpoint_manager import CheckpointManager
from core.progress_tracker import TokenProgressTracker, ProgressStats
from core.error_recovery import ErrorRecoveryManager
from .html_translator import HTMLTranslator, TranslateConfig

logger = logging.getLogger(__name__)


@dataclass
class TranslationUnit:
    """翻译单元"""
    unit_id: str
    content: str
    translated: str = ""
    status: str = "pending"  # pending, completed, failed
    error: str = ""


@dataclass
class TranslateResult:
    """翻译结果"""
    success: bool
    output_path: str = ""
    total_units: int = 0
    completed_units: int = 0
    failed_units: int = 0
    elapsed_seconds: float = 0
    error: str = ""


class EPUBTranslator:
    """
    EPUB 翻译器

    Features:
    - 断点续传（CheckpointManager）
    - 精确进度追踪（TokenProgressTracker）
    - 错误恢复（ErrorRecoveryManager）
    - 单语/双语模式分离
    - 临时文件自动清理

    Usage:
        config = TranslateConfig(
            api_key='xxx',
            model='deepseek-chat',
            base_url='https://api.deepseek.com/v1',
            lang_in='en',
            lang_out='zh'
        )

        translator = EPUBTranslator(
            input_path='/path/to/input.epub',
            output_path='/path/to/output.epub',
            html_translator=HTMLTranslator(config),
            translation_style='mono'  # or 'dual'
        )

        result = translator.translate()
    """

    def __init__(
        self,
        input_path: str,
        output_path: str,
        html_translator: HTMLTranslator,
        translation_style: str = 'mono',
        task_id: Optional[str] = None,
        checkpoint_manager: Optional[CheckpointManager] = None,
        progress_callback: Optional[Callable[[ProgressStats], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.html_translator = html_translator
        self.translation_style = translation_style
        self.task_id = task_id or f"epub_{int(time.time())}"

        # 核心模块
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.progress_tracker = TokenProgressTracker()
        self.error_recovery = ErrorRecoveryManager(log_callback=log_callback)

        # 回调函数
        self.progress_callback = progress_callback
        self.log_callback = log_callback

        # 工作目录
        self.work_dir = Path(f"data/work/{self.input_path.stem}")
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 翻译单元
        self.units: List[TranslationUnit] = []
        self.completed_count = 0
        self.failed_count = 0

    def _log(self, message: str):
        """记录日志"""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)

    def _update_progress(self):
        """更新进度"""
        stats = self.progress_tracker.get_stats()
        if self.progress_callback:
            self.progress_callback(stats)

    def _parse_epub(self) -> List[TranslationUnit]:
        """
        解析 EPUB 文件

        Returns:
            翻译单元列表
        """
        self._log("解析 EPUB 文件...")

        # 清理旧的工作目录
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)

        # 提取 EPUB
        self.work_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(self.input_path, 'r') as zf:
            zf.extractall(self.work_dir)

        # 获取所有 XHTML 文件
        units = []
        for xhtml_file in self.work_dir.rglob("*.xhtml"):
            rel_path = xhtml_file.relative_to(self.work_dir)
            with open(xhtml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            units.append(TranslationUnit(
                unit_id=str(rel_path),
                content=content
            ))

        self._log(f"找到 {len(units)} 个待翻译单元")
        return units

    def _save_translated_unit(self, unit: TranslationUnit):
        """保存翻译后的单元"""
        output_file = self.work_dir / unit.unit_id
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(unit.translated)

    def _rebuild_epub(self) -> str:
        """重建 EPUB 文件"""
        self._log("重建 EPUB 文件...")

        # 清理旧的结果文件
        if self.output_path.exists():
            self.output_path.unlink()

        # 创建新的 EPUB
        with zipfile.ZipFile(self.output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in self.work_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(self.work_dir)
                    zf.write(file_path, arcname)

        return str(self.output_path)

    def _cleanup(self):
        """清理临时文件"""
        self._log("清理临时文件...")
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)

    def _start_checkpoint(self):
        """开始检查点"""
        config = {
            'input_path': str(self.input_path),
            'output_path': str(self.output_path),
            'translation_style': self.translation_style,
            'lang_in': self.html_translator.config.lang_in,
            'lang_out': self.html_translator.config.lang_out
        }
        self.checkpoint_manager.start_job(
            translation_id=self.task_id,
            file_type='epub',
            config=config,
            input_file_path=str(self.input_path)
        )

    def _save_checkpoint(self, unit: TranslationUnit, index: int):
        """保存检查点"""
        self.checkpoint_manager.save_checkpoint(
            translation_id=self.task_id,
            chunk_index=index,
            original_text=unit.content,
            translated_text=unit.translated,
            chunk_data={'unit_id': unit.unit_id, 'status': unit.status}
        )
        self.checkpoint_manager.update_job_progress(
            self.task_id,
            current_chunk_index=index,
            completed_chunks=self.completed_count
        )

    def _finish_checkpoint(self):
        """完成检查点"""
        self.checkpoint_manager.mark_completed(self.task_id)

    def translate(self) -> TranslateResult:
        """
        执行翻译

        Returns:
            TranslateResult: 翻译结果
        """
        start_time = time.time()
        self._log(f"开始 EPUB 翻译，模式: {'单语' if self.translation_style == 'mono' else '双语'}")

        try:
            # 开始检查点
            self._start_checkpoint()

            # 解析 EPUB
            self.units = self._parse_epub()
            total_units = len(self.units)

            if total_units == 0:
                return TranslateResult(
                    success=False,
                    error="未找到可翻译的内容"
                )

            # 初始化进度追踪
            self.progress_tracker.start()

            # 注册所有翻译单元的 token 数
            for unit in self.units:
                # 估算 token 数（按字符数/4 估算）
                token_count = len(unit.content) // 4
                self.progress_tracker.register_chunk(token_count)

            # 翻译每个单元
            unit_start_time = time.time()
            for i, unit in enumerate(self.units):
                self._log(f"翻译单元 {i+1}/{total_units}: {unit.unit_id}")

                try:
                    # 翻译 HTML 内容
                    if self.translation_style == 'dual':
                        unit.translated = self.html_translator.translate_dual(
                            unit.content,
                            log_callback=self._log
                        )
                    else:
                        unit.translated = self.html_translator.translate_mono(
                            unit.content,
                            log_callback=self._log
                        )

                    unit.status = 'completed'
                    self.completed_count += 1

                    # 保存翻译后的文件
                    self._save_translated_unit(unit)

                    # 保存检查点
                    self._save_checkpoint(unit, i)

                    # 更新进度（使用单元索引，但使用实际耗时）
                    unit_elapsed = time.time() - unit_start_time
                    self.progress_tracker.mark_completed(i, unit_elapsed)
                    self._update_progress()

                    self._log(f"单元 {i+1} 翻译完成")
                    unit_start_time = time.time()  # 重置计时器

                except Exception as e:
                    unit.status = 'failed'
                    unit.error = str(e)
                    self.failed_count += 1
                    self.progress_tracker.mark_failed(i)
                    self._log(f"单元 {i+1} 翻译失败: {e}")
                    unit_start_time = time.time()  # 重置计时器
                    # 继续下一个单元

            # 重建 EPUB
            output_path = self._rebuild_epub()

            # 完成检查点
            self._finish_checkpoint()

            # 清理临时文件
            self._cleanup()

            elapsed = time.time() - start_time
            self._log(f"翻译完成！耗时: {elapsed:.2f}秒")

            return TranslateResult(
                success=True,
                output_path=output_path,
                total_units=total_units,
                completed_units=self.completed_count,
                failed_units=self.failed_count,
                elapsed_seconds=elapsed
            )

        except Exception as e:
            elapsed = time.time() - start_time
            self._log(f"翻译失败: {e}")
            return TranslateResult(
                success=False,
                error=str(e),
                elapsed_seconds=elapsed
            )

    def resume(self) -> TranslateResult:
        """
        从检查点恢复翻译

        Returns:
            TranslateResult: 翻译结果
        """
        start_time = time.time()
        self._log("从检查点恢复翻译...")

        try:
            # 加载检查点
            checkpoint = self.checkpoint_manager.load_checkpoint(self.task_id)
            if not checkpoint:
                self._log("未找到检查点，开始新翻译")
                return self.translate()

            resume_from_index = checkpoint['resume_from_index']
            self._log(f"从单元 {resume_from_index + 1} 开始恢复")

            # 解析 EPUB
            self.units = self._parse_epub()
            total_units = len(self.units)

            # 加载已完成的翻译
            saved_chunks = checkpoint.get('chunks', [])
            for chunk in saved_chunks:
                unit_id = chunk.get('chunk_data', {}).get('unit_id')
                translated_text = chunk.get('translated_text')
                if unit_id and translated_text:
                    for unit in self.units:
                        if unit.unit_id == unit_id:
                            unit.translated = translated_text
                            unit.status = 'completed'
                            self.completed_count += 1

            # 继续翻译
            self.progress_tracker.start()

            for i in range(resume_from_index, total_units):
                unit = self.units[i]
                self._log(f"翻译单元 {i+1}/{total_units}: {unit.unit_id}")

                if unit.status == 'completed':
                    self._log(f"单元 {i+1} 已完成，跳过")
                    continue

                try:
                    if self.translation_style == 'dual':
                        unit.translated = self.html_translator.translate_dual(
                            unit.content,
                            log_callback=self._log
                        )
                    else:
                        unit.translated = self.html_translator.translate_mono(
                            unit.content,
                            log_callback=self._log
                        )

                    unit.status = 'completed'
                    self.completed_count += 1
                    self._save_translated_unit(unit)
                    self._save_checkpoint(unit, i)
                    self.progress_tracker.mark_completed(i, time.time() - start_time)
                    self._update_progress()

                except Exception as e:
                    unit.status = 'failed'
                    unit.error = str(e)
                    self.failed_count += 1
                    self.progress_tracker.mark_failed(i)
                    self._log(f"单元 {i+1} 翻译失败: {e}")

            # 重建 EPUB
            output_path = self._rebuild_epub()
            self._finish_checkpoint()
            self._cleanup()

            elapsed = time.time() - start_time
            self._log(f"恢复翻译完成！耗时: {elapsed:.2f}秒")

            return TranslateResult(
                success=True,
                output_path=output_path,
                total_units=total_units,
                completed_units=self.completed_count,
                failed_units=self.failed_count,
                elapsed_seconds=elapsed
            )

        except Exception as e:
            elapsed = time.time() - start_time
            return TranslateResult(
                success=False,
                error=str(e),
                elapsed_seconds=elapsed
            )

    def get_progress(self) -> ProgressStats:
        """获取当前进度"""
        return self.progress_tracker.get_stats()

    def abort(self):
        """中止翻译"""
        self.checkpoint_manager.mark_interrupted(self.task_id)
        self._cleanup()