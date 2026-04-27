"""
Translation service adapters module.

Provides adapter classes for integrating various translation services:
- OpenAI-compatible API adapters
- Ollama local inference adapters
- BabelDOC professional translation adapters
- Format adapters for PDF, ePub, Markdown files

All adapters follow a common interface for consistent translation operations.
"""

from core.adapters.format_adapter import FormatAdapter, TranslationUnit
from core.adapters.pdf_adapter import PDFAdapter
from core.adapters.markdown_adapter import MarkdownAdapter
from core.adapters.epub_adapter import EPUBAdapter

__all__ = [
    "FormatAdapter",
    "TranslationUnit",
    "PDFAdapter",
    "MarkdownAdapter",
    "EPUBAdapter",
]
