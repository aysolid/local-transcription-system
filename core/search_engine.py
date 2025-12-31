# core/search_engine.py
"""
Search and analysis engine for transcriptions.
Provides full-text search, word frequency analysis, and speaker statistics.
"""

import os
import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path


@dataclass
class SearchResult:
    """Represents a single search result."""
    segment_index: int
    text: str
    speaker: str
    start: float
    end: float
    match_positions: List[tuple]  # (start, end) positions of matches in text
    score: float = 1.0


class TranscriptionIndex:
    """
    Full-text search index for transcriptions using Whoosh.
    """

    def __init__(self, index_dir: str = None):
        """
        Initialize the transcription index.

        Args:
            index_dir: Directory to store the index
        """
        self.index_dir = index_dir or os.path.join(os.path.expanduser("~"), ".transcription_index")
        self._index = None
        self._schema = None

    def _ensure_index(self):
        """Ensure the index exists and is ready."""
        if self._index is not None:
            return

        try:
            from whoosh import index
            from whoosh.fields import Schema, TEXT, ID, NUMERIC, STORED

            # Define schema
            self._schema = Schema(
                segment_id=ID(stored=True, unique=True),
                text=TEXT(stored=True),
                speaker=TEXT(stored=True),
                start=NUMERIC(stored=True),
                end=NUMERIC(stored=True),
                file_path=ID(stored=True)
            )

            # Create or open index
            os.makedirs(self.index_dir, exist_ok=True)

            if index.exists_in(self.index_dir):
                self._index = index.open_dir(self.index_dir)
            else:
                self._index = index.create_in(self.index_dir, self._schema)

        except ImportError:
            print("Warning: Whoosh not installed. Full-text search unavailable.")
            self._index = None

    def add_transcription(self, segments: List[Any], file_path: str):
        """
        Add transcription segments to the index.

        Args:
            segments: List of transcription segments
            file_path: Path to the source audio file
        """
        self._ensure_index()

        if self._index is None:
            return

        writer = self._index.writer()

        for i, seg in enumerate(segments):
            segment_id = f"{file_path}_{i}"
            writer.update_document(
                segment_id=segment_id,
                text=seg.text if hasattr(seg, 'text') else seg.get('text', ''),
                speaker=seg.speaker if hasattr(seg, 'speaker') else seg.get('speaker', ''),
                start=seg.start if hasattr(seg, 'start') else seg.get('start', 0),
                end=seg.end if hasattr(seg, 'end') else seg.get('end', 0),
                file_path=file_path
            )

        writer.commit()

    def search(self, query: str, limit: int = 50) -> List[SearchResult]:
        """
        Search for text in indexed transcriptions.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of SearchResult objects
        """
        self._ensure_index()

        if self._index is None:
            return []

        try:
            from whoosh.qparser import QueryParser

            results = []
            with self._index.searcher() as searcher:
                parser = QueryParser("text", self._index.schema)
                q = parser.parse(query)

                search_results = searcher.search(q, limit=limit)

                for hit in search_results:
                    # Find match positions
                    match_positions = []
                    text = hit['text']
                    query_lower = query.lower()
                    text_lower = text.lower()

                    start = 0
                    while True:
                        pos = text_lower.find(query_lower, start)
                        if pos == -1:
                            break
                        match_positions.append((pos, pos + len(query)))
                        start = pos + 1

                    results.append(SearchResult(
                        segment_index=int(hit['segment_id'].split('_')[-1]),
                        text=text,
                        speaker=hit['speaker'],
                        start=hit['start'],
                        end=hit['end'],
                        match_positions=match_positions,
                        score=hit.score
                    ))

            return results

        except Exception as e:
            print(f"Search error: {e}")
            return []

    def clear_index(self):
        """Clear all indexed data."""
        self._ensure_index()

        if self._index is not None:
            from whoosh import index
            self._index = index.create_in(self.index_dir, self._schema)


