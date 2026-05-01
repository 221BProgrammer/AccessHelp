# src/voice/wake_word.py
import speech_recognition as sr
import threading
import time

class WakeWordDetector:
    """
    Wake word detector for "Hey Access" that captures the full command.

    IMPORTANT: The callback is called from a background thread.
    Do NOT call st.rerun() or any Streamlit function inside the callback.
    Instead, set a flag in st.session_state and let the main thread
    pick it up on the next natural rerun.
    """

    def __init__(self, wake_words=None):
        if wake_words is None:
            wake_words = ["hey access", "access help", "hello access"]
        self.wake_words = wake_words
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.listening = False
        self.callback = None

        # Calibrate once at startup
        try:
            with self.microphone as source:
                print("🔧 Calibrating microphone for wake word...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            print(f"⚠️ Microphone calibration warning: {e}")

        print("🎤 Wake word detector ready!")
        print(f"📢 Say: {', '.join(self.wake_words)} followed by your command")
        print("📢 Example: 'Hey Access open chatbot'")

    def start_listening(self, callback=None):
        """Start listening for wake word in a background thread."""
        self.listening = True
        self.callback = callback
        self._start_thread()

    def _start_thread(self):
        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()

    def _listen_loop(self):
        """
        Background loop: continuously listen for wake word + optional command.
        Only sets session-state flags; never calls st.rerun() directly.
        """
        while self.listening:
            try:
                with self.microphone as source:
                    # Short timeout so the while-loop stays responsive to stop_listening()
                    audio = self.recognizer.listen(
                        source, timeout=2, phrase_time_limit=6
                    )

                try:
                    text = self.recognizer.recognize_google(audio).lower()
                    print(f"👂 Heard: {text}")

                    for wake_word in self.wake_words:
                        if wake_word in text:
                            print(f"🔊 Wake word detected: '{wake_word}'")

                            # Extract any command spoken after the wake word
                            command = text.replace(wake_word, "", 1).strip()

                            # Fire the callback (must NOT call st.rerun() inside)
                            if self.callback:
                                self.callback(command)

                            break   # Only handle first matching wake word

                except sr.UnknownValueError:
                    pass    # Nothing intelligible heard — keep looping
                except sr.RequestError as e:
                    print(f"⚠️ Speech recognition API error: {e}")

            except sr.WaitTimeoutError:
                pass    # Silence timeout — keep looping
            except Exception as e:
                print(f"⚠️ Wake word loop error: {e}")

            time.sleep(0.05)    # Small yield to prevent CPU spin

    def stop_listening(self):
        """Stop the background listening thread."""
        self.listening = False
        print("🔇 Wake word detector stopped.")
