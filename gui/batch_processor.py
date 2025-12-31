# gui/batch_processor.py
"""
Batch processing UI component for handling multiple audio files.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QProgressBar, QLabel, QFileDialog, QHeaderView,
    QGroupBox, QSpinBox, QCheckBox, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from typing import List, Dict, Optional
import os

from core.batch_manager import BatchManager, BatchStatus, BatchJob
from core.transcriber import TranscriptionSystem


class BatchWorkerThread(QThread):
    """Worker thread for batch processing."""

    progress_updated = pyqtSignal(str, float, str)  # job_id, progress, message
    job_completed = pyqtSignal(str, bool, str)  # job_id, success, message
    all_completed = pyqtSignal()

    def __init__(self, batch_manager: BatchManager, trans_system: TranscriptionSystem):
        super().__init__()
        self.batch_manager = batch_manager
        self.trans_system = trans_system
        self._is_running = False

    def run(self):
        """Run batch processing."""
        self._is_running = True
        self.batch_manager.start_workers(self.trans_system)

        # Monitor progress
        while self._is_running:
            jobs = self.batch_manager.get_all_jobs()
            all_done = True

            for job in jobs:
                if job.status in (BatchStatus.PENDING, BatchStatus.PROCESSING):
                    all_done = False

                # Emit progress update
                msg = job.metadata.get('status_message', '') if job.metadata else ''
                self.progress_updated.emit(job.id, job.progress, msg)

                # Emit completion status
                if job.status == BatchStatus.COMPLETED:
                    self.job_completed.emit(job.id, True, "Completed successfully")
                elif job.status == BatchStatus.FAILED:
                    self.job_completed.emit(job.id, False, job.error or "Unknown error")

            if all_done:
                break

            self.msleep(500)  # Update every 500ms

        self.all_completed.emit()

    def stop(self):
        """Stop batch processing."""
        self._is_running = False
        self.batch_manager.is_running = False


class BatchProcessorWidget(QWidget):
    """Widget for batch processing multiple audio files."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.batch_manager = BatchManager(max_workers=2)
        self.trans_system = TranscriptionSystem()
        self.worker_thread: Optional[BatchWorkerThread] = None

        self.setup_ui()

    def setup_ui(self):
        """Setup the batch processor UI."""
        layout = QVBoxLayout(self)

        # Settings group
        settings_group = QGroupBox("Batch Settings")
        settings_layout = QHBoxLayout()

        # Model size
        settings_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems(["tiny", "base", "small", "medium", "large"])
        self.model_combo.setCurrentText("base")
        settings_layout.addWidget(self.model_combo)

        # Language
        settings_layout.addWidget(QLabel("Language:"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("Auto Detect", None)
        for code, name in self.trans_system.get_supported_languages().items():
            self.language_combo.addItem(name, code)
        settings_layout.addWidget(self.language_combo)

        # Diarization
        self.diarize_check = QCheckBox("Speaker Diarization")
        settings_layout.addWidget(self.diarize_check)

        # Workers
        settings_layout.addWidget(QLabel("Workers:"))
        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(1, 4)
        self.workers_spin.setValue(2)
        settings_layout.addWidget(self.workers_spin)

        settings_layout.addStretch()

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # File table
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(
            ["File", "Status", "Progress", "Duration", "Actions"]
        )
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.file_table.setColumnWidth(1, 120)
        self.file_table.setColumnWidth(2, 150)
        self.file_table.setColumnWidth(3, 80)
        self.file_table.setColumnWidth(4, 80)
        layout.addWidget(self.file_table)

        # Overall progress
        progress_layout = QHBoxLayout()
        self.overall_progress = QProgressBar()
        self.overall_progress.setFormat("%v / %m files (%p%)")
        progress_layout.addWidget(self.overall_progress)

        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        layout.addLayout(progress_layout)

        # Buttons
        button_layout = QHBoxLayout()

        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self.add_files)
        button_layout.addWidget(self.add_files_btn)

        self.add_folder_btn = QPushButton("Add Folder")
        self.add_folder_btn.clicked.connect(self.add_folder)
        button_layout.addWidget(self.add_folder_btn)

        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_selected)
        button_layout.addWidget(self.remove_btn)

        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.clicked.connect(self.clear_all)
        button_layout.addWidget(self.clear_btn)

        button_layout.addStretch()

        self.start_btn = QPushButton("Start Batch")
        self.start_btn.clicked.connect(self.start_batch)
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        button_layout.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel_batch)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)

        self.export_btn = QPushButton("Export Report")
        self.export_btn.clicked.connect(self.export_report)
        button_layout.addWidget(self.export_btn)

        layout.addLayout(button_layout)

        # Job tracking
        self.job_rows: Dict[str, int] = {}  # job_id -> table row
        self.file_paths: List[str] = []

    def add_files(self):
        """Add audio files to the batch."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            "",
            "Audio Files (*.wav *.mp3 *.m4a *.flac *.ogg *.webm);;All Files (*)"
        )

        for filepath in files:
            self._add_file_to_table(filepath)

    def add_folder(self):
        """Add all audio files from a folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")

        if folder:
            supported_exts = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.webm'}
            for filename in os.listdir(folder):
                ext = os.path.splitext(filename)[1].lower()
                if ext in supported_exts:
                    filepath = os.path.join(folder, filename)
                    self._add_file_to_table(filepath)

    def _add_file_to_table(self, filepath: str):
        """Add a file to the table."""
        if filepath in self.file_paths:
            return  # Skip duplicates

        self.file_paths.append(filepath)
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)

        # Filename
        filename = os.path.basename(filepath)
        self.file_table.setItem(row, 0, QTableWidgetItem(filename))

        # Status
        status_item = QTableWidgetItem("Pending")
        status_item.setForeground(QColor("#666666"))
        self.file_table.setItem(row, 1, status_item)

        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(0)
        self.file_table.setCellWidget(row, 2, progress_bar)

        # Duration (placeholder)
        self.file_table.setItem(row, 3, QTableWidgetItem("-"))

        # Remove button
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self._remove_row(row))
        self.file_table.setCellWidget(row, 4, remove_btn)

        # Update overall progress
        self.overall_progress.setMaximum(len(self.file_paths))

    def _remove_row(self, row: int):
        """Remove a row from the table."""
        if row < len(self.file_paths):
            self.file_paths.pop(row)
            self.file_table.removeRow(row)
            self.overall_progress.setMaximum(len(self.file_paths))

    def remove_selected(self):
        """Remove selected files."""
        selected_rows = set()
        for item in self.file_table.selectedItems():
            selected_rows.add(item.row())

        for row in sorted(selected_rows, reverse=True):
            self._remove_row(row)

    def clear_all(self):
        """Clear all files."""
        self.file_table.setRowCount(0)
        self.file_paths.clear()
        self.job_rows.clear()
        self.overall_progress.setMaximum(0)
        self.overall_progress.setValue(0)

    def start_batch(self):
        """Start batch processing."""
        if not self.file_paths:
            QMessageBox.warning(self, "No Files", "Please add files to process.")
            return

        # Create new batch manager with settings
        self.batch_manager = BatchManager(max_workers=self.workers_spin.value())

        # Update transcription system
        self.trans_system = TranscriptionSystem(
            model_size=self.model_combo.currentText()
        )

        # Get settings
        settings = {
            'language': self.language_combo.currentData(),
            'diarize': self.diarize_check.isChecked(),
        }

        # Add jobs
        job_ids = self.batch_manager.add_jobs(self.file_paths, settings)

        # Map job IDs to table rows
        for i, job_id in enumerate(job_ids):
            self.job_rows[job_id] = i

        # Start worker thread
        self.worker_thread = BatchWorkerThread(self.batch_manager, self.trans_system)
        self.worker_thread.progress_updated.connect(self._update_progress)
        self.worker_thread.job_completed.connect(self._job_completed)
        self.worker_thread.all_completed.connect(self._batch_completed)
        self.worker_thread.start()

        # Update UI
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.add_files_btn.setEnabled(False)
        self.add_folder_btn.setEnabled(False)
        self.status_label.setText("Processing...")

    def _update_progress(self, job_id: str, progress: float, message: str):
        """Update progress for a job."""
        if job_id not in self.job_rows:
            return

        row = self.job_rows[job_id]

        # Update progress bar
        progress_bar = self.file_table.cellWidget(row, 2)
        if progress_bar:
            progress_bar.setValue(int(progress))

        # Update status
        status_item = self.file_table.item(row, 1)
        if status_item:
            status_item.setText("Processing")
            status_item.setForeground(QColor("#2196F3"))

        # Update overall progress
        completed = sum(
            1 for job in self.batch_manager.get_all_jobs()
            if job.status in (BatchStatus.COMPLETED, BatchStatus.FAILED)
        )
        self.overall_progress.setValue(completed)

    def _job_completed(self, job_id: str, success: bool, message: str):
        """Handle job completion."""
        if job_id not in self.job_rows:
            return

        row = self.job_rows[job_id]

        # Update status
        status_item = self.file_table.item(row, 1)
        if status_item:
            if success:
                status_item.setText("Completed")
                status_item.setForeground(QColor("#4CAF50"))
            else:
                status_item.setText("Failed")
                status_item.setForeground(QColor("#F44336"))

        # Update progress bar
        progress_bar = self.file_table.cellWidget(row, 2)
        if progress_bar:
            progress_bar.setValue(100 if success else 0)

    def _batch_completed(self):
        """Handle batch completion."""
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.add_files_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)

        # Count results
        completed = 0
        failed = 0
        for job in self.batch_manager.get_all_jobs():
            if job.status == BatchStatus.COMPLETED:
                completed += 1
            elif job.status == BatchStatus.FAILED:
                failed += 1

        self.status_label.setText(f"Done: {completed} completed, {failed} failed")

        QMessageBox.information(
            self,
            "Batch Complete",
            f"Batch processing complete.\n\n"
            f"Completed: {completed}\n"
            f"Failed: {failed}"
        )

    def cancel_batch(self):
        """Cancel batch processing."""
        if self.worker_thread:
            self.worker_thread.stop()
            self.worker_thread.wait()

        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.add_files_btn.setEnabled(True)
        self.add_folder_btn.setEnabled(True)
        self.status_label.setText("Cancelled")

    def export_report(self):
        """Export batch processing report."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report",
            "batch_report.json",
            "JSON Files (*.json)"
        )

        if filepath:
            self.batch_manager.export_batch_report(filepath)
            QMessageBox.information(
                self,
                "Export Complete",
                f"Report exported to:\n{filepath}"
            )
