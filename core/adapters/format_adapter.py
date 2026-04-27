"""
Format adapter abstract base class for file format translation.

This module provides the abstract interface for adapting various file formats
(PDF, ePub, Markdown, etc.) to the generic translation system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TranslationUnit:
    """
    Represents a single unit of text to translate.

    Attributes:
        unit_id: Unique identifier for this translation unit
        content: The text content to be translated
        metadata: Optional dictionary containing additional context
                 (e.g., page number, chapter, formatting info)
    """

    unit_id: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class FormatAdapter(ABC):
    """
    Abstract interface for adapting a file format to the generic translation system.

    Each format adapter is responsible for:
    1. Preparing the input file for translation
    2. Breaking it into translation units
    3. Saving translated units
    4. Reconstructing the final output file
    5. Supporting resume from checkpoint

    Concrete implementations must override all abstract methods to provide
    format-specific behavior for PDF, ePub, Markdown, and other formats.
    """

    def __init__(
        self,
        input_file_path: str,
        output_file_path: str,
        config: Dict[str, Any]
    ) -> None:
        """
        Initialize the format adapter.

        Args:
            input_file_path: Path to the source file to translate
            output_file_path: Path where the translated output will be saved
            config: Configuration dictionary with translation settings
        """
        self.input_file_path = Path(input_file_path)
        self.output_file_path = Path(output_file_path)
        self.config = config

    @abstractmethod
    async def prepare_for_translation(self) -> bool:
        """
        Prepare the file for translation.

        This method is called once before translation begins and should
        perform any necessary preprocessing (e.g., parsing the file,
        extracting text, analyzing structure).

        Returns:
            True if preparation was successful, False otherwise
        """
        pass

    @abstractmethod
    def get_translation_units(self) -> List[TranslationUnit]:
        """
        Get all translation units from the prepared file.

        This method returns all units that need to be translated.
        Each unit should have a unique ID and the content to translate.

        Returns:
            List of TranslationUnit objects representing the content to translate
        """
        pass

    @abstractmethod
    async def save_unit_translation(self, unit_id: str, translated_content: str) -> bool:
        """
        Save the translation of a single unit.

        Called after each unit is translated to persist the result.
        The adapter may store this in memory, to disk, or another storage.

        Args:
            unit_id: The unique identifier of the TranslationUnit
            translated_content: The translated text content

        Returns:
            True if saving was successful, False otherwise
        """
        pass

    @abstractmethod
    async def reconstruct_output(self, bilingual: bool = False) -> bytes:
        """
        Reconstruct the final output file from translated units.

        This method assembles all translated content into the final
        output file format. If bilingual is True, the output should
        include both source and translated text.

        Args:
            bilingual: Whether to produce bilingual output with both
                      source and translated text

        Returns:
            The complete translated file as bytes
        """
        pass

    @abstractmethod
    async def resume_from_checkpoint(self, checkpoint_data: Dict[str, Any]) -> int:
        """
        Restore adapter state from a checkpoint.

        Allows translation to resume from a specific point after
        interruption. The checkpoint data typically contains completed
        unit IDs and their translations.

        Args:
            checkpoint_data: Dictionary containing checkpoint information
                           (completed units, translations, adapter state)

        Returns:
            Number of units that were already completed in the checkpoint
        """
        pass

    @property
    @abstractmethod
    def format_name(self) -> str:
        """
        Get the format identifier.

        Returns a short string identifying the format this adapter handles
        (e.g., 'pdf', 'epub', 'markdown').

        Returns:
            The format identifier string
        """
        pass
