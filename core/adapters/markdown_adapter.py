"""
Markdown format adapter with token-based chunking.

This adapter uses TokenChunker to split Markdown content into translation units
while respecting natural boundaries (paragraphs and sentences).
"""

import logging
from typing import Any, Dict, List

from .format_adapter import FormatAdapter, TranslationUnit
from core.chunking.token_chunker import TokenChunker

logger = logging.getLogger(__name__)


class MarkdownAdapter(FormatAdapter):
    """
    Adapter for Markdown files with token-based chunking.

    Uses TokenChunker to split content into appropriately sized chunks
    with 80% soft limit, respecting natural text boundaries.
    """

    def __init__(
        self,
        input_file_path: str,
        output_file_path: str,
        config: Dict[str, Any]
    ) -> None:
        """
        Initialize the Markdown adapter.

        Args:
            input_file_path: Path to the source Markdown file to translate
            output_file_path: Path where the translated output will be saved
            config: Configuration dictionary with translation settings
        """
        super().__init__(input_file_path, output_file_path, config)
        max_tokens = config.get('max_tokens', 800)
        soft_limit = config.get('soft_limit', 0.8)
        self.chunker = TokenChunker(max_tokens=max_tokens, soft_limit_ratio=soft_limit)
        self.content: str = ""
        self.translated_chunks: Dict[str, str] = {}
        self.original_chunks: Dict[str, str] = {}  # 保存原文

    @property
    def format_name(self) -> str:
        """Return the format identifier."""
        return "markdown"

    async def prepare_for_translation(self) -> bool:
        """
        Read and parse Markdown file.

        Returns:
            True if file was read successfully, False otherwise
        """
        try:
            with open(self.input_file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
            logger.info(f"Loaded Markdown file: {len(self.content)} characters")
            return True
        except Exception as e:
            logger.error(f"Failed to read Markdown file: {e}")
            return False

    def get_translation_units(self) -> List[TranslationUnit]:
        """
        Split Markdown into token-based chunks with context.

        Uses TokenChunker to create chunks with:
        - context_before: Last paragraph of previous chunk
        - context_after: First paragraph of next chunk
        - main_content: The actual content to translate

        Returns:
            List of TranslationUnit objects
        """
        chunks = self.chunker.chunk_text(self.content)
        units = []
        for i, chunk in enumerate(chunks):
            unit_id = f"chunk_{i}"
            self.original_chunks[unit_id] = chunk['main_content']  # 保存原文
            units.append(TranslationUnit(
                unit_id,
                chunk['main_content'],
                {
                    'context_before': chunk['context_before'],
                    'context_after': chunk['context_after']
                }
            ))
        return units

    async def save_unit_translation(self, unit_id: str, translated_content: str) -> bool:
        """
        Save translated chunk.

        Stores translated content in memory for later reconstruction.

        Args:
            unit_id: The unique identifier of the TranslationUnit
            translated_content: The translated text content

        Returns:
            True if saving was successful, False otherwise
        """
        try:
            self.translated_chunks[unit_id] = translated_content
            return True
        except Exception as e:
            logger.error(f"Failed to save translation for {unit_id}: {e}")
            return False

    async def reconstruct_output(self, bilingual: bool = False) -> bytes:
        """
        Reconstruct Markdown from translated chunks.

        Joins all translated chunks with double newlines to preserve
        paragraph structure. If bilingual is True, returns source and
        translated text interleaved.

        Args:
            bilingual: Whether to produce bilingual output

        Returns:
            The complete translated Markdown file as bytes
        """
        if not self.translated_chunks:
            logger.warning("No translated chunks available")
            return b""

        try:
            if bilingual:
                # 双语模式：原文和译文交替显示
                lines = []
                for unit_id in sorted(self.translated_chunks.keys()):
                    original = self.original_chunks.get(unit_id, '')
                    translated = self.translated_chunks.get(unit_id, '')
                    # 添加分隔线
                    lines.append('')
                    lines.append('---')
                    lines.append('')
                    lines.append(f"**原文 (Original):**")
                    lines.append('')
                    lines.append(original)
                    lines.append('')
                    lines.append(f"**译文 (Translation):**")
                    lines.append('')
                    lines.append(translated)
                output = '\n'.join(lines)
            else:
                # 单语模式：只保留译文
                output = '\n\n'.join(self.translated_chunks.values())
            return output.encode('utf-8')
        except Exception as e:
            logger.error(f"Failed to reconstruct output: {e}")
            return b""

    async def resume_from_checkpoint(self, checkpoint_data: Dict[str, Any]) -> int:
        """
        Resume from checkpoint.

        Restores translated chunks from checkpoint data to allow
        translation to continue from where it left off.

        Args:
            checkpoint_data: Dictionary containing checkpoint information
                           (completed units, translations, adapter state)

        Returns:
            Number of units that were already completed in the checkpoint
        """
        translated_chunks = checkpoint_data.get('translated_chunks', {})
        if translated_chunks:
            self.translated_chunks = translated_chunks
            logger.info(f"Restored {len(translated_chunks)} chunks from checkpoint")
            return len(translated_chunks)

        logger.info("No checkpoint data found")
        return 0
