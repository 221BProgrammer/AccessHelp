# src/voice/voice_assistant.py
import threading
from .voice_controller import VoiceController


class VoiceAssistant:
    """
    Voice assistant that can be activated by wake word or button press.

    Threading note
    --------------
    listen_for_command() spawns a daemon thread so the Streamlit UI thread
    is never blocked.  The callback you pass in must only mutate
    st.session_state — it must NOT call st.rerun() (that is the UI thread's
    job, triggered by a flag check at the top of run_app()).
    """

    def __init__(self):
        self.voice_controller = VoiceController()
        self.is_active = False
        self._is_listening = False          # internal guard against double-listen
        self._lock = threading.Lock()

    # ── Activation helpers ────────────────────────────────────────────────────

    def activate(self):
        """Mark the assistant as active (e.g. button pressed)."""
        self.is_active = True
        print("🎤 Voice assistant activated!")

    def deactivate(self):
        """Mark the assistant as inactive."""
        self.is_active = False
        print("🔇 Voice assistant deactivated.")

    # ── Synchronous listen (used directly in the UI thread) ───────────────────

    def listen_once(self, duration: int = 5) -> str | None:
        """
        Blocking listen — call this from the Streamlit UI thread when you
        already have a spinner / placeholder shown.  Returns the recognised
        text or None.
        """
        return self.voice_controller.listen(duration=duration)

    # ── Asynchronous listen (used for wake-word follow-up) ───────────────────

    def listen_for_command(self, callback=None):
        """
        Non-blocking: listen in a background thread and call *callback(text)*
        when a command is recognised.

        The callback receives a single str argument (the recognised text, or
        an empty string if nothing was heard).  It must only set
        st.session_state flags — never call st.rerun().
        """
        with self._lock:
            if self._is_listening:
                print("⚠️ Already listening — ignoring duplicate request.")
                return
            self._is_listening = True

        def _worker():
            try:
                command = self.voice_controller.listen(duration=5)
                if callback:
                    callback(command or "")
            except Exception as e:
                print(f"❌ VoiceAssistant listen error: {e}")
                if callback:
                    callback("")
            finally:
                with self._lock:
                    self._is_listening = False

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    # ── Convenience wrapper ───────────────────────────────────────────────────

    def listen_and_execute(self, command_handler):
        """
        Listen in the background and pass the result to *command_handler*.
        command_handler(text: str) → any
        """
        self.listen_for_command(callback=command_handler)
