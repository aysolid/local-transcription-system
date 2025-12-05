# gui/main_window.py - Additional Methods
class MainWindow(QMainWindow):
    # ... existing code ...
    
    def setup_ui(self):
        # ... existing code ...
        
        # Add new menu items
        self.setup_advanced_menus()
        
        # Add search panel
        self.setup_search_panel()
        
        # Add plugin manager
        self.plugin_manager = PluginManager()
        
    def setup_advanced_menus(self):
        """Setup advanced feature menus"""
        # Analysis menu
        analysis_menu = self.menuBar().addMenu("&Analysis")
        
        word_freq_action = QAction("Word Frequency", self)
        word_freq_action.triggered.connect(self.show_word_frequency)
        analysis_menu.addAction(word_freq_action)
        
        speaker_stats_action = QAction("Speaker Statistics", self)
        speaker_stats_action.triggered.connect(self.show_speaker_stats)
        analysis_menu.addAction(speaker_stats_action)
        
        export_report_action = QAction("Export Analysis Report", self)
        export_report_action.triggered.connect(self.export_analysis_report)
        analysis_menu.addAction(export_report_action)
        
        # Language menu
        language_menu = self.menuBar().addMenu("&Language")
        
        language_group = QActionGroup(self)
        for code, name in self.language_manager.available_languages.items():
            action = QAction(name, self)
            action.setCheckable(True)
            action.setData(code)
            if code == "en":
                action.setChecked(True)
            action.triggered.connect(self.change_language)
            language_group.addAction(action)
            language_menu.addAction(action)
        
        # Plugins menu
        plugins_menu = self.menuBar().addMenu("&Plugins")
        
        manage_plugins_action = QAction("Manage Plugins", self)
        manage_plugins_action.triggered.connect(self.manage_plugins)
        plugins_menu.addAction(manage_plugins_action)
        
        plugins_menu.addSeparator()
        
        # Plugin actions will be added dynamically
        self.plugin_actions = {}
    
    def setup_search_panel(self):
        """Setup search and analysis panel"""
        self.search_dock = QDockWidget("Search & Analysis", self)
        self.search_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | 
                                        Qt.DockWidgetArea.RightDockWidgetArea)
        
        search_widget = QWidget()
        layout = QVBoxLayout(search_widget)
        
        # Search input
        self.global_search_input = QLineEdit()
        self.global_search_input.setPlaceholderText("Search across all transcriptions...")
        layout.addWidget(self.global_search_input)
        
        # Search results list
        self.search_results_list = QListWidget()
        layout.addWidget(self.search_results_list)
        
        # Analysis controls
        analysis_btn = QPushButton("Analyze Current Transcription")
        analysis_btn.clicked.connect(self.analyze_current)
        layout.addWidget(analysis_btn)
        
        # Word cloud display
        self.word_cloud_label = QLabel()
        self.word_cloud_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.word_cloud_label)
        
        self.search_dock.setWidget(search_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.search_dock)
    
    def manage_plugins(self):
        """Open plugin manager dialog"""
        dialog = PluginManagerDialog(self.plugin_manager, self)
        dialog.exec()
    
    def analyze_current(self):
        """Analyze current transcription"""
        if not self.transcription_data:
            return
        
        analyzer = SearchAnalyzer()
        analysis = analyzer.analyze_transcription(self.transcription_data)
        
        # Display results
        self.show_analysis_results(analysis)
    
    def show_word_frequency(self):
        """Show word frequency visualization"""
        if not self.transcription_data:
            return
        
        analyzer = SearchAnalyzer()
        analysis = analyzer.analyze_transcription(self.transcription_data)
        
        # Create word cloud
        self.generate_word_cloud(analysis['wordcloud_data'])
    
    def generate_word_cloud(self, word_freq):
        """Generate and display word cloud"""
        try:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
            
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
            layout.replaceWidget(self.word_cloud_label, canvas)
            self.word_cloud_label = canvas
            
        except ImportError:
            QMessageBox.warning(self, "Feature Unavailable", 
                              "Word cloud generation requires matplotlib and wordcloud packages")