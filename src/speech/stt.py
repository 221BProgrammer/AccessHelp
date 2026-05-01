import whisper
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav

class SpeechToText:
    def __init__(self):
        print("Loading Whisper model...")
        self.model = whisper.load_model("base")  # you can use "small" later
        print("Model loaded!")

    def record_audio(self, duration=5, fs=16000):
        print("Recording... Speak now!")
        audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait()
        print("Recording finished.")

        wav.write("temp.wav", fs, audio)
        return "temp.wav"

    def transcribe(self, audio_path):
        print("Transcribing...")
        result = self.model.transcribe(audio_path)
        return result["text"]