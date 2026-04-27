"""
Text chunking and segmentation module.

Provides strategies for splitting large documents into manageable chunks
for translation processing, including:
- Semantic chunking by meaning boundaries
- Length-based chunking with configurable limits
- Overlap strategies for context preservation
"""

from core.chunking.token_chunker import TokenChunker

__all__ = ["TokenChunker"]