class SearchAnalyzer:
    """
    Analyzer for transcription content.
    Provides word frequency, speaker statistics, and phrase extraction.
    """

    # Common stop words to exclude from analysis
    STOP_WORDS = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
        'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
        'must', 'shall', 'can', 'need', 'dare', 'ought', 'used', 'i', 'you', 'he',
        'she', 'it', 'we', 'they', 'what', 'which', 'who', 'whom', 'this', 'that',
        'these', 'those', 'am', 'been', 'being', 'as', 'if', 'then', 'than',
        'so', 'just', 'also', 'very', 'too', 'only', 'own', 'same', 'here',
        'there', 'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
        'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
        'out', 'over', 'under', 'again', 'further', 'once', 'um', 'uh', 'like',
        'yeah', 'okay', 'ok', 'yes', 'no', 'well', 'right', 'now', 'know',
    }

    def __init__(self):
        """Initialize the analyzer."""
        pass

    def analyze_transcription(self, segments: List[Any]) -> Dict[str, Any]:
        """
        Perform comprehensive analysis on transcription segments.

        Args:
            segments: List of transcription segments

        Returns:
            Dictionary containing analysis results
        """
        # Extract all text
        all_text = " ".join(
            seg.text if hasattr(seg, 'text') else seg.get('text', '')
            for seg in segments
        )

        # Get analysis components
        word_freq = self.get_word_frequency(all_text)
        speaker_stats = self.get_speaker_statistics(segments)
        phrases = self.extract_common_phrases(all_text)
        wordcloud_data = self.get_wordcloud_data(all_text)

        # Calculate total duration
        total_duration = 0
        if segments:
            last_seg = segments[-1]
            total_duration = last_seg.end if hasattr(last_seg, 'end') else last_seg.get('end', 0)

        return {
            'word_frequency': word_freq,
            'speaker_statistics': speaker_stats,
            'common_phrases': phrases,
            'wordcloud_data': wordcloud_data,
            'total_words': len(all_text.split()),
            'total_segments': len(segments),
            'total_duration': total_duration,
            'words_per_minute': (len(all_text.split()) / total_duration * 60) if total_duration > 0 else 0,
            'unique_words': len(set(self._tokenize(all_text))),
        }

    def get_word_frequency(self, text: str, top_n: int = 50) -> List[tuple]:
        """
        Get word frequency count.

        Args:
            text: Text to analyze
            top_n: Number of top words to return

        Returns:
            List of (word, count) tuples
        """
        words = self._tokenize(text)
        filtered_words = [w for w in words if w not in self.STOP_WORDS and len(w) > 2]
        counter = Counter(filtered_words)
        return counter.most_common(top_n)

    def get_speaker_statistics(self, segments: List[Any]) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for each speaker.

        Args:
            segments: List of transcription segments

        Returns:
            Dictionary mapping speaker to their statistics
        """
        speaker_data = {}

        for seg in segments:
            speaker = seg.speaker if hasattr(seg, 'speaker') else seg.get('speaker', 'Unknown')
            text = seg.text if hasattr(seg, 'text') else seg.get('text', '')
            start = seg.start if hasattr(seg, 'start') else seg.get('start', 0)
            end = seg.end if hasattr(seg, 'end') else seg.get('end', 0)
            duration = end - start

            if speaker not in speaker_data:
                speaker_data[speaker] = {
                    'total_duration': 0,
                    'total_words': 0,
                    'segment_count': 0,
                    'words': [],
                }

            speaker_data[speaker]['total_duration'] += duration
            speaker_data[speaker]['segment_count'] += 1
            words = text.split()
            speaker_data[speaker]['total_words'] += len(words)
            speaker_data[speaker]['words'].extend(words)

        # Calculate additional metrics
        for speaker, data in speaker_data.items():
            data['avg_segment_duration'] = (
                data['total_duration'] / data['segment_count']
                if data['segment_count'] > 0 else 0
            )
            data['words_per_minute'] = (
                data['total_words'] / data['total_duration'] * 60
                if data['total_duration'] > 0 else 0
            )
            # Get top words for this speaker
            filtered = [w.lower() for w in data['words'] if w.lower() not in self.STOP_WORDS and len(w) > 2]
            data['top_words'] = Counter(filtered).most_common(10)
            del data['words']  # Remove raw words to save memory

        return speaker_data

    def extract_common_phrases(self, text: str, min_count: int = 2, max_words: int = 4) -> List[tuple]:
        """
        Extract common phrases (n-grams) from text.

        Args:
            text: Text to analyze
            min_count: Minimum occurrences to include
            max_words: Maximum words in a phrase

        Returns:
            List of (phrase, count) tuples
        """
        words = self._tokenize(text)
        phrases = Counter()

        # Extract n-grams (2 to max_words)
        for n in range(2, max_words + 1):
            for i in range(len(words) - n + 1):
                ngram = tuple(words[i:i + n])

                # Skip if contains only stop words
                if all(w in self.STOP_WORDS for w in ngram):
                    continue

                phrases[ngram] += 1

        # Filter by minimum count and convert to strings
        result = [
            (' '.join(phrase), count)
            for phrase, count in phrases.items()
            if count >= min_count
        ]

        return sorted(result, key=lambda x: x[1], reverse=True)[:30]

    def get_wordcloud_data(self, text: str) -> Dict[str, int]:
        """
        Get word frequency data suitable for word cloud generation.

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping words to their frequencies
        """
        words = self._tokenize(text)
        filtered_words = [w for w in words if w not in self.STOP_WORDS and len(w) > 2]
        return dict(Counter(filtered_words))

    def simple_search(
        self,
        segments: List[Any],
        query: str,
        case_sensitive: bool = False
    ) -> List[SearchResult]:
        """
        Perform simple text search through segments.

        Args:
            segments: List of transcription segments
            query: Search query
            case_sensitive: Whether to perform case-sensitive search

        Returns:
            List of SearchResult objects
        """
        results = []

        for i, seg in enumerate(segments):
            text = seg.text if hasattr(seg, 'text') else seg.get('text', '')
            search_text = text if case_sensitive else text.lower()
            search_query = query if case_sensitive else query.lower()

            if search_query in search_text:
                # Find all match positions
                match_positions = []
                start = 0
                while True:
                    pos = search_text.find(search_query, start)
                    if pos == -1:
                        break
                    match_positions.append((pos, pos + len(query)))
                    start = pos + 1

                results.append(SearchResult(
                    segment_index=i,
                    text=text,
                    speaker=seg.speaker if hasattr(seg, 'speaker') else seg.get('speaker', ''),
                    start=seg.start if hasattr(seg, 'start') else seg.get('start', 0),
                    end=seg.end if hasattr(seg, 'end') else seg.get('end', 0),
                    match_positions=match_positions,
                    score=len(match_positions)  # Score by number of matches
                ))

        return sorted(results, key=lambda x: x.score, reverse=True)

    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into words.

        Args:
            text: Text to tokenize

        Returns:
            List of words
        """
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', '', text.lower())
        return text.split()

    def compare_speakers(self, segments: List[Any]) -> Dict[str, Any]:
        """
        Compare speaking patterns between speakers.

        Args:
            segments: List of transcription segments

        Returns:
            Dictionary with comparison metrics
        """
        stats = self.get_speaker_statistics(segments)

        if len(stats) < 2:
            return {'message': 'Not enough speakers for comparison'}

        speakers = list(stats.keys())
        total_duration = sum(s['total_duration'] for s in stats.values())

        comparison = {
            'speakers': speakers,
            'speaking_time_distribution': {
                speaker: (data['total_duration'] / total_duration * 100) if total_duration > 0 else 0
                for speaker, data in stats.items()
            },
            'word_count_distribution': {
                speaker: data['total_words']
                for speaker, data in stats.items()
            },
            'speaking_rate': {
                speaker: data['words_per_minute']
                for speaker, data in stats.items()
            },
            'most_talkative': max(stats.items(), key=lambda x: x[1]['total_duration'])[0],
            'fastest_speaker': max(stats.items(), key=lambda x: x[1]['words_per_minute'])[0],
        }

        return comparison
