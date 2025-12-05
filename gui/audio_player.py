# gui/audio_player.py
import pyaudio
import wave
import threading
import time
from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np

class AudioPlayer(QThread):
    """Audio player with segment synchronization"""
    
    position_changed = pyqtSignal(float)  # Current position in seconds
    playback_finished = pyqtSignal()
    
    def __init__(self, audio_path):
        super().__init__()
        self.audio_path = audio_path
        self.wf = wave.open(audio_path, 'rb')
        self.p = pyaudio.PyAudio()
        
        self.stream = None
        self.is_playing = False
        self.current_position = 0.0
        self.playback_rate = 1.0
        self.target_segment = None  # (start, end)
        
        # Audio parameters
        self.chunk_size = 1024
        self.sample_rate = self.wf.getframerate()
        self.channels = self.wf.getnchannels()
        
        self.lock = threading.Lock()
    
    def play_segment(self, start_time, end_time):
        """Play specific audio segment"""
        self.target_segment = (start_time, end_time)
        self.current_position = start_time
        
        # Calculate frame position
        start_frame = int(start_time * self.sample_rate)
        end_frame = int(end_time * self.sample_rate)
        
        self.wf.setpos(start_frame)
        
        if not self.is_playing:
            self.start()
    
    def run(self):
        """Main playback loop"""
        self.is_playing = True
        
        # Open stream
        self.stream = self.p.open(
            format=self.p.get_format_from_width(self.wf.getsampwidth()),
            channels=self.channels,
            rate=int(self.sample_rate * self.playback_rate),
            output=True,
            frames_per_buffer=self.chunk_size
        )
        
        # Calculate total frames for segment
        if self.target_segment:
            start_time, end_time = self.target_segment
            total_frames = int((end_time - start_time) * self.sample_rate)
            frames_read = 0
        
        try:
            while self.is_playing:
                if self.target_segment:
                    # Check if segment playback is complete
                    if frames_read >= total_frames:
                        break
                    
                    # Read audio data
                    data = self.wf.readframes(self.chunk_size)
                    
                    # Calculate how many frames we're actually reading
                    frames_in_chunk = len(data) // (self.wf.getsampwidth() * self.channels)
                    frames_read += frames_in_chunk
                    
                    # Update current position
                    self.current_position = start_time + (frames_read / self.sample_rate)
                    
                else:
                    # Continuous playback
                    data = self.wf.readframes(self.chunk_size)
                    if not data:
                        break  # End of file
                
                # Play audio
                self.stream.write(data)
                
                # Emit position update
                self.position_changed.emit(self.current_position)
                
        except Exception as e:
            print(f"Playback error: {e}")
        
        finally:
            self.stop()
            self.playback_finished.emit()
    
    def stop(self):
        """Stop playback"""
        self.is_playing = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
    
    def pause(self):
        """Pause playback"""
        self.is_playing = False
    
    def resume(self):
        """Resume playback"""
        self.is_playing = True
    
    def set_playback_rate(self, rate):
        """Set playback speed (0.5x, 1x, 1.5x, 2x)"""
        self.playback_rate = rate
    
    def get_duration(self):
        """Get total audio duration"""
        return self.wf.getnframes() / self.sample_rate
    
    def __del__(self):
        """Cleanup"""
        self.stop()
        if self.wf:
            self.wf.close()
        self.p.terminate()