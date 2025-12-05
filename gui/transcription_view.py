# gui/transcription_view.py
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import os
from dataclasses import dataclass
from typing import List, Optional
from gui.audio_player import AudioPlayer

@dataclass
class EditableSegment:
    """Enhanced segment with editing capabilities"""
    segment_id: str
    start: float
    end: float
    original_text: str
    edited_text: str
    speaker: str
    confidence: float
    is_edited: bool = False
    comments: List[str] = None
    
    def __post_init__(self):
        if self.comments is None:
            self.comments = []
        if not self.edited_text:
            self.edited_text = self.original_text

class TranscriptionView(QWidget):
    """Enhanced transcription viewer with editing and audio sync"""
    
    def __init__(self, segments, audio_path=None):
        super().__init__()
        self.segments = [
            EditableSegment(
                segment_id=f"seg_{i}",
                start=seg.start,
                end=seg.end,
                original_text=seg.text,
                edited_text=seg.text,
                speaker=seg.speaker,
                confidence=seg.confidence
            )
            for i, seg in enumerate(segments)
        ]
        self.audio_path = audio_path
        self.audio_player = AudioPlayer(audio_path) if audio_path else None
        self.current_segment_index = -1
        self.search_results = []
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Setup the transcription editor interface"""
        main_layout = QVBoxLayout(self)
        
        # Top toolbar
        toolbar = QToolBar()
        
        # Navigation buttons
        self.prev_btn = QAction("◀ Previous", self)
        self.next_btn = QAction("Next ▶", self)
        
        # Audio control buttons
        self.play_btn = QAction("▶ Play Segment", self)
        self.stop_btn = QAction("⏹ Stop", self)
        
        # Editing buttons
        self.accept_all_btn = QAction("✓ Accept All", self)
        self.undo_btn = QAction("↶ Undo", self)
        
        for btn in [self.prev_btn, self.play_btn, self.stop_btn, 
                   self.next_btn, self.accept_all_btn, self.undo_btn]:
            toolbar.addAction(btn)
        
        main_layout.addWidget(toolbar)
        
        # Splitter for main content
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - Segment list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in transcription...")
        self.search_btn = QPushButton("Search")
        self.clear_search_btn = QPushButton("Clear")
        
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        search_layout.addWidget(self.clear_search_btn)
        left_layout.addLayout(search_layout)
        
        # Segment list
        self.segment_list = QListWidget()
        self.segment_list.setAlternatingRowColors(True)
        left_layout.addWidget(self.segment_list)
        
        # Right panel - Editor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Segment info
        info_group = QGroupBox("Segment Information")
        info_layout = QFormLayout()
        
        self.speaker_label = QLabel()
        self.time_label = QLabel()
        self.confidence_label = QLabel()
        
        info_layout.addRow("Speaker:", self.speaker_label)
        info_layout.addRow("Time:", self.time_label)
        info_layout.addRow("Confidence:", self.confidence_label)
        
        info_group.setLayout(info_layout)
        right_layout.addWidget(info_group)
        
        # Text editor
        editor_group = QGroupBox("Transcription Text")
        editor_layout = QVBoxLayout()
        
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setMinimumHeight(150)
        
        # Formatting toolbar for editor
        format_toolbar = QToolBar()
        self.bold_btn = QAction("B", self)
        self.italic_btn = QAction("I", self)
        self.underline_btn = QAction("U", self)
        
        for btn in [self.bold_btn, self.italic_btn, self.underline_btn]:
            format_toolbar.addAction(btn)
        
        editor_layout.addWidget(format_toolbar)
        editor_layout.addWidget(self.text_edit)
        
        # Speaker assignment
        speaker_layout = QHBoxLayout()
        speaker_layout.addWidget(QLabel("Speaker:"))
        self.speaker_combo = QComboBox()
        speaker_layout.addWidget(self.speaker_combo)
        editor_layout.addLayout(speaker_layout)
        
        editor_group.setLayout(editor_layout)
        right_layout.addWidget(editor_group)
        
        # Comments section
        comment_group = QGroupBox("Comments & Notes")
        comment_layout = QVBoxLayout()
        
        self.comment_list = QListWidget()
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("Add comment...")
        self.add_comment_btn = QPushButton("Add Comment")
        
        comment_layout.addWidget(self.comment_list)
        comment_layout.addWidget(self.comment_input)
        comment_layout.addWidget(self.add_comment_btn)
        
        comment_group.setLayout(comment_layout)
        right_layout.addWidget(comment_group)
        
        # Save/Cancel buttons
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.cancel_btn = QPushButton("Cancel")
        
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        right_layout.addLayout(button_layout)
        
        right_layout.addStretch()
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
        # Populate initial data
        self.refresh_segment_list()
        if self.segments:
            self.select_segment(0)
    
    def setup_connections(self):
        """Setup signal connections"""
        # Navigation
        self.prev_btn.triggered.connect(self.previous_segment)
        self.next_btn.triggered.connect(self.next_segment)
        
        # Audio controls
        if self.audio_player:
            self.play_btn.triggered.connect(self.play_current_segment)
            self.stop_btn.triggered.connect(self.audio_player.stop)
        
        # Editing
        self.save_btn.clicked.connect(self.save_current_segment)
        self.cancel_btn.clicked.connect(self.cancel_edit)
        self.accept_all_btn.triggered.connect(self.accept_all_changes)
        self.undo_btn.triggered.connect(self.undo_last_change)
        
        # Text editor formatting
        self.bold_btn.triggered.connect(lambda: self.text_edit.setFontWeight(
            QFont.Weight.Bold if self.text_edit.fontWeight() == QFont.Weight.Normal 
            else QFont.Weight.Normal
        ))
        
        # Speaker assignment
        self.speaker_combo.currentTextChanged.connect(self.update_speaker)
        
        # Comments
        self.add_comment_btn.clicked.connect(self.add_comment)
        self.comment_input.returnPressed.connect(self.add_comment)
        
        # Search
        self.search_btn.clicked.connect(self.search_transcription)
        self.clear_search_btn.clicked.connect(self.clear_search)
        self.search_input.returnPressed.connect(self.search_transcription)
        
        # Segment list selection
        self.segment_list.currentRowChanged.connect(self.select_segment)
    
    def refresh_segment_list(self):
        """Refresh the segment list display"""
        self.segment_list.clear()
        
        # Get unique speakers for combo box
        speakers = set(seg.speaker for seg in self.segments)
        self.speaker_combo.clear()
        self.speaker_combo.addItems(sorted(speakers))
        
        for i, seg in enumerate(self.segments):
            # Create list item
            text = seg.edited_text[:50] + "..." if len(seg.edited_text) > 50 else seg.edited_text
            item_text = f"[{seg.speaker}] {text}"
            
            item = QListWidgetItem(item_text)
            
            # Color coding
            if seg.is_edited:
                item.setForeground(QColor("#4CAF50"))  # Green for edited
            elif seg.confidence < 0.7:
                item.setForeground(QColor("#FF9800"))  # Orange for low confidence
            
            # Add time info
            item.setData(Qt.ItemDataRole.UserRole, i)
            item.setToolTip(f"Time: {seg.start:.1f}s - {seg.end:.1f}s\n"
                          f"Confidence: {seg.confidence:.2f}")
            
            self.segment_list.addItem(item)
    
    def select_segment(self, index):
        """Select and display a segment"""
        if 0 <= index < len(self.segments):
            self.current_segment_index = index
            seg = self.segments[index]
            
            # Update info labels
            self.speaker_label.setText(seg.speaker)
            self.time_label.setText(f"{seg.start:.1f}s - {seg.end:.1f}s")
            self.confidence_label.setText(f"{seg.confidence:.2f}")
            
            # Update text editor
            self.text_edit.setPlainText(seg.edited_text)
            
            # Update speaker combo
            self.speaker_combo.setCurrentText(seg.speaker)
            
            # Update comments list
            self.comment_list.clear()
            for comment in seg.comments:
                self.comment_list.addItem(comment)
            
            # Highlight in list
            self.segment_list.setCurrentRow(index)
    
    def play_current_segment(self):
        """Play audio for current segment"""
        if self.audio_player and self.current_segment_index >= 0:
            seg = self.segments[self.current_segment_index]
            self.audio_player.play_segment(seg.start, seg.end)
    
    def save_current_segment(self):
        """Save changes to current segment"""
        if self.current_segment_index >= 0:
            seg = self.segments[self.current_segment_index]
            
            # Check if changes were made
            new_text = self.text_edit.toPlainText()
            if new_text != seg.original_text:
                seg.edited_text = new_text
                seg.is_edited = True
            
            self.refresh_segment_list()
    
    def update_speaker(self, speaker):
        """Update speaker for current segment"""
        if self.current_segment_index >= 0:
            seg = self.segments[self.current_segment_index]
            seg.speaker = speaker
            seg.is_edited = True
            self.speaker_label.setText(speaker)
    
    def add_comment(self):
        """Add comment to current segment"""
        comment = self.comment_input.text().strip()
        if comment and self.current_segment_index >= 0:
            seg = self.segments[self.current_segment_index]
            seg.comments.append(f"{datetime.now().strftime('%H:%M')}: {comment}")
            self.comment_list.addItem(seg.comments[-1])
            self.comment_input.clear()
    
    def search_transcription(self):
        """Search through transcription"""
        query = self.search_input.text().strip()
        if not query:
            return
        
        self.search_results = []
        
        # Simple search (can be enhanced with Whoosh for larger transcriptions)
        for i, seg in enumerate(self.segments):
            if query.lower() in seg.edited_text.lower():
                self.search_results.append(i)
        
        # Highlight results
        for i in range(self.segment_list.count()):
            item = self.segment_list.item(i)
            if i in self.search_results:
                item.setBackground(QColor("#FFF9C4"))  # Light yellow
            else:
                item.setBackground(QColor(Qt.GlobalColor.white))
        
        if self.search_results:
            self.select_segment(self.search_results[0])
    
    def clear_search(self):
        """Clear search highlights"""
        self.search_input.clear()
        for i in range(self.segment_list.count()):
            item = self.segment_list.item(i)
            item.setBackground(QColor(Qt.GlobalColor.white))
        self.search_results = []
    
    def accept_all_changes(self):
        """Accept all edited segments as final"""
        for seg in self.segments:
            if seg.is_edited:
                seg.original_text = seg.edited_text
                seg.is_edited = False
        self.refresh_segment_list()
    
    def undo_last_change(self):
        """Undo last edit for current segment"""
        if self.current_segment_index >= 0:
            seg = self.segments[self.current_segment_index]
            seg.edited_text = seg.original_text
            seg.is_edited = False
            self.text_edit.setPlainText(seg.edited_text)
            self.refresh_segment_list()