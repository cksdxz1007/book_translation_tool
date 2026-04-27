"""
PDF format adapter using BabelDOC.

This adapter uses BabelDOC for professional PDF translation with layout preservation.
BabelDOC handles chunking internally, so this adapter treats the entire PDF as a single
translation unit.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .format_adapter import FormatAdapter, TranslationUnit

logger = logging.getLogger(__name__)


class PDFAdapter(FormatAdapter):
    """
    Adapter for PDF files using BabelDOC.

    BabelDOC handles PDF translation with layout preservation. The adapter
    provides the interface between the generic translation system and
    BabelDOC's specific implementation.
    """

    def __init__(
        self,
        input_file_path: str,
        output_file_path: str,
        config: Dict[str, Any]
    ) -> None:
        """
        Initialize the PDF adapter with BabelDOC integration.

        Args:
            input_file_path: Path to the source PDF file to translate
            output_file_path: Path where the translated output will be saved
            config: Configuration dictionary with translation settings
        """
        super().__init__(input_file_path, output_file_path, config)
        self._translation_result: Optional[Dict[str, Any]] = None
        self._completed_units: set = set()

    @property
    def format_name(self) -> str:
        """Return the format identifier."""
        return "pdf"

    async def prepare_for_translation(self) -> bool:
        """
        Prepare the PDF file for translation by running BabelDOC.

        This method validates the input file exists and triggers the actual
        BabelDOC translation. The translation is performed synchronously
        since BabelDOC handles its own async internally.

        Returns:
            True if translation was successful, False otherwise
        """
        # Validate input file exists
        if not self.input_file_path.exists():
            logger.error(f"PDF file does not exist: {self.input_file_path}")
            return False

        try:
            # Import BabelDOC translator
            from services.pdf_translator_babeldoc import BabelDocTranslator

            # Get translation settings from config
            api_key = self.config.get('api_key')
            model = self.config.get('model', 'deepseek-chat')
            base_url = self.config.get('base_url')
            lang_in = self.config.get('source_lang', 'en')
            lang_out = self.config.get('target_lang', 'zh')

            # Create output directory
            output_dir = str(self.output_file_path.parent)
            os.makedirs(output_dir, exist_ok=True)

            # Create BabelDOC translator
            translator = BabelDocTranslator(
                api_key=api_key,
                model=model,
                base_url=base_url
            )

            # Check if BabelDOC is available
            if not translator.is_available():
                logger.error("BabelDOC is not available")
                return False

            logger.info(f"Starting BabelDOC translation: {self.input_file_path}")
            logger.info(f"Output directory: {output_dir}")
            logger.info(f"Language: {lang_in} -> {lang_out}")

            # Run BabelDOC translation
            result = translator.translate_pdf(
                pdf_path=str(self.input_file_path),
                output_dir=output_dir,
                lang_in=lang_in,
                lang_out=lang_out,
                progress_callback=None  # Could add progress tracking here
            )

            self._translation_result = result

            if result.get('success'):
                logger.info(f"BabelDOC translation completed successfully")
                logger.info(f"Mono PDF: {result.get('mono_pdf_path')}")
                logger.info(f"Dual PDF: {result.get('dual_pdf_path')}")
                return True
            else:
                logger.error(f"BabelDOC translation failed: {result.get('error')}")
                return False

        except Exception as e:
            logger.error(f"Failed to prepare PDF for translation: {e}")
            return False

    def get_translation_units(self) -> List[TranslationUnit]:
        """
        Get translation units from the PDF file.

        Since BabelDOC handles chunking internally and already completed
        the translation in prepare_for_translation(), this returns a single
        unit representing the already-translated PDF.

        Returns:
            List containing a single TranslationUnit for the entire PDF
        """
        # The translation was already done by BabelDOC in prepare_for_translation
        # We return a single unit to represent the whole PDF
        if self._translation_result:
            result_path = self._translation_result.get('mono_pdf_path') or \
                         self._translation_result.get('no_watermark_mono_pdf_path')
            if result_path:
                return [TranslationUnit("full_pdf", result_path)]

        return [TranslationUnit("full_pdf", str(self.input_file_path))]

    async def save_unit_translation(self, unit_id: str, translated_content: str) -> bool:
        """
        Save the translation of a single unit.

        Since BabelDOC handles translation internally and already saved
        the results to disk, this method just tracks completion.

        Args:
            unit_id: The unique identifier of the TranslationUnit
            translated_content: The translated content (unused for PDF)

        Returns:
            True indicating success
        """
        # BabelDOC handles translation and saving internally
        self._completed_units.add(unit_id)
        return True

    async def reconstruct_output(self, bilingual: bool = False) -> bytes:
        """
        Reconstruct the final PDF output.

        Reads the translated PDF bytes from the BabelDOC output directory.
        If bilingual is True, returns the dual-language PDF if available.

        Args:
            bilingual: Whether to produce bilingual output

        Returns:
            The complete translated PDF file as bytes
        """
        if not self._translation_result:
            logger.error("No translation result available")
            return b""

        try:
            # Determine which PDF to return based on bilingual flag
            if bilingual:
                pdf_path = self._translation_result.get('dual_pdf_path') or \
                          self._translation_result.get('no_watermark_dual_pdf_path')
            else:
                pdf_path = self._translation_result.get('mono_pdf_path') or \
                          self._translation_result.get('no_watermark_mono_pdf_path')

            if not pdf_path:
                logger.error("No PDF path in translation result")
                return b""

            # Read and return the PDF bytes
            pdf_bytes = Path(pdf_path).read_bytes()
            logger.info(f"Reconstructed output PDF: {len(pdf_bytes)} bytes")
            return pdf_bytes

        except Exception as e:
            logger.error(f"Failed to reconstruct output PDF: {e}")
            return b""

    async def resume_from_checkpoint(self, checkpoint_data: Dict[str, Any]) -> int:
        """
        Resume translation from a checkpoint.

        For PDF/BabelDOC, if a checkpoint exists with translation result,
        restore it. Otherwise, BabelDOC doesn't support incremental resume
        and would need to restart translation.

        Args:
            checkpoint_data: Dictionary containing checkpoint information

        Returns:
            Number of units already completed (0 or 1 for PDF)
        """
        # Check if we have a previous translation result in checkpoint
        translation_result = checkpoint_data.get('translation_result')
        if translation_result:
            self._translation_result = translation_result
            self._completed_units = set(checkpoint_data.get('completed_units', []))
            logger.info("Restored translation state from checkpoint")
            return len(self._completed_units)

        # No valid checkpoint - BabelDOC would need to restart
        logger.info("No valid checkpoint found, translation needs to restart")
        return 0