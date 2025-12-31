# plugins/base_plugin.py
"""
Plugin system for extending transcription functionality.
Provides base classes and plugin management.
"""

import os
import importlib
import importlib.util
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QTextEdit, QCheckBox, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt


@dataclass
class PluginInfo:
    """Information about a plugin."""
    name: str
    version: str
    author: str
    description: str
    enabled: bool = True
    path: Optional[str] = None
    instance: Optional['BasePlugin'] = None


class BasePlugin(ABC):
    """
    Abstract base class for all plugins.

    Plugins can extend transcription functionality by:
    - Processing transcription segments
    - Adding custom vocabulary
    - Providing custom export formats
    - Adding UI components
    """

    # Plugin metadata (override in subclasses)
    NAME = "Base Plugin"
    VERSION = "1.0.0"
    AUTHOR = "Unknown"
    DESCRIPTION = "Base plugin class"

    def __init__(self):
        """Initialize the plugin."""
        self._enabled = True
        self._hooks: Dict[str, List[Callable]] = {}

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """Set plugin enabled state."""
        self._enabled = value

    def get_info(self) -> PluginInfo:
        """Get plugin information."""
        return PluginInfo(
            name=self.NAME,
            version=self.VERSION,
            author=self.AUTHOR,
            description=self.DESCRIPTION,
            enabled=self._enabled,
            instance=self
        )

    @abstractmethod
    def activate(self) -> bool:
        """
        Activate the plugin.

        Returns:
            True if activation was successful
        """
        pass

    @abstractmethod
    def deactivate(self) -> bool:
        """
        Deactivate the plugin.

        Returns:
            True if deactivation was successful
        """
        pass

    def process_segments(self, segments: List[Any]) -> List[Any]:
        """
        Process transcription segments.

        Override this method to modify segments.

        Args:
            segments: List of transcription segments

        Returns:
            Modified segments
        """
        return segments

    def on_transcription_complete(self, segments: List[Any], metadata: Dict[str, Any]):
        """
        Called when transcription is complete.

        Override to perform post-processing.

        Args:
            segments: Transcription segments
            metadata: Transcription metadata
        """
        pass

    def get_menu_actions(self) -> List[Dict[str, Any]]:
        """
        Get menu actions to add to the UI.

        Returns:
            List of action dictionaries with 'name', 'callback', and optional 'shortcut'
        """
        return []

    def get_settings_widget(self) -> Optional[Any]:
        """
        Get a settings widget for plugin configuration.

        Returns:
            QWidget or None
        """
        return None

    def register_hook(self, event: str, callback: Callable):
        """
        Register a callback for an event.

        Args:
            event: Event name
            callback: Callback function
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def trigger_hook(self, event: str, *args, **kwargs):
        """
        Trigger callbacks for an event.

        Args:
            event: Event name
            *args: Positional arguments
            **kwargs: Keyword arguments
        """
        for callback in self._hooks.get(event, []):
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"Plugin hook error ({self.NAME}): {e}")


class PluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.
    """

    DEFAULT_PLUGIN_DIRS = [
        os.path.join(os.path.dirname(__file__)),  # Built-in plugins
        os.path.join(os.path.expanduser("~"), ".transcription_plugins"),  # User plugins
    ]

    def __init__(self, plugin_dirs: List[str] = None):
        """
        Initialize the plugin manager.

        Args:
            plugin_dirs: List of directories to search for plugins
        """
        self.plugin_dirs = plugin_dirs or self.DEFAULT_PLUGIN_DIRS
        self.plugins: Dict[str, BasePlugin] = {}
        self._load_callbacks: List[Callable] = []

    def discover_plugins(self) -> List[PluginInfo]:
        """
        Discover available plugins.

        Returns:
            List of PluginInfo objects
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir):
                continue

            for filename in os.listdir(plugin_dir):
                if filename.endswith('.py') and not filename.startswith('_'):
                    if filename == 'base_plugin.py':
                        continue

                    filepath = os.path.join(plugin_dir, filename)
                    try:
                        info = self._get_plugin_info(filepath)
                        if info:
                            discovered.append(info)
                    except Exception as e:
                        print(f"Error discovering plugin {filename}: {e}")

        return discovered

    def _get_plugin_info(self, filepath: str) -> Optional[PluginInfo]:
        """
        Get plugin info without fully loading it.

        Args:
            filepath: Path to plugin file

        Returns:
            PluginInfo or None
        """
        module_name = Path(filepath).stem

        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"Error loading plugin module {module_name}: {e}")
            return None

        # Find plugin class
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, BasePlugin) and
                attr is not BasePlugin):

                return PluginInfo(
                    name=getattr(attr, 'NAME', attr_name),
                    version=getattr(attr, 'VERSION', '1.0.0'),
                    author=getattr(attr, 'AUTHOR', 'Unknown'),
                    description=getattr(attr, 'DESCRIPTION', ''),
                    enabled=False,
                    path=filepath
                )

        return None

    def load_plugin(self, filepath: str) -> Optional[BasePlugin]:
        """
        Load a plugin from file.

        Args:
            filepath: Path to plugin file

        Returns:
            Plugin instance or None
        """
        module_name = Path(filepath).stem

        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"Error loading plugin {module_name}: {e}")
            return None

        # Find and instantiate plugin class
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, BasePlugin) and
                attr is not BasePlugin):

                try:
                    plugin = attr()
                    self.plugins[plugin.NAME] = plugin

                    # Notify callbacks
                    for callback in self._load_callbacks:
                        callback(plugin)

                    return plugin
                except Exception as e:
                    print(f"Error instantiating plugin {attr_name}: {e}")

        return None

    def enable_plugin(self, name: str) -> bool:
        """
        Enable a plugin.

        Args:
            name: Plugin name

        Returns:
            True if successful
        """
        if name not in self.plugins:
            return False

        plugin = self.plugins[name]
        if plugin.activate():
            plugin.enabled = True
            return True

        return False

    def disable_plugin(self, name: str) -> bool:
        """
        Disable a plugin.

        Args:
            name: Plugin name

        Returns:
            True if successful
        """
        if name not in self.plugins:
            return False

        plugin = self.plugins[name]
        if plugin.deactivate():
            plugin.enabled = False
            return True

        return False

    def get_enabled_plugins(self) -> List[BasePlugin]:
        """Get list of enabled plugins."""
        return [p for p in self.plugins.values() if p.enabled]

    def process_segments(self, segments: List[Any]) -> List[Any]:
        """
        Process segments through all enabled plugins.

        Args:
            segments: Original segments

        Returns:
            Processed segments
        """
        for plugin in self.get_enabled_plugins():
            try:
                segments = plugin.process_segments(segments)
            except Exception as e:
                print(f"Plugin error ({plugin.NAME}): {e}")

        return segments

    def notify_transcription_complete(self, segments: List[Any], metadata: Dict[str, Any]):
        """
        Notify plugins that transcription is complete.

        Args:
            segments: Transcription segments
            metadata: Transcription metadata
        """
        for plugin in self.get_enabled_plugins():
            try:
                plugin.on_transcription_complete(segments, metadata)
            except Exception as e:
                print(f"Plugin error ({plugin.NAME}): {e}")

    def on_plugin_load(self, callback: Callable[[BasePlugin], None]):
        """Register a callback for plugin loading."""
        self._load_callbacks.append(callback)

    def get_all_menu_actions(self) -> List[Dict[str, Any]]:
        """Get menu actions from all enabled plugins."""
        actions = []
        for plugin in self.get_enabled_plugins():
            try:
                actions.extend(plugin.get_menu_actions())
            except Exception as e:
                print(f"Plugin error ({plugin.NAME}): {e}")
        return actions


class PluginManagerDialog(QDialog):
    """Dialog for managing plugins."""

    def __init__(self, plugin_manager: PluginManager, parent=None):
        super().__init__(parent)
        self.plugin_manager = plugin_manager
        self.setWindowTitle("Plugin Manager")
        self.setMinimumSize(600, 400)
        self.setup_ui()
        self.refresh_plugins()

    def setup_ui(self):
        """Setup the dialog UI."""
        layout = QHBoxLayout(self)

        # Left panel - plugin list
        left_panel = QVBoxLayout()

        self.plugin_list = QListWidget()
        self.plugin_list.currentItemChanged.connect(self.on_plugin_selected)
        left_panel.addWidget(QLabel("Available Plugins:"))
        left_panel.addWidget(self.plugin_list)

        # Buttons
        button_layout = QHBoxLayout()
        self.enable_btn = QPushButton("Enable")
        self.enable_btn.clicked.connect(self.toggle_plugin)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_plugins)

        button_layout.addWidget(self.enable_btn)
        button_layout.addWidget(self.refresh_btn)
        left_panel.addLayout(button_layout)

        layout.addLayout(left_panel)

        # Right panel - plugin details
        right_panel = QVBoxLayout()

        details_group = QGroupBox("Plugin Details")
        details_layout = QVBoxLayout()

        self.name_label = QLabel()
        self.version_label = QLabel()
        self.author_label = QLabel()
        self.description_text = QTextEdit()
        self.description_text.setReadOnly(True)
        self.description_text.setMaximumHeight(100)

        details_layout.addWidget(self.name_label)
        details_layout.addWidget(self.version_label)
        details_layout.addWidget(self.author_label)
        details_layout.addWidget(QLabel("Description:"))
        details_layout.addWidget(self.description_text)

        details_group.setLayout(details_layout)
        right_panel.addWidget(details_group)

        # Settings placeholder
        self.settings_group = QGroupBox("Plugin Settings")
        self.settings_layout = QVBoxLayout()
        self.settings_group.setLayout(self.settings_layout)
        right_panel.addWidget(self.settings_group)

        right_panel.addStretch()

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        right_panel.addWidget(close_btn)

        layout.addLayout(right_panel)

    def refresh_plugins(self):
        """Refresh the plugin list."""
        self.plugin_list.clear()

        # Add loaded plugins
        for name, plugin in self.plugin_manager.plugins.items():
            item = QListWidgetItem(name)
            item.setData(Qt.ItemDataRole.UserRole, plugin.get_info())
            if plugin.enabled:
                item.setText(f"[Enabled] {name}")
            self.plugin_list.addItem(item)

        # Discover additional plugins
        for info in self.plugin_manager.discover_plugins():
            if info.name not in self.plugin_manager.plugins:
                item = QListWidgetItem(f"[Not Loaded] {info.name}")
                item.setData(Qt.ItemDataRole.UserRole, info)
                self.plugin_list.addItem(item)

    def on_plugin_selected(self, current, previous):
        """Handle plugin selection."""
        if current is None:
            return

        info = current.data(Qt.ItemDataRole.UserRole)
        if info is None:
            return

        self.name_label.setText(f"<b>{info.name}</b>")
        self.version_label.setText(f"Version: {info.version}")
        self.author_label.setText(f"Author: {info.author}")
        self.description_text.setText(info.description)

        if info.enabled:
            self.enable_btn.setText("Disable")
        else:
            self.enable_btn.setText("Enable")

        # Clear and update settings
        while self.settings_layout.count():
            item = self.settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if info.instance:
            settings_widget = info.instance.get_settings_widget()
            if settings_widget:
                self.settings_layout.addWidget(settings_widget)
            else:
                self.settings_layout.addWidget(QLabel("No settings available"))
        else:
            self.settings_layout.addWidget(QLabel("Plugin not loaded"))

    def toggle_plugin(self):
        """Toggle the selected plugin."""
        current = self.plugin_list.currentItem()
        if current is None:
            return

        info = current.data(Qt.ItemDataRole.UserRole)
        if info is None:
            return

        # Load plugin if not loaded
        if info.name not in self.plugin_manager.plugins:
            if info.path:
                plugin = self.plugin_manager.load_plugin(info.path)
                if plugin is None:
                    QMessageBox.warning(self, "Error", f"Failed to load plugin: {info.name}")
                    return
            else:
                QMessageBox.warning(self, "Error", "Plugin path not available")
                return

        # Toggle state
        if info.enabled:
            if self.plugin_manager.disable_plugin(info.name):
                self.enable_btn.setText("Enable")
            else:
                QMessageBox.warning(self, "Error", "Failed to disable plugin")
        else:
            if self.plugin_manager.enable_plugin(info.name):
                self.enable_btn.setText("Disable")
            else:
                QMessageBox.warning(self, "Error", "Failed to enable plugin")

        self.refresh_plugins()
