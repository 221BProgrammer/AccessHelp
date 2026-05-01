# src/chatbot/bot.py
"""
AccessHelp AI Chatbot
─────────────────────
Primary  : Ollama (local LLM — runs fully offline, no API key needed)
Fallback : Smart keyword-based responses (always works, zero dependencies)

HOW TO SET UP OLLAMA (one-time setup):
  1. Download from https://ollama.com and install it
  2. Open a terminal and run:
       ollama pull llama3          ← best quality  (~4.7 GB)
       OR
       ollama pull phi3            ← faster, lighter (~2.3 GB)
       OR
       ollama pull gemma2:2b       ← smallest, very fast (~1.6 GB)
  3. Ollama runs automatically in the background after install.
  4. Start your app normally:  streamlit run main.py

The chatbot will detect which model is available and use it automatically.
No Gradio URL, no Google Colab, no internet connection required.
"""

import requests
import json
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Ollama model preference order — first available one is used
# ─────────────────────────────────────────────────────────────────────────────
OLLAMA_MODEL_PRIORITY = [
    "llama3",       # Best quality for conversations
    "llama3.2",     # Newer llama variant
    "phi3",         # Microsoft's fast small model
    "phi3.5",
    "gemma2:2b",    # Google's lightweight model
    "gemma2",
    "mistral",      # Good general purpose
    "llama2",       # Older fallback
    "tinyllama",    # Smallest possible — very fast
]

OLLAMA_BASE_URL = "http://localhost:11434"


# ─────────────────────────────────────────────────────────────────────────────
# System prompt — tells the model exactly who it is and what to help with
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are AccessHelp, a compassionate and knowledgeable AI assistant \
specifically designed to support people with disabilities — particularly those who are \
blind, deaf, or mute/non-verbal.

Your role:
- Provide clear, practical, and empathetic advice
- Recommend assistive technologies, apps, and strategies
- Give emergency guidance tailored to each disability type
- Explain how to communicate with or assist people with disabilities
- Keep responses concise and easy to understand

Key topics you specialise in:
1. BLIND / VISUALLY IMPAIRED
   - Screen readers (NVDA, JAWS, VoiceOver, TalkBack)
   - Navigation apps (BlindSquare, Google Maps voice)
   - OCR apps (Seeing AI, KNFB Reader)
   - Braille technology and displays
   - Emergency: calling 911, stating "I am blind", using voice assistants

2. DEAF / HARD OF HEARING
   - Communication: lip reading, sign language (ASL, BSL), written notes
   - Apps: Google Live Transcribe, Ava, InnoCaption
   - Alerts: vibrating devices, flashing lights, smartwatches
   - Emergency: text-to-911, Video Relay Services (VRS)

3. MUTE / NON-VERBAL
   - AAC (Augmentative and Alternative Communication) devices
   - Apps: Proloquo2Go, Speak4Me, Talkitt, LetMeTalk
   - Communication boards and picture cards
   - Emergency: pre-typed messages, medical ID, 911 open line

