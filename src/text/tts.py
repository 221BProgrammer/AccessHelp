# src/text/tts.py
import os
import time
import tempfile
from gtts import gTTS
import pygame

pygame.mixer.init()

class TextToSpeech:
    def __init__(self):
        self.is_playing = False
        self.current_file = None
    
    def speak(self, text, lang="en"):
        if not text.strip():
            print("No text provided")
            return

        try:
            # Stop any currently playing audio
            self.stop()
            
            print(f"🔊 Speaking: {text}")

            # Create temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
                temp_file = fp.name
                self.current_file = temp_file

            # Generate speech
            tts = gTTS(text=text, lang=lang)
            tts.save(temp_file)

            # Play audio
            pygame.mixer.music.load(temp_file)
            pygame.mixer.music.play()
            self.is_playing = True

        except Exception as e:
            print("TTS Error:", e)
    
    def pause(self):
        """Pause the current playback"""
        if self.is_playing:
            pygame.mixer.music.pause()
            print("⏸ Paused")
            return True
        return False
    
    def resume(self):
        """Resume the paused playback"""
        pygame.mixer.music.unpause()
        self.is_playing = True
        print("▶️ Resumed")
        return True
    
    def stop(self):
        """Stop the current playback"""
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        self.is_playing = False
        if self.current_file and os.path.exists(self.current_file):
            try:
                os.remove(self.current_file)
            except:
                pass
            self.current_file = None
        print("⏹ Stopped")