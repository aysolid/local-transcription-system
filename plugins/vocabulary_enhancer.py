# plugins/vocabulary_enhancer.py
"""
Vocabulary enhancer plugin for improving transcription accuracy
with domain-specific terms and custom dictionaries.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Set
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QLineEdit,
    QPushButton, QLabel, QFileDialog, QTextEdit, QGroupBox, QComboBox
)

from .base_plugin import BasePlugin


class VocabularyEnhancerPlugin(BasePlugin):
    """
    Plugin to enhance transcription with custom vocabulary.

    Features:
    - Custom word dictionaries
    - Domain-specific term replacement
    - Automatic capitalization correction
    - Acronym expansion
    """

    NAME = "Vocabulary Enhancer"
    VERSION = "1.0.0"
    AUTHOR = "Local Transcription Team"
    DESCRIPTION = (
        "Enhances transcription accuracy with custom vocabulary, "
        "domain-specific terms, and automatic corrections."
    )

    # Default dictionaries path
    DEFAULT_DICT_DIR = os.path.join(os.path.expanduser("~"), ".transcription_vocab")

    def __init__(self):
        super().__init__()

        # Vocabulary storage
        self.custom_words: Set[str] = set()
        self.replacements: Dict[str, str] = {}
        self.acronyms: Dict[str, str] = {}
        self.proper_nouns: Set[str] = set()

        # Settings
        self.auto_capitalize = True
        self.expand_acronyms = True
        self.apply_replacements = True

        # Ensure dictionary directory exists
        os.makedirs(self.DEFAULT_DICT_DIR, exist_ok=True)

        # Load default dictionaries
        self._load_dictionaries()

    def activate(self) -> bool:
        """Activate the plugin."""
        self._load_dictionaries()
        return True

    def deactivate(self) -> bool:
        """Deactivate the plugin."""
        self._save_dictionaries()
        return True

    def _load_dictionaries(self):
        """Load dictionaries from disk."""
        # Load custom words
        words_path = os.path.join(self.DEFAULT_DICT_DIR, "custom_words.json")
        if os.path.exists(words_path):
            try:
                with open(words_path, 'r', encoding='utf-8') as f:
                    self.custom_words = set(json.load(f))
            except Exception as e:
                print(f"Error loading custom words: {e}")

        # Load replacements
        replacements_path = os.path.join(self.DEFAULT_DICT_DIR, "replacements.json")
        if os.path.exists(replacements_path):
            try:
                with open(replacements_path, 'r', encoding='utf-8') as f:
                    self.replacements = json.load(f)
            except Exception as e:
                print(f"Error loading replacements: {e}")

        # Load acronyms
        acronyms_path = os.path.join(self.DEFAULT_DICT_DIR, "acronyms.json")
        if os.path.exists(acronyms_path):
            try:
                with open(acronyms_path, 'r', encoding='utf-8') as f:
                    self.acronyms = json.load(f)
            except Exception as e:
                print(f"Error loading acronyms: {e}")

        # Load proper nouns
        nouns_path = os.path.join(self.DEFAULT_DICT_DIR, "proper_nouns.json")
        if os.path.exists(nouns_path):
            try:
                with open(nouns_path, 'r', encoding='utf-8') as f:
                    self.proper_nouns = set(json.load(f))
            except Exception as e:
                print(f"Error loading proper nouns: {e}")

    def _save_dictionaries(self):
        """Save dictionaries to disk."""
        try:
            # Save custom words
            with open(os.path.join(self.DEFAULT_DICT_DIR, "custom_words.json"), 'w', encoding='utf-8') as f:
                json.dump(list(self.custom_words), f, indent=2)

            # Save replacements
            with open(os.path.join(self.DEFAULT_DICT_DIR, "replacements.json"), 'w', encoding='utf-8') as f:
                json.dump(self.replacements, f, indent=2)

            # Save acronyms
            with open(os.path.join(self.DEFAULT_DICT_DIR, "acronyms.json"), 'w', encoding='utf-8') as f:
                json.dump(self.acronyms, f, indent=2)

            # Save proper nouns
            with open(os.path.join(self.DEFAULT_DICT_DIR, "proper_nouns.json"), 'w', encoding='utf-8') as f:
                json.dump(list(self.proper_nouns), f, indent=2)

        except Exception as e:
            print(f"Error saving dictionaries: {e}")

    def process_segments(self, segments: List[Any]) -> List[Any]:
        """
        Process transcription segments with vocabulary enhancements.

        Args:
            segments: List of transcription segments

        Returns:
            Enhanced segments
        """
        for segment in segments:
            text = segment.text if hasattr(segment, 'text') else segment.get('text', '')
            enhanced_text = self.enhance_text(text)

            if hasattr(segment, 'text'):
                segment.text = enhanced_text
            else:
                segment['text'] = enhanced_text

        return segments

    def enhance_text(self, text: str) -> str:
        """
        Enhance text with vocabulary corrections.

        Args:
            text: Original text

        Returns:
            Enhanced text
        """
        if not text:
            return text

        result = text

        # Apply replacements
        if self.apply_replacements:
            for wrong, correct in self.replacements.items():
                # Case-insensitive replacement
                pattern = re.compile(re.escape(wrong), re.IGNORECASE)
                result = pattern.sub(correct, result)

        # Expand acronyms
        if self.expand_acronyms:
            for acronym, expansion in self.acronyms.items():
                # Match whole word only
                pattern = re.compile(r'\b' + re.escape(acronym) + r'\b', re.IGNORECASE)
                result = pattern.sub(f"{acronym} ({expansion})", result)

        # Fix proper noun capitalization
        if self.auto_capitalize:
            for noun in self.proper_nouns:
                pattern = re.compile(r'\b' + re.escape(noun) + r'\b', re.IGNORECASE)
                result = pattern.sub(noun, result)

        return result

    def add_custom_word(self, word: str):
        """Add a custom word to the dictionary."""
        self.custom_words.add(word)
        self._save_dictionaries()

    def add_replacement(self, wrong: str, correct: str):
        """Add a replacement rule."""
        self.replacements[wrong] = correct
        self._save_dictionaries()

    def add_acronym(self, acronym: str, expansion: str):
        """Add an acronym expansion."""
        self.acronyms[acronym] = expansion
        self._save_dictionaries()

    def add_proper_noun(self, noun: str):
        """Add a proper noun for capitalization."""
        self.proper_nouns.add(noun)
        self._save_dictionaries()

    def import_dictionary(self, filepath: str, dict_type: str = "words"):
        """
        Import a dictionary from file.

        Args:
            filepath: Path to dictionary file (JSON or text)
            dict_type: Type of dictionary ('words', 'replacements', 'acronyms', 'nouns')
        """
        path = Path(filepath)

        if path.suffix == '.json':
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            # Plain text - one item per line
            with open(filepath, 'r', encoding='utf-8') as f:
                data = [line.strip() for line in f if line.strip()]

        if dict_type == "words":
            if isinstance(data, list):
                self.custom_words.update(data)
            elif isinstance(data, dict):
                self.custom_words.update(data.keys())

        elif dict_type == "replacements":
            if isinstance(data, dict):
                self.replacements.update(data)

        elif dict_type == "acronyms":
            if isinstance(data, dict):
                self.acronyms.update(data)

        elif dict_type == "nouns":
            if isinstance(data, list):
                self.proper_nouns.update(data)

        self._save_dictionaries()

    def get_settings_widget(self) -> QWidget:
        """Get the settings widget for this plugin."""
        return VocabularySettingsWidget(self)

    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """Get menu actions for this plugin."""
        return [
            {
                'name': 'Import Vocabulary',
                'callback': self._show_import_dialog,
            },
            {
                'name': 'Export Vocabulary',
                'callback': self._show_export_dialog,
            },
        ]

    def _show_import_dialog(self):
        """Show import dialog."""
        filepath, _ = QFileDialog.getOpenFileName(
            None,
            "Import Vocabulary",
            "",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
        )
        if filepath:
            self.import_dictionary(filepath)

    def _show_export_dialog(self):
        """Show export dialog."""
        filepath, _ = QFileDialog.getSaveFileName(
            None,
            "Export Vocabulary",
            "vocabulary.json",
            "JSON Files (*.json)"
        )
        if filepath:
            data = {
                'custom_words': list(self.custom_words),
                'replacements': self.replacements,
                'acronyms': self.acronyms,
                'proper_nouns': list(self.proper_nouns),
            }
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)


class VocabularySettingsWidget(QWidget):
    """Settings widget for the Vocabulary Enhancer plugin."""

    def __init__(self, plugin: VocabularyEnhancerPlugin, parent=None):
        super().__init__(parent)
        self.plugin = plugin
        self.setup_ui()

    def setup_ui(self):
        """Setup the settings UI."""
        layout = QVBoxLayout(self)

        # Dictionary type selector
        type_layout = QHBoxLayout()
        type_layout.addWidget(QLabel("Dictionary:"))
        self.dict_type_combo = QComboBox()
        self.dict_type_combo.addItems(["Custom Words", "Replacements", "Acronyms", "Proper Nouns"])
        self.dict_type_combo.currentIndexChanged.connect(self.refresh_list)
        type_layout.addWidget(self.dict_type_combo)
        layout.addLayout(type_layout)

        # List display
        self.item_list = QListWidget()
        layout.addWidget(self.item_list)

        # Add/Edit section
        add_group = QGroupBox("Add Entry")
        add_layout = QVBoxLayout()

        self.entry_input = QLineEdit()
        self.entry_input.setPlaceholderText("Enter word or term...")
        add_layout.addWidget(self.entry_input)

        self.value_input = QLineEdit()
        self.value_input.setPlaceholderText("Enter replacement/expansion (if applicable)...")
        add_layout.addWidget(self.value_input)

        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_entry)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.remove_entry)

        button_layout.addWidget(add_btn)
        button_layout.addWidget(remove_btn)
        add_layout.addLayout(button_layout)

        add_group.setLayout(add_layout)
        layout.addWidget(add_group)

        # Import/Export buttons
        io_layout = QHBoxLayout()
        import_btn = QPushButton("Import")
        import_btn.clicked.connect(self.import_dict)
        export_btn = QPushButton("Export")
        export_btn.clicked.connect(self.export_dict)
        io_layout.addWidget(import_btn)
        io_layout.addWidget(export_btn)
        layout.addLayout(io_layout)

        # Initial refresh
        self.refresh_list()

    def refresh_list(self):
        """Refresh the list display."""
        self.item_list.clear()
        dict_type = self.dict_type_combo.currentText()

        if dict_type == "Custom Words":
            for word in sorted(self.plugin.custom_words):
                self.item_list.addItem(word)
            self.value_input.setVisible(False)

        elif dict_type == "Replacements":
            for wrong, correct in sorted(self.plugin.replacements.items()):
                self.item_list.addItem(f"{wrong} ’ {correct}")
            self.value_input.setVisible(True)
            self.value_input.setPlaceholderText("Correct spelling...")

        elif dict_type == "Acronyms":
            for acronym, expansion in sorted(self.plugin.acronyms.items()):
                self.item_list.addItem(f"{acronym} = {expansion}")
            self.value_input.setVisible(True)
            self.value_input.setPlaceholderText("Full expansion...")

        elif dict_type == "Proper Nouns":
            for noun in sorted(self.plugin.proper_nouns):
                self.item_list.addItem(noun)
            self.value_input.setVisible(False)

    def add_entry(self):
        """Add an entry to the current dictionary."""
        entry = self.entry_input.text().strip()
        value = self.value_input.text().strip()
        dict_type = self.dict_type_combo.currentText()

        if not entry:
            return

        if dict_type == "Custom Words":
            self.plugin.add_custom_word(entry)

        elif dict_type == "Replacements":
            if value:
                self.plugin.add_replacement(entry, value)

        elif dict_type == "Acronyms":
            if value:
                self.plugin.add_acronym(entry, value)

        elif dict_type == "Proper Nouns":
            self.plugin.add_proper_noun(entry)

        self.entry_input.clear()
        self.value_input.clear()
        self.refresh_list()

    def remove_entry(self):
        """Remove the selected entry."""
        current = self.item_list.currentItem()
        if not current:
            return

        text = current.text()
        dict_type = self.dict_type_combo.currentText()

        if dict_type == "Custom Words":
            self.plugin.custom_words.discard(text)

        elif dict_type == "Replacements":
            key = text.split(" ’ ")[0]
            self.plugin.replacements.pop(key, None)

        elif dict_type == "Acronyms":
            key = text.split(" = ")[0]
            self.plugin.acronyms.pop(key, None)

        elif dict_type == "Proper Nouns":
            self.plugin.proper_nouns.discard(text)

        self.plugin._save_dictionaries()
        self.refresh_list()

    def import_dict(self):
        """Import dictionary from file."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Import Dictionary",
            "",
            "JSON Files (*.json);;Text Files (*.txt);;All Files (*)"
        )
        if filepath:
            dict_type = self.dict_type_combo.currentText()
            type_map = {
                "Custom Words": "words",
                "Replacements": "replacements",
                "Acronyms": "acronyms",
                "Proper Nouns": "nouns",
            }
            self.plugin.import_dictionary(filepath, type_map[dict_type])
            self.refresh_list()

    def export_dict(self):
        """Export current dictionary to file."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export Dictionary",
            "dictionary.json",
            "JSON Files (*.json)"
        )
        if filepath:
            dict_type = self.dict_type_combo.currentText()

            if dict_type == "Custom Words":
                data = list(self.plugin.custom_words)
            elif dict_type == "Replacements":
                data = self.plugin.replacements
            elif dict_type == "Acronyms":
                data = self.plugin.acronyms
            elif dict_type == "Proper Nouns":
                data = list(self.plugin.proper_nouns)
            else:
                data = []

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
