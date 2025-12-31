# plugins/__init__.py
"""Plugin system for extending transcription functionality."""

from .base_plugin import BasePlugin, PluginManager, PluginManagerDialog
from .vocabulary_enhancer import VocabularyEnhancerPlugin

__all__ = [
    'BasePlugin',
    'PluginManager',
    'PluginManagerDialog',
    'VocabularyEnhancerPlugin',
]
