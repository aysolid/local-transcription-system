# utils/language_utils.py
"""
Language utilities for internationalization and language management.
"""

from typing import Dict, Optional, Callable
import os


class LanguageManager:
    """
    Manages language settings and translations for the application.
    """

    # Supported languages with their native names
    SUPPORTED_LANGUAGES = {
        "en": "English",
        "es": "Español",
        "fr": "Français",
        "de": "Deutsch",
        "it": "Italiano",
        "pt": "Português",
        "nl": "Nederlands",
        "ru": " CAA:89",
        "zh": "-‡",
        "ja": "å,ž",
        "ko": "\m´",
        "ar": "'D91(J)",
        "hi": "9?(M&@",
        "tr": "Türkçe",
        "pl": "Polski",
        "uk": "#:@0W=AL:0",
        "vi": "Ti¿ng ViÇt",
        "th": "D"",
        "id": "Bahasa Indonesia",
        "ms": "Bahasa Melayu",
    }

    # UI translations
    TRANSLATIONS = {
        "en": {
            "app_title": "Local Transcription System",
            "file": "File",
            "open": "Open",
            "save": "Save",
            "save_as": "Save As",
            "export": "Export",
            "exit": "Exit",
            "edit": "Edit",
            "undo": "Undo",
            "redo": "Redo",
            "cut": "Cut",
            "copy": "Copy",
            "paste": "Paste",
            "view": "View",
            "analysis": "Analysis",
            "word_frequency": "Word Frequency",
            "speaker_statistics": "Speaker Statistics",
            "export_report": "Export Analysis Report",
            "language": "Language",
            "plugins": "Plugins",
            "manage_plugins": "Manage Plugins",
            "help": "Help",
            "about": "About",
            "transcribe": "Transcribe",
            "start_transcription": "Start Transcription",
            "stop": "Stop",
            "pause": "Pause",
            "resume": "Resume",
            "settings": "Settings",
            "model_size": "Model Size",
            "enable_diarization": "Enable Speaker Diarization",
            "select_language": "Select Language",
            "auto_detect": "Auto Detect",
            "processing": "Processing...",
            "completed": "Completed",
            "failed": "Failed",
            "cancel": "Cancel",
            "ok": "OK",
            "apply": "Apply",
            "search": "Search",
            "search_placeholder": "Search in transcription...",
            "no_results": "No results found",
            "speaker": "Speaker",
            "confidence": "Confidence",
            "time": "Time",
            "duration": "Duration",
            "segment": "Segment",
            "segments": "Segments",
            "words": "Words",
            "characters": "Characters",
            "add_comment": "Add Comment",
            "comments": "Comments",
            "accept_changes": "Accept Changes",
            "discard_changes": "Discard Changes",
            "batch_process": "Batch Process",
            "add_files": "Add Files",
            "remove_selected": "Remove Selected",
            "clear_all": "Clear All",
            "start_batch": "Start Batch",
            "cancel_batch": "Cancel Batch",
            "export_results": "Export Results",
            "progress": "Progress",
            "status": "Status",
            "pending": "Pending",
            "in_progress": "In Progress",
            "error": "Error",
            "warning": "Warning",
            "info": "Information",
            "confirm": "Confirm",
            "unsaved_changes": "You have unsaved changes. Do you want to save before closing?",
        },
        "es": {
            "app_title": "Sistema de Transcripción Local",
            "file": "Archivo",
            "open": "Abrir",
            "save": "Guardar",
            "save_as": "Guardar como",
            "export": "Exportar",
            "exit": "Salir",
            "edit": "Editar",
            "undo": "Deshacer",
            "redo": "Rehacer",
            "cut": "Cortar",
            "copy": "Copiar",
            "paste": "Pegar",
            "view": "Ver",
            "analysis": "Análisis",
            "word_frequency": "Frecuencia de palabras",
            "speaker_statistics": "Estadísticas de hablantes",
            "export_report": "Exportar informe de análisis",
            "language": "Idioma",
            "plugins": "Complementos",
            "manage_plugins": "Gestionar complementos",
            "help": "Ayuda",
            "about": "Acerca de",
            "transcribe": "Transcribir",
            "start_transcription": "Iniciar transcripción",
            "stop": "Detener",
            "pause": "Pausar",
            "resume": "Continuar",
            "settings": "Configuración",
            "model_size": "Tamaño del modelo",
            "enable_diarization": "Habilitar diarización de hablantes",
            "select_language": "Seleccionar idioma",
            "auto_detect": "Detección automática",
            "processing": "Procesando...",
            "completed": "Completado",
            "failed": "Fallido",
            "cancel": "Cancelar",
            "ok": "Aceptar",
            "apply": "Aplicar",
            "search": "Buscar",
            "search_placeholder": "Buscar en transcripción...",
            "no_results": "No se encontraron resultados",
            "speaker": "Hablante",
            "confidence": "Confianza",
            "time": "Tiempo",
            "duration": "Duración",
            "segment": "Segmento",
            "segments": "Segmentos",
            "words": "Palabras",
            "characters": "Caracteres",
            "add_comment": "Agregar comentario",
            "comments": "Comentarios",
            "accept_changes": "Aceptar cambios",
            "discard_changes": "Descartar cambios",
            "batch_process": "Procesamiento por lotes",
            "add_files": "Agregar archivos",
            "remove_selected": "Eliminar seleccionados",
            "clear_all": "Limpiar todo",
            "start_batch": "Iniciar lote",
            "cancel_batch": "Cancelar lote",
            "export_results": "Exportar resultados",
            "progress": "Progreso",
            "status": "Estado",
            "pending": "Pendiente",
            "in_progress": "En progreso",
            "error": "Error",
            "warning": "Advertencia",
            "info": "Información",
            "confirm": "Confirmar",
            "unsaved_changes": "Tiene cambios sin guardar. ¿Desea guardar antes de cerrar?",
        },
        "fr": {
            "app_title": "Système de Transcription Local",
            "file": "Fichier",
            "open": "Ouvrir",
            "save": "Enregistrer",
            "save_as": "Enregistrer sous",
            "export": "Exporter",
            "exit": "Quitter",
            "edit": "Édition",
            "undo": "Annuler",
            "redo": "Rétablir",
            "cut": "Couper",
            "copy": "Copier",
            "paste": "Coller",
            "view": "Affichage",
            "analysis": "Analyse",
            "word_frequency": "Fréquence des mots",
            "speaker_statistics": "Statistiques des locuteurs",
            "export_report": "Exporter le rapport d'analyse",
            "language": "Langue",
            "plugins": "Extensions",
            "manage_plugins": "Gérer les extensions",
            "help": "Aide",
            "about": "À propos",
            "transcribe": "Transcrire",
            "start_transcription": "Démarrer la transcription",
            "stop": "Arrêter",
            "pause": "Pause",
            "resume": "Reprendre",
            "settings": "Paramètres",
            "model_size": "Taille du modèle",
            "enable_diarization": "Activer la diarisation",
            "select_language": "Sélectionner la langue",
            "auto_detect": "Détection automatique",
            "processing": "Traitement en cours...",
            "completed": "Terminé",
            "failed": "Échec",
            "cancel": "Annuler",
            "ok": "OK",
            "apply": "Appliquer",
            "search": "Rechercher",
            "search_placeholder": "Rechercher dans la transcription...",
            "no_results": "Aucun résultat trouvé",
            "speaker": "Locuteur",
            "confidence": "Confiance",
            "time": "Temps",
            "duration": "Durée",
            "segment": "Segment",
            "segments": "Segments",
            "words": "Mots",
            "characters": "Caractères",
            "add_comment": "Ajouter un commentaire",
            "comments": "Commentaires",
            "accept_changes": "Accepter les modifications",
            "discard_changes": "Annuler les modifications",
            "batch_process": "Traitement par lots",
            "add_files": "Ajouter des fichiers",
            "remove_selected": "Supprimer la sélection",
            "clear_all": "Tout effacer",
            "start_batch": "Démarrer le lot",
            "cancel_batch": "Annuler le lot",
            "export_results": "Exporter les résultats",
            "progress": "Progression",
            "status": "Statut",
            "pending": "En attente",
            "in_progress": "En cours",
            "error": "Erreur",
            "warning": "Avertissement",
            "info": "Information",
            "confirm": "Confirmer",
            "unsaved_changes": "Vous avez des modifications non enregistrées. Voulez-vous les enregistrer avant de fermer?",
        },
    }

    def __init__(self, default_language: str = "en"):
        """
        Initialize the language manager.

        Args:
            default_language: Default language code
        """
        self._current_language = default_language
        self._change_callbacks: list = []

    @property
    def current_language(self) -> str:
        """Get current language code."""
        return self._current_language

    @property
    def available_languages(self) -> Dict[str, str]:
        """Get dictionary of available languages."""
        return self.SUPPORTED_LANGUAGES.copy()

    def change_language(self, language_code: str) -> bool:
        """
        Change the current language.

        Args:
            language_code: Language code to switch to

        Returns:
            True if language was changed successfully
        """
        if language_code not in self.SUPPORTED_LANGUAGES:
            return False

        old_language = self._current_language
        self._current_language = language_code

        # Notify callbacks
        for callback in self._change_callbacks:
            try:
                callback(old_language, language_code)
            except Exception as e:
                print(f"Error in language change callback: {e}")

        return True

    def get_text(self, key: str, **kwargs) -> str:
        """
        Get translated text for a key.

        Args:
            key: Translation key
            **kwargs: Format arguments

        Returns:
            Translated text or key if not found
        """
        translations = self.TRANSLATIONS.get(self._current_language, {})

        # Fallback to English if key not found
        if key not in translations:
            translations = self.TRANSLATIONS.get("en", {})

        text = translations.get(key, key)

        # Apply format arguments if provided
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass

        return text

    def t(self, key: str, **kwargs) -> str:
        """Shorthand for get_text."""
        return self.get_text(key, **kwargs)

    def on_language_change(self, callback: Callable[[str, str], None]):
        """
        Register a callback for language changes.

        Args:
            callback: Function to call with (old_language, new_language)
        """
        self._change_callbacks.append(callback)

    def get_language_name(self, code: str) -> str:
        """
        Get the display name for a language code.

        Args:
            code: Language code

        Returns:
            Language name
        """
        return self.SUPPORTED_LANGUAGES.get(code, code)

    def detect_system_language(self) -> str:
        """
        Detect the system's preferred language.

        Returns:
            Detected language code or 'en' as default
        """
        try:
            import locale
            lang, _ = locale.getdefaultlocale()
            if lang:
                code = lang.split('_')[0].lower()
                if code in self.SUPPORTED_LANGUAGES:
                    return code
        except Exception:
            pass

        # Check environment variables
        for env_var in ['LANG', 'LANGUAGE', 'LC_ALL']:
            lang = os.environ.get(env_var, '')
            if lang:
                code = lang.split('_')[0].split('.')[0].lower()
                if code in self.SUPPORTED_LANGUAGES:
                    return code

        return "en"


# Global language manager instance
language_manager = LanguageManager()


def _(key: str, **kwargs) -> str:
    """
    Translation shorthand function.

    Args:
        key: Translation key
        **kwargs: Format arguments

    Returns:
        Translated text
    """
    return language_manager.get_text(key, **kwargs)
