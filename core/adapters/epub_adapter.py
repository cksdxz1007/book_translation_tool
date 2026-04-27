"""
EPUB format adapter for translation.

This module provides the EPUBAdapter class that handles EPUB files by:
1. Extracting EPUB contents using zipfile
2. Translating XHTML files as translation units
3. Repackaging the EPUB after translation
"""

from pathlib import Path
from typing import Any, Dict, List

import zipfile

from .format_adapter import FormatAdapter, TranslationUnit


class EPUBAdapter(FormatAdapter):
    """
    Adapter for EPUB files.

    Uses zipfile to extract EPUB contents and translates XHTML files
    as individual translation units before repackaging.
    """

    @property
    def format_name(self) -> str:
        """
        Get the format identifier.

        Returns:
            The format identifier string 'epub'
        """
        return "epub"

    async def prepare_for_translation(self) -> bool:
        """
        Prepare the EPUB file for translation by extracting its contents.

        Uses zipfile to extract all EPUB contents to a work directory.

        Returns:
            True if extraction was successful, False otherwise
        """
        import shutil

        self.work_dir = Path(f"data/work/{self.input_file_path.stem}")
        self.work_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(self.input_file_path, 'r') as zf:
                zf.extractall(self.work_dir)
            return True
        except Exception as e:
            print(f"Failed to extract EPUB: {e}")
            return False

    def get_translation_units(self) -> List[TranslationUnit]:
        """
        Get XHTML files as translation units.

        Scans the extracted EPUB contents for .xhtml files and returns
        them as translation units.

        Returns:
            List of TranslationUnit objects for each XHTML file found
        """
        units = []
        if not hasattr(self, 'work_dir'):
            return units

        for xhtml_file in self.work_dir.rglob("*.xhtml"):
            rel_path = xhtml_file.relative_to(self.work_dir)
            with open(xhtml_file, 'r', encoding='utf-8') as f:
                content = f.read()
            units.append(TranslationUnit(str(rel_path), content))
        return units

    async def save_unit_translation(self, unit_id: str, translated_content: str) -> bool:
        """
        Save translated XHTML file to disk.

        Writes the translated content to the corresponding file in the
        work directory.

        Args:
            unit_id: The relative path of the XHTML file
            translated_content: The translated content

        Returns:
            True if save was successful, False otherwise
        """
        if not hasattr(self, 'work_dir'):
            return False
        output_path = self.work_dir / unit_id
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(translated_content)
            return True
        except Exception as e:
            print(f"Failed to save translation: {e}")
            return False

    async def reconstruct_output(self, bilingual: bool = False) -> bytes:
        """
        Repackage the translated EPUB contents.

        Creates a new EPUB file by zipping all contents from the work
        directory.

        Args:
            bilingual: Whether to produce bilingual output (currently ignored
                     for EPUB format)

        Returns:
            The complete translated EPUB file as bytes, or empty bytes if
            reconstruction failed
        """
        if not hasattr(self, 'work_dir'):
            return b""

        output_path = Path(f"data/results/{self.output_file_path.name}")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file_path in self.work_dir.rglob("*"):
                    if file_path.is_file():
                        zf.write(file_path, file_path.relative_to(self.work_dir))
            with open(output_path, 'rb') as f:
                return f.read()
        except Exception as e:
            print(f"Failed to create EPUB: {e}")
            return b""

    async def resume_from_checkpoint(self, checkpoint_data: Dict[str, Any]) -> int:
        """
        Resume from a checkpoint.

        Currently returns 0 as checkpoint resume for EPUB is not yet
        implemented.

        Args:
            checkpoint_data: Dictionary containing checkpoint information

        Returns:
            Number of units already completed (always 0 for now)
        """
        return 0
