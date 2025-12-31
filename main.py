#!/usr/bin/env python3
# main.py
"""
Local Transcription System - Main Entry Point

A desktop application for transcribing audio files using OpenAI Whisper.
Provides a full-featured GUI with batch processing, search, and analysis capabilities.
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def setup_logging(level: str = "INFO", log_file: str = None):
    """Configure application logging."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    handlers = [logging.StreamHandler()]

    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Local Transcription System - Audio transcription with Whisper"
    )

    parser.add_argument(
        '--file', '-f',
        type=str,
        help='Audio file to transcribe on startup'
    )

    parser.add_argument(
        '--model', '-m',
        type=str,
        choices=['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3'],
        default='base',
        help='Whisper model size (default: base)'
    )

    parser.add_argument(
        '--language', '-l',
        type=str,
        default=None,
        help='Language code (e.g., en, es, fr) or auto-detect if not specified'
    )

    parser.add_argument(
        '--no-gui',
        action='store_true',
        help='Run in CLI mode without GUI'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file path (for CLI mode)'
    )

    parser.add_argument(
        '--format',
        type=str,
        choices=['json', 'txt', 'srt', 'vtt', 'csv'],
        default='json',
        help='Output format (default: json)'
    )

    parser.add_argument(
        '--diarize',
        action='store_true',
        help='Enable speaker diarization'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    parser.add_argument(
        '--version', '-v',
        action='version',
        version='Local Transcription System 1.0.0'
    )

    return parser.parse_args()


def run_cli(args):
    """Run in CLI mode without GUI."""
    from core.transcriber import TranscriptionSystem

    if not args.file:
        print("Error: --file is required in CLI mode")
        sys.exit(1)

    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    print(f"Loading Whisper model '{args.model}'...")
    trans_system = TranscriptionSystem(model_size=args.model)

    def progress_callback(progress, message):
        print(f"[{progress:5.1f}%] {message}")

    print(f"Transcribing: {args.file}")
    try:
        segments = trans_system.transcribe_file(
            args.file,
            language=args.language,
            diarize=args.diarize,
            progress_callback=progress_callback
        )

        # Determine output path
        if args.output:
            output_path = args.output
        else:
            base_name = os.path.splitext(args.file)[0]
            ext_map = {'json': '.json', 'txt': '.txt', 'srt': '.srt', 'vtt': '.vtt', 'csv': '.csv'}
            output_path = base_name + ext_map.get(args.format, '.json')

        # Export
        trans_system.export_transcription(
            segments,
            args.format,
            output_path
        )

        print(f"\nTranscription complete!")
        print(f"Segments: {len(segments)}")
        print(f"Output: {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def run_gui(args):
    """Run the GUI application."""
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from gui.main_window import MainWindow
    except ImportError as e:
        print(f"Error: PyQt6 is required for GUI mode. Install with: pip install PyQt6")
        print(f"Details: {e}")
        sys.exit(1)

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Local Transcription System")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("LocalTranscription")

    # Set application style
    app.setStyle("Fusion")

    # Create main window
    window = MainWindow()

    # Open file if provided
    if args.file and os.path.exists(args.file):
        window.current_file = args.file
        window.status_label.setText(f"Loaded: {os.path.basename(args.file)}")

    # Show window
    window.show()

    # Run event loop
    sys.exit(app.exec())


def main():
    """Main entry point."""
    args = parse_args()

    # Setup logging
    setup_logging(args.log_level)

    # Log startup info
    logging.info("Starting Local Transcription System")
    logging.info(f"Model: {args.model}")
    if args.language:
        logging.info(f"Language: {args.language}")

    # Run in appropriate mode
    if args.no_gui:
        run_cli(args)
    else:
        run_gui(args)


if __name__ == "__main__":
    main()
