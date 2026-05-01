# src/voice/voice_controller.py
import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import whisper
import os
import time
import speech_recognition as sr

class VoiceController:
    def __init__(self):
        print("🎤 Loading Whisper model for voice control...")
        self.model = whisper.load_model("base")
        
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        try:
            with self.microphone as source:
                print("🔧 Adjusting for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except:
            pass
        
        print("✅ Voice model loaded!")

    def listen(self, duration=4, fs=16000, use_google_fallback=True):
        """Listen for voice command using Whisper or Google fallback"""
        try:
            print("🎤 Speak your command...")
            
            if use_google_fallback:
                try:
                    with self.microphone as source:
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"🧠 Command (Google): {text}")
                    return text
                    
                except sr.WaitTimeoutError:
                    print("⏱️ No speech detected")
                    return None
                except sr.UnknownValueError:
                    print("🤔 Could not understand")
                except sr.RequestError:
                    print("🌐 Google API error, falling back to Whisper")
            
            print("🔄 Using Whisper for transcription...")
            audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
            sd.wait()

            filename = "voice_command.wav"
            wav.write(filename, fs, audio)

            result = self.model.transcribe(filename)
            command = result["text"].lower()

            print(f"🧠 Command (Whisper): {command}")

            if os.path.exists(filename):
                os.remove(filename)

            return command

        except Exception as e:
            print("Voice Error:", e)
            return None


def interpret_command(command):
    """Interpret command for menu navigation"""
    if not command:
        return None

    command = command.lower()
    
    # Remove common filler words
    for word in ["open", "go to", "take me to", "navigate to", "switch to", "show me", "launch"]:
        if command.startswith(word):
            command = command.replace(word, "", 1).strip()
    
    feature_map = {
        "chatbot": "Chatbot",
        "chat": "Chatbot",
        "assistant": "Chatbot",
        
        "speech to text": "Speech → Text",
        "dictation": "Speech → Text",
        "voice to text": "Speech → Text",
        
        "text to speech": "Text → Speech",
        "read": "Text → Speech",
        "speak": "Text → Speech",
        
        "sign language": "Sign Language",
        "sign": "Sign Language",
        
        "multilingual": "Multilingual",
        "translate": "Multilingual",
        
        "pdf": "PDF Summarizer",
        "summarize": "PDF Summarizer",
        
        "text reader": "Text Reader",
        "reader": "Text Reader",
        
        "emergency": "🆘 Emergency",
        "help": "🆘 Emergency",
        "sos": "🆘 Emergency",
        
        "profile": "⚙️ User Profile",
        "settings": "⚙️ User Profile",
        
        "haptic": "🖐️ Haptic Braille",
        "braille": "🖐️ Haptic Braille",

        "speech to sign": "🗣️ Speech → Sign",
        "sign translator": "🗣️ Speech → Sign",
        "sign animator": "🗣️ Speech → Sign",
        
        "saved phrases": "Saved Phrases",
        "phrases": "Saved Phrases"
    }
    
    for key, feature in feature_map.items():
        if key in command:
            return feature
    
    return None


def interpret_action_command(command, current_menu):
    """Interpret command for actions inside current menu"""
    if not command:
        return None

    command = command.lower()

    # ── Chatbot ────────────────────────────────────────────────────────────────
    if current_menu == "Chatbot":
        if "clear" in command or "erase" in command:
            return "CLEAR"
        # Any other spoken text is treated as a question to the bot
        return "ASK_QUESTION"

    # ── Multilingual ───────────────────────────────────────────────────────────
    elif current_menu == "Multilingual":
        if "translate" in command:
            return "TRANSLATE"
        # FIX: return LANG_<name> not LANG_<code> so process_voice_action can
        #      look the name up in its own lang_map dict.
        lang_names = ["english", "hindi", "japanese", "french", "spanish", "german", "chinese"]
        for lang in lang_names:
            if lang in command:
                return f"LANG_{lang}"          # e.g. "LANG_hindi"
        # Any other spoken text is treated as text to translate
        if command.strip():
            return "ENTER_TEXT"

    # ── Text → Speech ──────────────────────────────────────────────────────────
    elif current_menu == "Text → Speech":
        if any(w in command for w in ["speak", "read", "say", "play"]):
            return "SPEAK"
        if "enter text" in command or "type" in command:
            return "ENTER_TEXT"

    # ── Speech → Text ──────────────────────────────────────────────────────────
    elif current_menu == "Speech → Text":
        if any(w in command for w in ["record", "listen", "start"]):
            return "RECORD"

    # ── PDF Summarizer ─────────────────────────────────────────────────────────
    elif current_menu == "PDF Summarizer":
        if "summarize" in command or "summary" in command:
            return "SUMMARIZE"
        if "upload" in command or "open" in command:
            return "UPLOAD_PDF"

    # ── Text Reader ────────────────────────────────────────────────────────────
    elif current_menu == "Text Reader":
        if "pause" in command:
            return "PAUSE"
        if "resume" in command or "continue" in command:
            return "RESUME"
        if "stop" in command:
            return "STOP"
        if "play" in command or "read" in command or "start" in command:
            return "PLAY"

    # ── Emergency ──────────────────────────────────────────────────────────────
    elif current_menu == "🆘 Emergency":
        if any(w in command for w in ["send sos", "emergency", "send alert", "sos"]):
            return "SEND_SOS"
        if "add contact" in command or "new contact" in command:
            return "ADD_CONTACT"

    # ── Haptic Braille ─────────────────────────────────────────────────────────
    elif current_menu == "🖐️ Haptic Braille":
        if any(w in command for w in ["play", "vibrate", "start"]):
            return "PLAY_HAPTIC"
        if "record speech" in command or "record" in command:
            return "RECORD_SPEECH"
        if "stop" in command:
            return "STOP_HAPTIC"
        if "text" in command or "type" in command:
            return "TEXT_INPUT"
        if "learn" in command:
            return "LEARN_BRAILLE"

    return None