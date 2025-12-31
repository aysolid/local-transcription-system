# gui/main_window.py
"""
Main application window for the Local Transcription System.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QMenuBar, QMenu, QToolBar, QStatusBar, QDockWidget, QLabel,
    QLineEdit, QListWidget, QPushButton, QFileDialog, QMessageBox,
    QActionGroup, QSplitter, QProgressBar, QComboBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence

from typing import Optional, List, Dict, Any
import os

from core.transcriber import TranscriptionSystem, TranscriptionSegment
from core.search_engine import SearchAnalyzer, TranscriptionIndex
from core.batch_manager import BatchManager
from gui.transcription_view import TranscriptionView
from gui.audio_player import AudioPlayer
from gui.batch_processor import BatchProcessorWidget
from plugins.base_plugin import PluginManager, PluginManagerDialog
from utils.language_utils import LanguageManager, language_manager


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()

        # Initialize core components
        self.trans_system = TranscriptionSystem()
        self.search_analyzer = SearchAnalyzer()
        self.transcription_index = TranscriptionIndex()
        self.plugin_manager = PluginManager()
        self.language_manager = language_manager

        # Data storage
        self.current_file: Optional[str] = None
        self.transcription_data: Optional[List[TranscriptionSegment]] = None
        self.transcription_view: Optional[TranscriptionView] = None

        # Setup UI
        self.setWindowTitle(self.language_manager.t("app_title"))
        self.setMinimumSize(1200, 800)

        self.setup_ui()
        self.setup_menus()
        self.setup_toolbar()
        self.setup_statusbar()
        self.setup_connections()

        # Load plugins
        self._load_plugins()

    def setup_ui(self):
        """Setup the main UI."""
        # Central widget with tabs
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        layout = QVBoxLayout(self.central_widget)

        # Tab widget for different views
        self.tab_widget = QTabWidget()

        # Transcription tab
        self.transcription_tab = QWidget()
        self.transcription_layout = QVBoxLayout(self.transcription_tab)

        # Placeholder for transcription view
        self.transcription_placeholder = QLabel(
            "Open an audio file to start transcribing\n\n"
            "Drag and drop audio files here, or use File > Open"
        )
        self.transcription_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.transcription_layout.addWidget(self.transcription_placeholder)

        self.tab_widget.addTab(self.transcription_tab, "Transcription")

        # Batch processing tab
        self.batch_tab = BatchProcessorWidget()
        self.tab_widget.addTab(self.batch_tab, "Batch Processing")

        layout.addWidget(self.tab_widget)

        # Setup dock widgets
        self.setup_search_panel()

    def setup_menus(self):
        """Setup application menus."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu(self.language_manager.t("file"))

        open_action = QAction(self.language_manager.t("open"), self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction(self.language_manager.t("save"), self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_transcription)
        file_menu.addAction(save_action)

        export_menu = file_menu.addMenu(self.language_manager.t("export"))

        for format_name in ["JSON", "TXT", "SRT", "VTT", "CSV"]:
            action = QAction(format_name, self)
            action.triggered.connect(lambda checked, f=format_name.lower(): self.export_transcription(f))
            export_menu.addAction(action)

        file_menu.addSeparator()

        exit_action = QAction(self.language_manager.t("exit"), self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu(self.language_manager.t("edit"))

        undo_action = QAction(self.language_manager.t("undo"), self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction(self.language_manager.t("redo"), self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction(self.language_manager.t("cut"), self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        edit_menu.addAction(cut_action)

        copy_action = QAction(self.language_manager.t("copy"), self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction(self.language_manager.t("paste"), self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        edit_menu.addAction(paste_action)

        # View menu
        view_menu = menubar.addMenu(self.language_manager.t("view"))

        toggle_search_action = QAction("Toggle Search Panel", self)
        toggle_search_action.setShortcut("Ctrl+F")
        toggle_search_action.triggered.connect(self.toggle_search_panel)
        view_menu.addAction(toggle_search_action)

        # Analysis menu
        analysis_menu = menubar.addMenu(self.language_manager.t("analysis"))

        word_freq_action = QAction(self.language_manager.t("word_frequency"), self)
        word_freq_action.triggered.connect(self.show_word_frequency)
        analysis_menu.addAction(word_freq_action)

        speaker_stats_action = QAction(self.language_manager.t("speaker_statistics"), self)
        speaker_stats_action.triggered.connect(self.show_speaker_stats)
        analysis_menu.addAction(speaker_stats_action)

        analysis_menu.addSeparator()

        export_report_action = QAction(self.language_manager.t("export_report"), self)
        export_report_action.triggered.connect(self.export_analysis_report)
        analysis_menu.addAction(export_report_action)

        # Language menu
        language_menu = menubar.addMenu(self.language_manager.t("language"))

        language_group = QActionGroup(self)
        for code, name in self.language_manager.available_languages.items():
            action = QAction(name, self)
            action.setCheckable(True)
            action.setData(code)
            if code == self.language_manager.current_language:
                action.setChecked(True)
            action.triggered.connect(self.change_language)
            language_group.addAction(action)
            language_menu.addAction(action)

        # Plugins menu
        plugins_menu = menubar.addMenu(self.language_manager.t("plugins"))

        manage_plugins_action = QAction(self.language_manager.t("manage_plugins"), self)
        manage_plugins_action.triggered.connect(self.manage_plugins)
        plugins_menu.addAction(manage_plugins_action)

        plugins_menu.addSeparator()

        self.plugin_actions_menu = plugins_menu

        # Help menu
        help_menu = menubar.addMenu(self.language_manager.t("help"))

        about_action = QAction(self.language_manager.t("about"), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_toolbar(self):
        """Setup main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # Open button
        open_btn = QAction("Open", self)
        open_btn.triggered.connect(self.open_file)
        toolbar.addAction(open_btn)

        toolbar.addSeparator()

        # Transcription settings
        toolbar.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("base")
        toolbar.addWidget(self.model_combo)

        toolbar.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("Auto Detect", None)
        for code, name in self.trans_system.get_supported_languages().items():
            self.language_combo.addItem(name, code)
        toolbar.addWidget(self.language_combo)

        toolbar.addSeparator()

        # Transcribe button
        self.transcribe_btn = QAction("Transcribe", self)
        self.transcribe_btn.triggered.connect(self.start_transcription)
        toolbar.addAction(self.transcribe_btn)

    def setup_statusbar(self):
        """Setup status bar."""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self.status_label = QLabel("Ready")
        self.statusbar.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusbar.addPermanentWidget(self.progress_bar)

    def setup_search_panel(self):
        """Setup search and analysis panel."""
        self.search_dock = QDockWidget("Search & Analysis", self)
        self.search_dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )

        search_widget = QWidget()
        layout = QVBoxLayout(search_widget)

        # Search input
        self.global_search_input = QLineEdit()
        self.global_search_input.setPlaceholderText("Search across all transcriptions...")
        self.global_search_input.returnPressed.connect(self.perform_search)
        layout.addWidget(self.global_search_input)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.perform_search)
        layout.addWidget(search_btn)

        # Search results list
        self.search_results_list = QListWidget()
        self.search_results_list.itemDoubleClicked.connect(self.goto_search_result)
        layout.addWidget(self.search_results_list)

        # Analysis controls
        analysis_btn = QPushButton("Analyze Current Transcription")
        analysis_btn.clicked.connect(self.analyze_current)
        layout.addWidget(analysis_btn)

        # Word cloud display
        self.word_cloud_label = QLabel()
        self.word_cloud_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.word_cloud_label.setMinimumHeight(200)
        layout.addWidget(self.word_cloud_label)

        layout.addStretch()

        self.search_dock.setWidget(search_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.search_dock)

    def setup_connections(self):
        """Setup signal connections."""
        pass

    def _load_plugins(self):
        """Load available plugins."""
        for info in self.plugin_manager.discover_plugins():
            if info.path:
                self.plugin_manager.load_plugin(info.path)

    def open_file(self):
        """Open an audio file for transcription."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg *.webm);;All Files (*)"
        )

        if filepath:
            self.current_file = filepath
            self.status_label.setText(f"Loaded: {os.path.basename(filepath)}")
            self.setWindowTitle(f"{os.path.basename(filepath)} - Local Transcription System")

    def start_transcription(self):
        """Start transcription of the current file."""
        if not self.current_file:
            QMessageBox.warning(self, "No File", "Please open an audio file first.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Transcribing...")
        self.transcribe_btn.setEnabled(False)

        # Update transcription system settings
        self.trans_system = TranscriptionSystem(
            model_size=self.model_combo.currentText()
        )

        def progress_callback(progress, message):
            self.progress_bar.setValue(int(progress))
            self.status_label.setText(message)

        try:
            # Perform transcription
            segments = self.trans_system.transcribe_file(
                self.current_file,
                language=self.language_combo.currentData(),
                diarize=True,
                progress_callback=progress_callback
            )

            # Apply plugins
            segments = self.plugin_manager.process_segments(segments)

            self.transcription_data = segments

            # Show transcription view
            self._show_transcription_view(segments)

            # Index for search
            self.transcription_index.add_transcription(segments, self.current_file)

            self.status_label.setText(f"Transcription complete: {len(segments)} segments")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Transcription failed:\n{str(e)}")
            self.status_label.setText("Transcription failed")

        finally:
            self.progress_bar.setVisible(False)
            self.transcribe_btn.setEnabled(True)

    def _show_transcription_view(self, segments: List[TranscriptionSegment]):
        """Show the transcription view."""
        # Remove placeholder
        if self.transcription_placeholder:
            self.transcription_placeholder.setParent(None)
            self.transcription_placeholder = None

        # Create transcription view
        if self.transcription_view:
            self.transcription_view.setParent(None)

        self.transcription_view = TranscriptionView(segments, self.current_file)
        self.transcription_layout.addWidget(self.transcription_view)

    def save_transcription(self):
        """Save the current transcription."""
        if not self.transcription_data:
            QMessageBox.warning(self, "No Transcription", "No transcription to save.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Transcription",
            os.path.splitext(self.current_file)[0] + ".json" if self.current_file else "transcription.json",
            "JSON Files (*.json)"
        )

        if filepath:
            self.trans_system.export_transcription(
                self.transcription_data,
                "json",
                filepath
            )
            self.status_label.setText(f"Saved: {os.path.basename(filepath)}")

    def export_transcription(self, format: str):
        """Export transcription to specified format."""
        if not self.transcription_data:
            QMessageBox.warning(self, "No Transcription", "No transcription to export.")
            return

        ext_map = {"json": ".json", "txt": ".txt", "srt": ".srt", "vtt": ".vtt", "csv": ".csv"}
        ext = ext_map.get(format, ".txt")

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            f"Export as {format.upper()}",
            os.path.splitext(self.current_file)[0] + ext if self.current_file else f"transcription{ext}",
            f"{format.upper()} Files (*{ext})"
        )

        if filepath:
            self.trans_system.export_transcription(
                self.transcription_data,
                format,
                filepath
            )
            self.status_label.setText(f"Exported: {os.path.basename(filepath)}")

    def perform_search(self):
        """Perform search across transcriptions."""
        query = self.global_search_input.text().strip()
        if not query:
            return

        self.search_results_list.clear()

        # Search in index
        results = self.transcription_index.search(query)

        for result in results:
            self.search_results_list.addItem(
                f"[{result.speaker}] {result.text[:60]}..."
            )

    def goto_search_result(self, item):
        """Navigate to a search result."""
        # This would navigate to the specific segment in the transcription view
        pass

    def toggle_search_panel(self):
        """Toggle search panel visibility."""
        self.search_dock.setVisible(not self.search_dock.isVisible())

    def analyze_current(self):
        """Analyze current transcription."""
        if not self.transcription_data:
            QMessageBox.warning(self, "No Transcription", "No transcription to analyze.")
            return

        analysis = self.search_analyzer.analyze_transcription(self.transcription_data)
        self.show_analysis_results(analysis)

    def show_word_frequency(self):
        """Show word frequency visualization."""
        if not self.transcription_data:
            QMessageBox.warning(self, "No Transcription", "No transcription to analyze.")
            return

        analysis = self.search_analyzer.analyze_transcription(self.transcription_data)
        self.generate_word_cloud(analysis['wordcloud_data'])

    def show_speaker_stats(self):
        """Show speaker statistics."""
        if not self.transcription_data:
            QMessageBox.warning(self, "No Transcription", "No transcription to analyze.")
            return

        stats = self.search_analyzer.get_speaker_statistics(self.transcription_data)

        msg = "Speaker Statistics:\n\n"
        for speaker, data in stats.items():
            msg += f"{speaker}:\n"
            msg += f"  Speaking time: {data['total_duration']:.1f}s\n"
            msg += f"  Words: {data['total_words']}\n"
            msg += f"  Words/min: {data['words_per_minute']:.1f}\n\n"

        QMessageBox.information(self, "Speaker Statistics", msg)

    def show_analysis_results(self, analysis: Dict[str, Any]):
        """Display analysis results."""
        msg = f"Analysis Results:\n\n"
        msg += f"Total segments: {analysis['total_segments']}\n"
        msg += f"Total words: {analysis['total_words']}\n"
        msg += f"Unique words: {analysis['unique_words']}\n"
        msg += f"Duration: {analysis['total_duration']:.1f}s\n"
        msg += f"Words per minute: {analysis['words_per_minute']:.1f}\n\n"
        msg += "Top 10 words:\n"
        for word, count in analysis['word_frequency'][:10]:
            msg += f"  {word}: {count}\n"

        QMessageBox.information(self, "Analysis Results", msg)

    def export_analysis_report(self):
        """Export analysis report."""
        if not self.transcription_data:
            QMessageBox.warning(self, "No Transcription", "No transcription to analyze.")
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Analysis Report",
            "analysis_report.json",
            "JSON Files (*.json)"
        )

        if filepath:
            import json
            analysis = self.search_analyzer.analyze_transcription(self.transcription_data)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)
            self.status_label.setText(f"Report exported: {os.path.basename(filepath)}")

    def generate_word_cloud(self, word_freq: Dict[str, int]):
        """Generate and display word cloud."""
        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
            from io import BytesIO

            wordcloud = WordCloud(
                width=400,
                height=200,
                background_color='white'
            ).generate_from_frequencies(word_freq)

            # Create matplotlib figure
            fig, ax = plt.subplots(figsize=(8, 4))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.axis('off')

            # Embed in Qt
            canvas = FigureCanvasQTAgg(fig)
            self.word_cloud_label.setParent(None)
            layout = self.search_dock.widget().layout()
            layout.addWidget(canvas)
            self.word_cloud_label = canvas

            plt.close(fig)

        except ImportError:
            QMessageBox.warning(
                self,
                "Feature Unavailable",
                "Word cloud generation requires matplotlib and wordcloud packages."
            )

    def change_language(self):
        """Change application language."""
        action = self.sender()
        if action:
            code = action.data()
            if self.language_manager.change_language(code):
                QMessageBox.information(
                    self,
                    "Language Changed",
                    "Please restart the application for the language change to take full effect."
                )

    def manage_plugins(self):
        """Open plugin manager dialog."""
        dialog = PluginManagerDialog(self.plugin_manager, self)
        dialog.exec()

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Local Transcription System",
            "Local Transcription System v1.0\n\n"
            "A powerful desktop application for audio transcription.\n\n"
            "Features:\n"
            "- OpenAI Whisper integration\n"
            "- Speaker diarization\n"
            "- Multi-format export\n"
            "- Batch processing\n"
            "- Plugin support\n"
            "- Full-text search\n\n"
            "Built with PyQt6 and Python."
        )

    def closeEvent(self, event):
        """Handle window close event."""
        # Check for unsaved changes
        if self.transcription_view:
            # Could add unsaved changes check here
            pass
        event.accept()