Always be warm, patient, and encouraging. If someone seems to be in immediate danger, \
prioritise emergency guidance first. Format responses with clear sections when helpful, \
but keep them conversational and not overly long.
"""


class AccessibilityChatbot:
    """
    Accessibility-focused chatbot.

    Tries Ollama (local LLM) first.
    Falls back to smart keyword responses if Ollama is not running.
    """

    def __init__(self, api_url: Optional[str] = None):
        """
        api_url is accepted but ignored — kept for backwards compatibility
        with ui.py which passes GRADIO_URL.  Ollama is always local.
        """
        self.ollama_url   = OLLAMA_BASE_URL
        self.model        = None          # set after detecting available models
        self.is_connected = False
        self.conversation_history: list[dict] = []   # for multi-turn memory

        print("🤖 Initialising AccessHelp AI Assistant...")
        self._detect_ollama()

    # ══════════════════════════════════════════════════════════════════════════
    # OLLAMA DETECTION
    # ══════════════════════════════════════════════════════════════════════════

    def _detect_ollama(self):
        """Check if Ollama is running and pick the best available model."""
        try:
            r = requests.get(f"{self.ollama_url}/api/tags", timeout=3)
            if r.status_code != 200:
                raise ConnectionError("Ollama not reachable")

            installed = {m["name"].split(":")[0] for m in r.json().get("models", [])}
            installed_full = {m["name"] for m in r.json().get("models", [])}

            # Pick first preferred model that is installed
            for preferred in OLLAMA_MODEL_PRIORITY:
                base = preferred.split(":")[0]
                if base in installed or preferred in installed_full:
                    # Use exact name if found, else base name
                    self.model = preferred if preferred in installed_full else base
                    break

            if self.model:
                self.is_connected = True
                print(f"✅ Ollama connected! Using model: {self.model}")
                print("🔒 Running fully offline — no internet needed.")
            else:
                print("⚠️ Ollama is running but no supported model is installed.")
                print("   Run one of these in your terminal:")
                for m in OLLAMA_MODEL_PRIORITY[:4]:
                    print(f"     ollama pull {m}")
                print("🔄 Using smart fallback responses.")

        except Exception as e:
            print(f"⚠️ Ollama not found ({e})")
            print("💡 To enable AI: install Ollama from https://ollama.com")
            print("   Then run: ollama pull llama3")
            print("🔄 Using smart fallback responses for now.")

    # ══════════════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════════════

    def get_response(self, user_input: str, use_rag: bool = True) -> str:
        """Return a response to the user's message."""
        user_input = user_input.strip()
        if not user_input:
            return "Please say or type something so I can help you! 🌸"

        if self.is_connected and self.model:
            return self._get_ollama_response(user_input)
        return self._get_fallback_response(user_input)

    def clear_history(self):
        """Reset multi-turn conversation memory."""
        self.conversation_history = []
        return "Conversation cleared! How can I help you? 🌸"

    # ══════════════════════════════════════════════════════════════════════════
    # OLLAMA RESPONSE
    # ══════════════════════════════════════════════════════════════════════════

    def _get_ollama_response(self, user_input: str) -> str:
        """Send message to Ollama and return its reply."""
        try:
            # Build message list with system prompt + history + new message
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(self.conversation_history[-10:])  # keep last 5 turns
            messages.append({"role": "user", "content": user_input})

            payload = {
                "model":    self.model,
                "messages": messages,
                "stream":   False,
                "options": {
                    "temperature": 0.7,    # balanced creativity
                    "num_predict": 512,    # max tokens in reply
                },
            }

            r = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=60,            # local models can be slow on first call
            )

            if r.status_code == 200:
                reply = r.json()["message"]["content"].strip()

                # Store turn in history for multi-turn memory
                self.conversation_history.append(
                    {"role": "user",      "content": user_input}
                )
                self.conversation_history.append(
                    {"role": "assistant", "content": reply}
                )
                return reply

            # Non-200 — fall through to fallback
            print(f"⚠️ Ollama returned status {r.status_code}")
            return self._get_fallback_response(user_input)

        except requests.exceptions.Timeout:
            return (
                "⏰ The AI model is taking a bit long — it may be loading for the "
                "first time. Please try again in a few seconds."
            )
        except Exception as e:
            print(f"Ollama error: {e}")
            # Mark as disconnected so we stop retrying
            self.is_connected = False
            return self._get_fallback_response(user_input)

    # ══════════════════════════════════════════════════════════════════════════
    # SMART FALLBACK  (no AI needed — always works)
    # ══════════════════════════════════════════════════════════════════════════

    def _get_fallback_response(self, text: str) -> str:
        """
        Keyword-based responses covering the most common accessibility questions.
        Used when Ollama is not installed or not running.
        """
        t = text.lower()

        # ── Greetings ─────────────────────────────────────────────────────────
        if any(w in t for w in ["hello", "hi", "hey", "good morning", "good evening"]):
            return (
                "👋 Hello! I'm AccessHelp, your accessibility assistant.\n\n"
                "I can help with:\n"
                "- 👁️ Blind / Visually Impaired support\n"
                "- 🦻 Deaf / Hard of Hearing support\n"
                "- 🔇 Mute / Non-verbal support\n"
                "- 🚨 Emergency guidance\n\n"
                "What would you like to know? 🌸"
            )

        if "how are you" in t:
            return "I'm doing great and ready to help! 🌟 What accessibility question can I answer for you?"

        if any(w in t for w in ["thank", "thanks", "thank you"]):
            return "You're very welcome! 😊 Feel free to ask anything else."

        if any(w in t for w in ["bye", "goodbye", "see you"]):
            return "Goodbye! 👋 Take care and come back anytime. You're not alone. 🌸"

        # ── EMERGENCY ─────────────────────────────────────────────────────────
        if any(w in t for w in ["emergency", "911", "ambulance", "urgent", "danger", "help me"]):
            if "deaf" in t or "hearing" in t:
                return (
                    "🚨 **EMERGENCY — DEAF / HARD OF HEARING**\n\n"
                    "1. **Text 911** (available in most areas — check beforehand)\n"
                    "2. **Text your emergency contacts** with your location\n"
                    "3. **Video Relay Service (VRS)** — connects you via sign language interpreter\n"
                    "4. **TTY/TDD devices** at payphones if available\n"
                    "5. Activate **visual strobe alerts** if you have them\n\n"
                    "⚠️ Pre-save emergency contacts and location-sharing apps now!"
                )
            if any(w in t for w in ["mute", "can't speak", "cannot speak", "nonverbal", "non-verbal"]):
                return (
                    "🚨 **EMERGENCY — MUTE / NON-VERBAL**\n\n"
                    "1. **Call 911 and stay on the line** — operators are trained for silent calls\n"
                    "2. **Press 1** if prompted to confirm it's an emergency\n"
                    "3. Use **pre-typed emergency messages** on your phone\n"
                    "4. Wear a **medical alert bracelet** explaining your condition\n"
                    "5. Use an **AAC app** with emergency phrases pre-loaded\n\n"
                    "⚠️ Set up emergency shortcut on your phone lock screen now!"
                )
            if any(w in t for w in ["blind", "can't see", "cannot see", "visually"]):
                return (
                    "🚨 **EMERGENCY — BLIND / VISUALLY IMPAIRED**\n\n"
                    "1. **Call 911 immediately** using voice assistant (Hey Siri / OK Google)\n"
                    "2. Clearly say: *'I am blind and need help at [address]'*\n"
                    "3. Stay on the line and keep talking\n"
                    "4. Share your **live location** via voice: 'Share my location with [name]'\n"
                    "5. Use **emergency SOS** on your phone (hold side button)\n\n"
                    "⚠️ Set up voice-activated emergency contacts in advance!"
                )
            return (
                "🚨 **EMERGENCY — Call 911 (or your local emergency number) immediately!**\n\n"
                "If you cannot speak: stay on the line and press 1.\n"
                "If you cannot hear: use Text 911 or Video Relay Service."
            )

        # ── BLIND / VISUALLY IMPAIRED ─────────────────────────────────────────
        if any(w in t for w in ["blind", "visually impaired", "can't see", "low vision", "sight loss"]):
            if any(w in t for w in ["navigate", "navigation", "travel", "walk", "move around"]):
                return (
                    "🦯 **Navigation for Blind / Visually Impaired**\n\n"
                    "**Apps:**\n"
                    "- **BlindSquare** — GPS with detailed audio descriptions\n"
                    "- **Google Maps** — voice navigation (free)\n"
                    "- **Lazarillo** — free city navigation\n"
                    "- **Microsoft Soundscape** — 3D audio navigation\n\n"
                    "**Physical aids:**\n"
                    "- Long white cane (mobility & obstacle detection)\n"
                    "- Guide dog programs\n"
                    "- Wearable obstacle detectors (OrCam, Microsoft Seeing AI glasses)\n\n"
                    "Would you like more detail on any of these?"
                )
            if any(w in t for w in ["screen reader", "read screen", "computer", "phone"]):
                return (
                    "🖥️ **Screen Readers**\n\n"
                    "**Windows:** NVDA (free) · JAWS (paid)\n"
                    "**Mac / iPhone:** VoiceOver (built-in, free)\n"
                    "**Android:** TalkBack (built-in, free)\n"
                    "**Web:** ChromeVox (Chrome extension, free)\n\n"
                    "**Tips:**\n"
                    "- Enable in Settings → Accessibility\n"
                    "- NVDA + Firefox is the most popular free combo on Windows\n"
                    "- iPhone VoiceOver: triple-click side button to toggle\n\n"
                    "Which device are you using?"
                )
            if any(w in t for w in ["read", "book", "text", "document", "ocr"]):
                return (
                    "📖 **Reading Tools for Blind Users**\n\n"
                    "**OCR (scan & read printed text):**\n"
                    "- **Seeing AI** (free, iOS) — reads text, describes scenes & people\n"
                    "- **KNFB Reader** — highly accurate document reader\n"
                    "- **Google Lens** (free) — point camera at text to hear it\n\n"
                    "**Audiobooks & digital reading:**\n"
                    "- **Libby / OverDrive** — free audiobooks via library card\n"
                    "- **Audible** — paid, huge catalogue\n"
                    "- **BARD Mobile** (USA) — free from Library of Congress\n\n"
                    "This app's **Text Reader** section can also read any text aloud!"
                )
            return (
                "👁️ **Blind / Visually Impaired Support**\n\n"
                "**Technology:**\n"
                "- Screen readers: NVDA, JAWS, VoiceOver, TalkBack\n"
                "- Navigation: BlindSquare, Google Maps (voice)\n"
                "- Reading: Seeing AI, KNFB Reader, Google Lens\n"
                "- Voice assistants: Siri, Alexa, Google Assistant\n\n"
                "**Daily living:**\n"
                "- Talking watches, clocks, and thermometers\n"
                "- Braille labels for appliances\n"
                "- High-contrast and large-print materials\n\n"
                "Ask me about any specific area — navigation, apps, reading, or emergency help!"
            )

        # ── DEAF / HARD OF HEARING ────────────────────────────────────────────
        if any(w in t for w in ["deaf", "hard of hearing", "hearing loss", "hearing impaired", "can't hear"]):
            if any(w in t for w in ["communicate", "talk", "conversation", "speak to"]):
                return (
                    "💬 **Communicating with Deaf / Hard of Hearing People**\n\n"
                    "**Do:**\n"
                    "- Face them directly so they can lip-read\n"
                    "- Speak clearly at normal pace (not exaggerated)\n"
                    "- Use written notes or a speech-to-text app\n"
                    "- Use gestures and facial expressions\n"
                    "- Learn a few basic signs (hello, thank you, help)\n\n"
                    "**Apps that help:**\n"
                    "- **Google Live Transcribe** — real-time captions (free)\n"
                    "- **Ava** — group conversation captions (free tier)\n"
                    "- **Rogervoice** — captioned phone calls\n\n"
                    "**Don't:** shout, exaggerate mouth movements, or cover your face."
                )
            if any(w in t for w in ["caption", "subtitle", "transcribe", "live caption"]):
                return (
                    "📝 **Captioning & Transcription Apps**\n\n"
                    "- **Google Live Transcribe** — free, real-time, works offline (Android)\n"
                    "- **Apple Live Captions** — built-in on iPhone/iPad (iOS 16+)\n"
                    "- **Ava** — great for group conversations\n"
                    "- **InnoCaption** — captioned phone calls (free in USA)\n"
                    "- **CART** — professional real-time captioning for events\n"
                    "- **Microsoft Teams / Zoom** — have built-in live captions\n\n"
                    "This app's **Speech → Text** section also provides live transcription!"
                )
            if any(w in t for w in ["sign language", "asl", "bsl", "sign"]):
                return (
                    "🤟 **Sign Language Resources**\n\n"
                    "**Learn sign language:**\n"
                    "- **ASL University** (Lifeprint.com) — free online lessons\n"
                    "- **SignSchool** — free beginner ASL\n"
                    "- **Marlee Signs** (YouTube) — free video lessons\n"
                    "- **Duolingo** — ASL course available\n\n"
                    "**Interpreter services:**\n"
                    "- **Video Remote Interpreting (VRI)** — on-demand via tablet/phone\n"
                    "- **Video Relay Service (VRS)** — free phone calls via interpreter\n\n"
                    "The **Sign Language** section in this app can help detect signs via camera!"
                )
            return (
                "🦻 **Deaf / Hard of Hearing Support**\n\n"
                "**Communication apps:**\n"
                "- Google Live Transcribe, Ava, InnoCaption\n\n"
                "**Alert systems:**\n"
                "- Vibrating smartwatches for notifications\n"
                "- Flashing light doorbells & smoke alarms\n"
                "- Bed shakers for alarm clocks\n\n"
                "**Entertainment:**\n"
                "- Closed captions on all streaming services\n"
                "- Subtitle apps for videos\n\n"
                "Ask me about captioning, sign language, communication, or emergency help!"
            )

        # ── MUTE / NON-VERBAL ─────────────────────────────────────────────────
        if any(w in t for w in ["mute", "non-verbal", "nonverbal", "can't speak", "cannot speak",
                                 "aac", "augmentative", "alternative communication"]):
            if any(w in t for w in ["app", "software", "device", "tool"]):
                return (
                    "📱 **AAC Apps & Communication Tools**\n\n"
                    "**Beginner / Simple:**\n"
                    "- **Speak4Me** — customisable phrases, easy to use\n"
                    "- **LetMeTalk** — free, open source AAC\n"
                    "- **CommunicoTot** — simple symbol-based communication\n\n"
                    "**Advanced:**\n"
                    "- **Proloquo2Go** — industry standard, symbol + text, iOS\n"
                    "- **TouchChat** — flexible AAC with many vocabulary sets\n"
                    "- **LAMP Words for Life** — motor learning approach\n\n"
                    "**Text-to-speech:**\n"
                    "- **Talkitt** — learns personal speech patterns\n"
                    "- **Voice Dream Writer** — typing + speech\n"
                    "- **Predictable** — word prediction + TTS\n\n"
                    "This app's **Text → Speech** section lets you type and speak instantly!"
                )
            return (
                "🔇 **Mute / Non-verbal Support**\n\n"
                "**Communication options:**\n"
                "- AAC devices and apps (Proloquo2Go, LetMeTalk)\n"
                "- Text-to-speech apps (Speak4Me, Talkitt)\n"
                "- Communication boards (physical or digital)\n"
                "- Writing / typing on phone\n\n"
                "**Emergency preparedness:**\n"
                "- Pre-type emergency messages on your phone\n"
                "- Wear medical ID with your condition explained\n"
                "- Programme emergency phrases into your AAC device\n\n"
                "Ask me about specific apps, communication strategies, or emergency help!"
            )

        # ── SCREEN READER / TECHNOLOGY ────────────────────────────────────────
        if any(w in t for w in ["screen reader", "nvda", "jaws", "voiceover", "talkback"]):
            return (
                "🖥️ **Screen Reader Guide**\n\n"
                "**Windows (free): NVDA**\n"
                "- Download: nvaccess.org\n"
                "- Works with Firefox, Chrome, Word, Outlook\n"
                "- Shortcut: Ctrl+Alt+N to start\n\n"
                "**Windows (paid): JAWS**\n"
                "- Most feature-rich, used in workplaces\n"
                "- 40-minute demo mode available free\n\n"
                "**Apple devices: VoiceOver**\n"
                "- Mac: Cmd+F5 to toggle\n"
                "- iPhone: Settings → Accessibility → VoiceOver\n"
                "- Supports Braille displays\n\n"
                "**Android: TalkBack**\n"
                "- Settings → Accessibility → TalkBack\n"
                "- Works with most Android apps\n\n"
                "Which operating system are you using?"
            )

        # ── BRAILLE ───────────────────────────────────────────────────────────
        if "braille" in t:
            return (
                "⠃⠗⠁⠊⠇⠇⠑ **Braille Support**\n\n"
                "**Braille displays (hardware):**\n"
                "- Connect to phone/computer and show text as Braille\n"
                "- Popular: Focus Blue, Orbit Reader, BrailleNote Touch\n\n"
                "**Learning Braille:**\n"
                "- **Hadley** (hadley.edu) — free online Braille courses\n"
                "- **BRL: Braille Through Remote Learning** — free\n"
                "- National Federation of the Blind resources\n\n"
                "**This app:**\n"
                "- The **Haptic Braille** section converts text to vibration/beep patterns\n"
                "- You can learn and feel Braille letters interactively!\n\n"
                "Would you like to know more about Braille learning or hardware displays?"
            )

        # ── APP RECOMMENDATIONS ───────────────────────────────────────────────
        if any(w in t for w in ["app", "recommend", "best app", "which app", "software"]):
            return (
                "📱 **Top Accessibility App Recommendations**\n\n"
                "**For Blind users:**\n"
                "- Seeing AI (iOS) — scene & text description\n"
                "- BlindSquare — GPS navigation\n"
                "- NVDA / VoiceOver — screen readers\n\n"
                "**For Deaf users:**\n"
                "- Google Live Transcribe — real-time captions\n"
                "- Ava — group captioning\n"
                "- Roger Voice — captioned calls\n\n"
                "**For Mute / Non-verbal:**\n"
                "- Proloquo2Go — AAC communication\n"
                "- LetMeTalk — free AAC\n"
                "- Speak4Me — simple TTS phrases\n\n"
                "**General accessibility:**\n"
                "- Be My Eyes — video call sighted volunteers\n"
                "- Aira — professional sighted assistance on demand\n\n"
                "Tell me which disability you need apps for and I'll go deeper!"
            )

        # ── GENERAL HELP / CATCH-ALL ──────────────────────────────────────────
        return (
            "💡 **AccessHelp AI Assistant**\n\n"
            "I specialise in accessibility support for:\n"
            "- 👁️ **Blind / Visually Impaired** — screen readers, navigation, OCR\n"
            "- 🦻 **Deaf / Hard of Hearing** — captions, sign language, alert systems\n"
            "- 🔇 **Mute / Non-verbal** — AAC devices, TTS apps, communication boards\n"
            "- 🚨 **Emergency guidance** for each disability type\n\n"
            "**Try asking:**\n"
            "- 'Best apps for blind people'\n"
            "- 'How to communicate with a deaf person'\n"
            "- 'Emergency help for mute person'\n"
            "- 'What is a screen reader'\n"
            "- 'Sign language resources'\n\n"
            "How can I help you today? 🌸"
        )