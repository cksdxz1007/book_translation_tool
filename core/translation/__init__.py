"""
Translation module for document translation.

Provides classes for translating various document formats.
"""

from .api_client import APIClient
from .html_translator import HTMLTranslator
from .epub_translator import EPUBTranslator

__all__ = ['APIClient', 'HTMLTranslator', 'EPUBTranslator']