# gui/__init__.py
"""GUI components for the transcription application."""

from .main_window import MainWindow
from .transcription_view import TranscriptionView, EditableSegment
from .audio_player import AudioPlayer
from .batch_processor import BatchProcessorWidget

__all__ = [
    'MainWindow',
    'TranscriptionView',
    'EditableSegment',
    'AudioPlayer',
    'BatchProcessorWidget',
]
