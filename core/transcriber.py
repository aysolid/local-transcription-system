# core/transcriber.py
"""
Core transcription engine using OpenAI Whisper for speech-to-text.
Supports multiple audio formats, language detection, and speaker diarization.
"""

import os
import json
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Callable, Dict, Any
from pathlib import Path
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)


@dataclass
class TranscriptionSegment:
    """Represents a single transcription segment."""
    start: float
    end: float
    text: str
    speaker: str = "Speaker 1"
    confidence: float = 1.0
    words: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert segment to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'TranscriptionSegment':
        """Create segment from dictionary."""
        return cls(**data)


class TranscriptionSystem:
    """
    Main transcription system using Whisper for speech-to-text.

    Features:
    - Multiple model sizes (tiny, base, small, medium, large)
    - Automatic language detection
    - Speaker diarization (optional)
    - Multiple audio format support
    - Progress callbacks for UI integration
    """

    SUPPORTED_FORMATS = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm', '.mp4', '.mpeg'}
    MODEL_SIZES = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']

    def __init__(self, model_size: str = "base", device: str = None):
        """
        Initialize the transcription system.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large)
            device: Device to run on ('cuda', 'cpu', or None for auto-detect)
        """
        self.model_size = model_size
        self.device = device
        self.model = None
        self._diarization_pipeline = None

    def load_model(self, progress_callback: Callable[[float, str], None] = None):
        """
        Load the Whisper model.

        Args:
            progress_callback: Callback function for progress updates
        """
        try:
            import whisper

            if progress_callback:
                progress_callback(10, "Loading Whisper model...")

            self.model = whisper.load_model(self.model_size, device=self.device)

            if progress_callback:
                progress_callback(20, "Model loaded successfully")

        except ImportError:
            raise ImportError(
                "Whisper is not installed. Please install it with: "
                "pip install openai-whisper"
            )

    def _load_diarization_pipeline(self):
        """Load the speaker diarization pipeline."""
        if self._diarization_pipeline is not None:
            return

        try:
            from pyannote.audio import Pipeline
            import torch

            # Use pyannote for diarization
            self._diarization_pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=os.environ.get("HF_TOKEN")
            )

            if torch.cuda.is_available():
                self._diarization_pipeline.to(torch.device("cuda"))

        except ImportError:
            print("Warning: pyannote.audio not installed. Speaker diarization unavailable.")
            self._diarization_pipeline = None
        except Exception as e:
            print(f"Warning: Could not load diarization pipeline: {e}")
            self._diarization_pipeline = None

    def transcribe_file(
        self,
        file_path: str,
        language: str = None,
        diarize: bool = False,
        progress_callback: Callable[[float, str], None] = None
    ) -> List[TranscriptionSegment]:
        """
        Transcribe an audio file.

        Args:
            file_path: Path to the audio file
            language: Language code (e.g., 'en', 'es', 'fr') or None for auto-detect
            diarize: Whether to perform speaker diarization
            progress_callback: Callback function for progress updates

        Returns:
            List of TranscriptionSegment objects
        """
        # Validate file
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        if file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported audio format: {file_path.suffix}. "
                f"Supported formats: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Load model if not already loaded
        if self.model is None:
            self.load_model(progress_callback)

        if progress_callback:
            progress_callback(25, "Processing audio file...")

        # Transcribe with Whisper
        try:
            transcribe_options = {
                "word_timestamps": True,
                "verbose": False
            }

            if language:
                transcribe_options["language"] = language

            if progress_callback:
                progress_callback(30, "Transcribing audio...")

            result = self.model.transcribe(str(file_path), **transcribe_options)

            if progress_callback:
                progress_callback(70, "Processing segments...")

        except Exception as e:
            raise RuntimeError(f"Transcription failed: {e}")

        # Convert Whisper result to TranscriptionSegments
        segments = self._convert_whisper_result(result)

        # Perform diarization if requested
        if diarize:
            if progress_callback:
                progress_callback(75, "Identifying speakers...")
            segments = self._apply_diarization(str(file_path), segments)

        if progress_callback:
            progress_callback(95, "Finalizing transcription...")

        return segments

    def _convert_whisper_result(self, result: dict) -> List[TranscriptionSegment]:
        """Convert Whisper result to TranscriptionSegment list."""
        segments = []

        for i, seg in enumerate(result.get("segments", [])):
            # Extract word-level data if available
            words = []
            if "words" in seg:
                words = [
                    {
                        "word": w.get("word", ""),
                        "start": w.get("start", 0),
                        "end": w.get("end", 0),
                        "confidence": w.get("probability", 1.0)
                    }
                    for w in seg["words"]
                ]

            # Calculate average confidence from words
            avg_confidence = 1.0
            if words:
                confidences = [w["confidence"] for w in words if "confidence" in w]
                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)

            segment = TranscriptionSegment(
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                text=seg.get("text", "").strip(),
                speaker="Speaker 1",  # Default speaker
                confidence=avg_confidence,
                words=words
            )
            segments.append(segment)

        return segments

    def _apply_diarization(
        self,
        audio_path: str,
        segments: List[TranscriptionSegment]
    ) -> List[TranscriptionSegment]:
        """Apply speaker diarization to segments."""
        self._load_diarization_pipeline()

        if self._diarization_pipeline is None:
            # Fallback: simple alternating speaker assignment
            return self._simple_speaker_assignment(segments)

        try:
            # Run diarization
            diarization = self._diarization_pipeline(audio_path)

            # Map speakers to segments based on time overlap
            for segment in segments:
                best_speaker = "Speaker 1"
                best_overlap = 0

                for turn, _, speaker in diarization.itertracks(yield_label=True):
                    # Calculate overlap
                    overlap_start = max(segment.start, turn.start)
                    overlap_end = min(segment.end, turn.end)
                    overlap = max(0, overlap_end - overlap_start)

                    if overlap > best_overlap:
                        best_overlap = overlap
                        best_speaker = speaker

                segment.speaker = best_speaker

        except Exception as e:
            print(f"Warning: Diarization failed: {e}")
            return self._simple_speaker_assignment(segments)

        return segments

    def _simple_speaker_assignment(
        self,
        segments: List[TranscriptionSegment]
    ) -> List[TranscriptionSegment]:
        """
        Simple speaker assignment based on pause detection.
        Assigns alternating speakers when there's a significant pause.
        """
        if not segments:
            return segments

        current_speaker = 1
        pause_threshold = 2.0  # seconds

        segments[0].speaker = f"Speaker {current_speaker}"

        for i in range(1, len(segments)):
            prev_segment = segments[i - 1]
            curr_segment = segments[i]

            # Check for significant pause
            gap = curr_segment.start - prev_segment.end
            if gap > pause_threshold:
                current_speaker = 3 - current_speaker  # Alternate between 1 and 2

            curr_segment.speaker = f"Speaker {current_speaker}"

        return segments

    def export_transcription(
        self,
        segments: List[TranscriptionSegment],
        format: str,
        output_path: str,
        include_metadata: bool = True
    ) -> str:
        """
        Export transcription to various formats.

        Args:
            segments: List of TranscriptionSegment objects
            format: Export format ('json', 'txt', 'srt', 'vtt', 'csv')
            output_path: Path for the output file
            include_metadata: Whether to include timing and speaker info

        Returns:
            Path to the exported file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        format = format.lower()

        if format == 'json':
            self._export_json(segments, output_path, include_metadata)
        elif format == 'txt':
            self._export_text(segments, output_path, include_metadata)
        elif format == 'srt':
            self._export_srt(segments, output_path)
        elif format == 'vtt':
            self._export_vtt(segments, output_path)
        elif format == 'csv':
            self._export_csv(segments, output_path)
        else:
            raise ValueError(f"Unsupported export format: {format}")

        return str(output_path)

    def _export_json(
        self,
        segments: List[TranscriptionSegment],
        output_path: Path,
        include_metadata: bool
    ):
        """Export to JSON format."""
        data = {
            "segments": [seg.to_dict() for seg in segments],
            "metadata": {
                "total_segments": len(segments),
                "total_duration": segments[-1].end if segments else 0,
                "speakers": list(set(seg.speaker for seg in segments))
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _export_text(
        self,
        segments: List[TranscriptionSegment],
        output_path: Path,
        include_metadata: bool
    ):
        """Export to plain text format."""
        with open(output_path, 'w', encoding='utf-8') as f:
            current_speaker = None

            for seg in segments:
                if include_metadata and seg.speaker != current_speaker:
                    f.write(f"\n[{seg.speaker}]\n")
                    current_speaker = seg.speaker

                f.write(f"{seg.text}\n")

    def _export_srt(self, segments: List[TranscriptionSegment], output_path: Path):
        """Export to SRT subtitle format."""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments, 1):
                start_time = self._format_timestamp_srt(seg.start)
                end_time = self._format_timestamp_srt(seg.end)

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{seg.text}\n\n")

    def _export_vtt(self, segments: List[TranscriptionSegment], output_path: Path):
        """Export to WebVTT subtitle format."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")

            for i, seg in enumerate(segments, 1):
                start_time = self._format_timestamp_vtt(seg.start)
                end_time = self._format_timestamp_vtt(seg.end)

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"<v {seg.speaker}>{seg.text}\n\n")

    def _export_csv(self, segments: List[TranscriptionSegment], output_path: Path):
        """Export to CSV format."""
        import csv

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Start', 'End', 'Speaker', 'Text', 'Confidence'])

            for seg in segments:
                writer.writerow([
                    f"{seg.start:.2f}",
                    f"{seg.end:.2f}",
                    seg.speaker,
                    seg.text,
                    f"{seg.confidence:.2f}"
                ])

    @staticmethod
    def _format_timestamp_srt(seconds: float) -> str:
        """Format timestamp for SRT format (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_timestamp_vtt(seconds: float) -> str:
        """Format timestamp for VTT format (HH:MM:SS.mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    def get_supported_languages(self) -> Dict[str, str]:
        """Get dictionary of supported languages."""
        return {
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "nl": "Dutch",
            "ru": "Russian",
            "zh": "Chinese",
            "ja": "Japanese",
            "ko": "Korean",
            "ar": "Arabic",
            "hi": "Hindi",
            "tr": "Turkish",
            "pl": "Polish",
            "uk": "Ukrainian",
            "vi": "Vietnamese",
            "th": "Thai",
            "id": "Indonesian",
            "ms": "Malay",
        }

    def detect_language(self, file_path: str) -> str:
        """
        Detect the language of an audio file.

        Args:
            file_path: Path to the audio file

        Returns:
            Detected language code
        """
        if self.model is None:
            self.load_model()

        try:
            import whisper

            # Load audio and detect language
            audio = whisper.load_audio(file_path)
            audio = whisper.pad_or_trim(audio)

            mel = whisper.log_mel_spectrogram(audio).to(self.model.device)
            _, probs = self.model.detect_language(mel)

            detected_lang = max(probs, key=probs.get)
            return detected_lang

        except Exception as e:
            print(f"Language detection failed: {e}")
            return "en"  # Default to English
