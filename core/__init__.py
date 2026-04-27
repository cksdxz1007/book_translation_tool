"""
Core optimization modules for document translation.

This package contains the core components for P0 optimization:
- chunking: Text chunking and segmentation strategies
- adapters: Translation service adapters and abstractions
- progress_tracker: Token-based progress tracking
- checkpoint_manager: Translation checkpoint management
- error_recovery: Error recovery and content splitting
"""

# Progress tracking
from core.progress_tracker import TokenProgressTracker, ProgressStats

# Checkpoint management
from core.checkpoint_manager import CheckpointManager

# Error recovery
from core.error_recovery import RecoveryResult, ContentSplitter, ErrorRecoveryManager

# Chunking
from core.chunking.token_chunker import TokenChunker

# Adapters
from core.adapters.format_adapter import FormatAdapter, TranslationUnit
from core.adapters.pdf_adapter import PDFAdapter
from core.adapters.markdown_adapter import MarkdownAdapter
from core.adapters.epub_adapter import EPUBAdapter

__all__ = [
    # Progress tracking
    'TokenProgressTracker',
    'ProgressStats',
    # Checkpoint management
    'CheckpointManager',
    # Error recovery
    'RecoveryResult',
    'ContentSplitter',
    'ErrorRecoveryManager',
    # Chunking
    'TokenChunker',
    # Adapters
    'FormatAdapter',
    'TranslationUnit',
    'PDFAdapter',
    'MarkdownAdapter',
    'EPUBAdapter',
]
