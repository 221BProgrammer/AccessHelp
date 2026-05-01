import streamlit as st
import sys
import os
import json
import base64
import tempfile
import platform
from datetime import datetime
from deep_translator import GoogleTranslator

# Add the root directory to Python path (IMPORTANT)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.text.tts import TextToSpeech
from src.speech.stt import SpeechToText
from src.text.pdf_reader import PDFReader
from src.text.summarizer import TextSummarizer
from src.emergency.alert import EmergencySystem
from src.user.profile_manager import UserProfileManager
from src.voice.voice_controller import VoiceController, interpret_command, interpret_action_command
from src.haptic.haptic_feedback import HapticFeedback, BrailleDisplayEmulator, BraillePattern, VibrationPattern
from src.vision.sign_animator import SignAnimator
# from src.vision.ocr_enhanced import ocr_enhanced
# from src.vision.screen_reader import screen_reader
# from src.browser.extension_api import start_extension_api, extension_api
# from src.utils.error_handler import error_handler, safe_execute

# Import the new AI chatbot from the chatbot folder
from src.chatbot.bot import AccessibilityChatbot


# Initialize modules
tts = TextToSpeech()
stt = SpeechToText()
pdf_reader = PDFReader()
summarizer = TextSummarizer()
emergency = EmergencySystem()
profile_manager = UserProfileManager()
voice = VoiceController()
haptic = HapticFeedback()
braille_display = BrailleDisplayEmulator()
sign_animator = SignAnimator()

# Add this helper function
def get_temp_path(filename):
    """Get a proper temp path that works on all platforms"""
    temp_dir = tempfile.gettempdir()
    return os.path.join(temp_dir, filename)

# ============================================
# INITIALIZE AI CHATBOT WITH OLLAMA
# ============================================
try:
    chatbot = AccessibilityChatbot()
    print("✅ AI Chatbot initialized successfully!")

except Exception as e:
    print(f"⚠️ Error initializing AI Chatbot: {e}")
    print("⚠️ Using fallback mode...")
    chatbot = None
# ============================================

def get_background_image(theme):
    """Get background image from local file for light or dark mode"""
    LIGHT_IMAGE_URL = "https://wallpapercave.com/wp/wp15391627.jpg"  # ← REPLACE THIS
    DARK_IMAGE_URL = "https://wallpapers.com/images/hd/garden-of-words-makoto-shinkai-rain-aesthetic-7afz9sxgr1mpzaal.jpg"   # ← REPLACE THIS

    if theme == "light":
        return LIGHT_IMAGE_URL if LIGHT_IMAGE_URL else None
    else:
        return DARK_IMAGE_URL if DARK_IMAGE_URL else None

def get_background_css(theme):
    """Generate working CSS for background image with proper readability"""
    
    bg_url = get_background_image(theme)
    
    if theme == "light":
        overlay_color = "rgba(255, 255, 255, 0.85)"
        card_bg = "rgba(255, 255, 255, 0.95)"
        text_color = "#1a1a2e"
        text_secondary = "#4a5568"
        border_color = "rgba(102, 126, 234, 0.2)"
        gradient_start = "#667eea"
        gradient_end = "#764ba2"
        input_bg = "#ffffff"
        input_text = "#1a1a2e"
        input_placeholder = "#a0aec0"
        selectbox_bg = "#ffffff"
        selectbox_text = "#1a1a2e"
        selectbox_hover = "#f0f0f0"
        dropdown_bg = "#ffffff"  # White dropdown for light mode
        dropdown_text = "#1a1a2e"  # Dark text for light mode
    else:  # dark mode
        overlay_color = "rgba(0, 0, 0, 0.85)"
        card_bg = "rgba(26, 26, 46, 0.95)"
        text_color = "#e2e8f0"
        text_secondary = "#a0aec0"
        border_color = "rgba(102, 126, 234, 0.3)"
        gradient_start = "#667eea"
        gradient_end = "#764ba2"
        input_bg = "#1a1a2e"
        input_text = "#e2e8f0"
        input_placeholder = "#718096"
        selectbox_bg = "#1a1a2e"  # Dark background for selectbox
        selectbox_text = "#e2e8f0"  # Light text
        selectbox_hover = "#2d2d4a"
        dropdown_bg = "#1a1a2e"  # BLACK/DARK background for dropdown
        dropdown_text = "#e2e8f0"  # WHITE text for dark mode
    
    css = f"""
    <style>
        /* Sidebar scrolling */
        [data-testid="stSidebar"] {{
            overflow-y: auto !important;
            height: 100vh !important;
            max-height: 100vh !important;
            scrollbar-width: thin !important;
        }}

        /* Main app background */
        .stApp {{
            background-image: url('{bg_url}') !important;
            background-size: cover !important;
            background-position: center !important;
            background-repeat: no-repeat !important;
            background-attachment: fixed !important;
        }}

        .stApp::before {{
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background-color: {overlay_color};
            z-index: 0;
        }}

        .stApp > div {{
            position: relative;
            z-index: 1;
        }}
        
        /* Dropdown menu container */
        [data-baseweb="popover"] {{
            background-color: {dropdown_bg} !important;
        }}
        
        [data-baseweb="popover"] * {{
            background-color: {dropdown_bg} !important;
            color: {dropdown_text} !important;
        }}

        [data-baseweb="menu"] {{
            background-color: {dropdown_bg} !important;
            border: 1px solid {border_color} !important;
            border-radius: 10px !important;
        }}

        [data-baseweb="menu"] li {{
            background-color: {dropdown_bg} !important;
            color: {dropdown_text} !important;
        }}

        [data-baseweb="menu"] li:hover {{
            background-color: {selectbox_hover} !important;
            color: {dropdown_text} !important;
        }}

        [data-baseweb="menu"] li[aria-selected="true"] {{
            background: linear-gradient(135deg, {gradient_start} 0%, {gradient_end} 100%) !important;
            color: white !important;
        }}

        [data-baseweb="menu"] li span {{
            color: {dropdown_text} !important;
            background-color: transparent !important;
        }}

        [data-baseweb="select"] > div {{
            background-color: {selectbox_bg} !important;
            border-color: {border_color} !important;
        }}

        [data-baseweb="select"] span {{
            color: {selectbox_text} !important;
        }}

        [data-baseweb="popover"] [role="listbox"],
        [data-baseweb="popover"] [role="option"] {{
            background-color: {dropdown_bg} !important;
            color: {dropdown_text} !important;
        }}
        
        
        /* Main selectbox container */
        .stSelectbox > div > div {{
            background-color: {selectbox_bg} !important;
            border: 1px solid {border_color} !important;
            border-radius: 10px !important;
        }}
        
        /* Selected value text inside the box */
        .stSelectbox > div > div > div {{
            color: {selectbox_text} !important;
            background-color: transparent !important;
        }}
        
        /* Sidebar selectbox */
        [data-testid="stSidebar"] .stSelectbox > div > div {{
            background-color: {selectbox_bg} !important;
        }}
        
        [data-testid="stSidebar"] .stSelectbox > div > div > div {{
            color: {selectbox_text} !important;
        }}
        
        /* Dropdown arrow icon */
        .stSelectbox svg {{
            fill: {selectbox_text} !important;
        }}

        
        .main-header {{
            background: linear-gradient(135deg, {gradient_start} 0%, {gradient_end} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3em;
            font-weight: bold;
            text-align: center;
            margin-bottom: 30px;
            padding: 20px;
            position: relative;
            z-index: 2;
        }}

        .feature-card {{
            background: {card_bg};
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 25px;
            margin: 15px 0;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid {border_color};
            position: relative;
            z-index: 2;
        }}

        .stButton > button {{
            background: linear-gradient(135deg, {gradient_start} 0%, {gradient_end} 100%);
            color: white !important;
            border: none;
            transition: all 0.3s ease;
            font-weight: 600;
            padding: 10px 20px;
            border-radius: 10px;
        }}

        .stButton > button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }}

        /* Input fields */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {{
            background-color: {input_bg} !important;
            color: {input_text} !important;
            border: 1px solid {border_color} !important;
            border-radius: 10px !important;
            padding: 10px !important;
            font-size: 16px !important;
        }}

        .stTextInput > div > div > input::placeholder,
        .stTextArea > div > div > textarea::placeholder {{
            color: {input_placeholder} !important;
        }}

        /* Sidebar */
        [data-testid="stSidebar"] {{
            background: {card_bg};
            backdrop-filter: blur(10px);
            border-right: 1px solid {border_color};
        }}

        [data-testid="stSidebar"] * {{
            color: {text_color};
        }}

        /* General text */
        label, .stMarkdown, p, li, div {{
            color: {text_color};
        }}

        h1, h2, h3, h4, h5, h6 {{
            color: {text_color};
            font-weight: 600;
        }}

        /* Animation container */
        .animation-container {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 9999;
            overflow: hidden;
        }}
    </style>
    """
    return css

def get_sakura_petals_animation():
    """Sakura flowers falling animation for light mode"""
    return """
    <style>
        @keyframes fall {
            0% {
                transform: translateY(-10vh) rotate(0deg);
                opacity: 1;
            }
            100% {
                transform: translateY(100vh) rotate(360deg);
                opacity: 0;
            }
        }

        .animation-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 9999;
            overflow: hidden;
        }

        .sakura-petal {
            position: absolute;
            animation: fall linear infinite;
            font-size: 20px;
        }
    </style>

    <div class="animation-container" id="animation-container">
        <div class="sakura-petal" style="left:5%; animation-duration:7s; animation-delay:0s;">🌸</div>
        <div class="sakura-petal" style="left:15%; animation-duration:6s; animation-delay:1s;">🌸</div>
        <div class="sakura-petal" style="left:25%; animation-duration:8s; animation-delay:2s;">🌸</div>
        <div class="sakura-petal" style="left:35%; animation-duration:5s; animation-delay:0.5s;">🌸</div>
        <div class="sakura-petal" style="left:45%; animation-duration:7s; animation-delay:1.5s;">🌸</div>
        <div class="sakura-petal" style="left:55%; animation-duration:6s; animation-delay:3s;">🌸</div>
        <div class="sakura-petal" style="left:65%; animation-duration:9s; animation-delay:0.8s;">🌸</div>
        <div class="sakura-petal" style="left:75%; animation-duration:7s; animation-delay:2.5s;">🌸</div>
        <div class="sakura-petal" style="left:85%; animation-duration:6s; animation-delay:1.2s;">🌸</div>
        <div class="sakura-petal" style="left:95%; animation-duration:8s; animation-delay:4s;">🌸</div>
    </div>
    """

def get_leaves_animation():
    """Leaves flowing from left to right for dark mode (wind effect)"""
    return """
    <style>
        @keyframes blow {
            0% {
                transform: translateX(-10vw) translateY(0px) rotate(0deg);
                opacity: 1;
            }
            100% {
                transform: translateX(110vw) translateY(30px) rotate(360deg);
                opacity: 0;
            }
        }

        .animation-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 9999;
            overflow: hidden;
        }

        .leaf {
            position: absolute;
            animation: blow linear infinite;
            font-size: 22px;
            filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.3));
        }
    </style>

    <div class="animation-container" id="animation-container">
        <div class="leaf" style="top:5%; animation-duration:6s; animation-delay:0s;">🍃</div>
        <div class="leaf" style="top:15%; animation-duration:7s; animation-delay:1s;">🍂</div>
        <div class="leaf" style="top:25%; animation-duration:5s; animation-delay:2s;">🍃</div>
        <div class="leaf" style="top:35%; animation-duration:8s; animation-delay:0.5s;">🍂</div>
        <div class="leaf" style="top:45%; animation-duration:6s; animation-delay:1.5s;">🍃</div>
        <div class="leaf" style="top:55%; animation-duration:7s; animation-delay:3s;">🍂</div>
        <div class="leaf" style="top:65%; animation-duration:5.5s; animation-delay:0.8s;">🍃</div>
        <div class="leaf" style="top:75%; animation-duration:8s; animation-delay:2.5s;">🍂</div>
        <div class="leaf" style="top:85%; animation-duration:6.5s; animation-delay:1.2s;">🍃</div>
        <div class="leaf" style="top:95%; animation-duration:7.5s; animation-delay:4s;">🍂</div>
        <div class="leaf" style="top:10%; animation-duration:6.8s; animation-delay:0.3s;">🍃</div>
        <div class="leaf" style="top:40%; animation-duration:7.2s; animation-delay:2.2s;">🍂</div>
        <div class="leaf" style="top:70%; animation-duration:5.8s; animation-delay:1.8s;">🍃</div>
        <div class="leaf" style="top:90%; animation-duration:6.5s; animation-delay:3.5s;">🍂</div>
    </div>
    """


def speak_and_announce(message):
    """Speak a message and show it on screen"""
    tts.speak(message)
    st.info(f"🔊 {message}")

def process_voice_action(action, current_menu):
    """Process voice actions based on current menu"""
    if action == "SPEAK":
        st.session_state.voice_trigger_speak = True
    elif action == "RECORD":
        st.session_state.voice_trigger_record = True
    elif action == "TRANSLATE":
        st.session_state.voice_trigger_translate = True
    elif action.startswith("LANG_"):
        lang_map = {
            "english": "en", "hindi": "hi", "japanese": "ja", 
            "french": "fr", "spanish": "es", "german": "de", "chinese": "zh"
        }
        lang_name = action.replace("LANG_", "")
        st.session_state.voice_lang_selection = lang_map.get(lang_name, "en")
    elif action == "ENTER_TEXT":
        st.session_state.voice_text_mode = True
    elif action == "ASK_QUESTION":
        st.session_state.voice_ask_mode = True
    elif action == "SUMMARIZE":
        st.session_state.voice_trigger_summarize = True
    elif action == "UPLOAD_PDF":
        st.session_state.voice_upload_pdf = True
        st.info("📁 Please select a PDF file manually (voice upload not yet supported)")
    elif action == "PLAY_HAPTIC":
        st.session_state.voice_trigger_haptic = True
    elif action == "RECORD_SPEECH":
        st.session_state.voice_trigger_speech_record = True
    elif action == "TEXT_INPUT":
        st.session_state.voice_text_input_mode = True
    elif action == "LEARN_BRAILLE":
        st.session_state.voice_learn_braille = True
    elif action == "STOP_HAPTIC":
        st.session_state.voice_stop_haptic = True
    elif action == "CLEAR":
        st.session_state.voice_clear_chat = True
    # NEW: Emergency contact addition actions
    elif action == "SEND_SOS":
        st.session_state.voice_send_sos = True
    elif action == "ADD_CONTACT":
        st.session_state.voice_add_contact_mode = True
    elif action == "CONFIRM_CONTACT":
        st.session_state.voice_confirm_contact = True
    elif action == "CANCEL_CONTACT":
        st.session_state.voice_cancel_contact = True

def run_app():
    # 🎤 VOICE ASSISTANT SETUP
    if "voice_assistant" not in st.session_state:
        from src.voice.wake_word import WakeWordDetector
        from src.voice.voice_assistant import VoiceAssistant
        st.session_state.voice_assistant = VoiceAssistant()
        st.session_state.wake_word_detector = None
        st.session_state.wake_word_enabled = False
        st.session_state.last_menu = ""
        st.session_state.waiting_for_command = False
        st.session_state.theme = "light"  # Default theme
        
        # NEW: Command mode for blind users
        st.session_state.command_mode = False
        st.session_state.voice_command_listening = False
        
        # NEW: Emergency contact workflow states
        st.session_state.pending_contact = {}
        st.session_state.waiting_for_contact_name = False
        st.session_state.waiting_for_contact_phone = False
        st.session_state.waiting_for_contact_email = False
        st.session_state.waiting_for_contact_confirm = False
        
        # NEW: Multilingual workflow states
        st.session_state.waiting_for_translation_text = False
        st.session_state.waiting_for_language = False
        
        # Voice action session states
        if "voice_action" not in st.session_state:
            st.session_state.voice_action = None
        if "voice_text_input" not in st.session_state:
            st.session_state.voice_text_input = ""
        if "voice_lang_selection" not in st.session_state:
            st.session_state.voice_lang_selection = None
        if "voice_trigger_speak" not in st.session_state:
            st.session_state.voice_trigger_speak = False
        if "voice_trigger_record" not in st.session_state:
            st.session_state.voice_trigger_record = False
        if "voice_trigger_translate" not in st.session_state:
            st.session_state.voice_trigger_translate = False
        if "voice_clear_chat" not in st.session_state:
            st.session_state.voice_clear_chat = False
        if "voice_trigger_summarize" not in st.session_state:
            st.session_state.voice_trigger_summarize = False
        if "voice_upload_pdf" not in st.session_state:
            st.session_state.voice_upload_pdf = False
        
        # NEW: Emergency voice states
        if "voice_send_sos" not in st.session_state:
            st.session_state.voice_send_sos = False
        if "voice_add_contact_mode" not in st.session_state:
            st.session_state.voice_add_contact_mode = False
        if "voice_confirm_contact" not in st.session_state:
            st.session_state.voice_confirm_contact = False
        if "voice_cancel_contact" not in st.session_state:
            st.session_state.voice_cancel_contact = False

        # Voice text storage (separate from widget keys)
        if "voice_tts_text" not in st.session_state:
            st.session_state.voice_tts_text = ""
        
        if "voice_multilingual_text" not in st.session_state:
            st.session_state.voice_multilingual_text = ""
        
        if "voice_haptic_text" not in st.session_state:
            st.session_state.voice_haptic_text = ""

        # Haptic Braille session states
        if "voice_trigger_haptic" not in st.session_state:
            st.session_state.voice_trigger_haptic = False
        if "voice_trigger_speech_record" not in st.session_state:
            st.session_state.voice_trigger_speech_record = False
        if "voice_text_input_mode" not in st.session_state:
            st.session_state.voice_text_input_mode = False
        if "voice_learn_braille" not in st.session_state:
            st.session_state.voice_learn_braille = False
        if "voice_stop_haptic" not in st.session_state:
            st.session_state.voice_stop_haptic = False
        if "haptic_text_input" not in st.session_state:
            st.session_state.haptic_text_input = ""

        # Speech → Sign session states
        if "sign_input_text" not in st.session_state:
            st.session_state.sign_input_text = ""
        if "sign_current_frame" not in st.session_state:
            st.session_state.sign_current_frame = 0
        if "sign_auto_play" not in st.session_state:
            st.session_state.sign_auto_play = False
        if "sign_speed" not in st.session_state:
            st.session_state.sign_speed = "Normal"
    
    
    if st.session_state.get("voice_listen_trigger", False) and not st.session_state.get("voice_command_listening", False):
        st.session_state.voice_command_listening = True
        st.session_state.voice_listen_trigger = False
        
        command = st.session_state.voice_assistant.voice_controller.listen(duration=5)
        
        if command:
            command_lower = command.lower()
            
            # Check for command mode activation
            if "command mode" in command_lower or "command mode initiated" in command_lower:
                st.session_state.command_mode = True
                speak_and_announce("Command mode activated. You can now control everything with your voice. Say help for commands.")
                st.rerun()
            
            # Check for command mode deactivation
            elif "exit command mode" in command_lower or "disable command mode" in command_lower:
                st.session_state.command_mode = False
                speak_and_announce("Command mode deactivated.")
                st.rerun()
            
            # If in command mode, process the command
            elif st.session_state.get("command_mode", False):
                
                # Check for menu navigation
                if any(word in command_lower for word in ["open", "go to", "switch to"]):
                    feature = interpret_command(command)
                    if feature:
                        st.session_state["voice_nav"] = feature
                        speak_and_announce(f"Opening {feature}")
                        st.rerun()
                
                # Handle emergency contact workflow
                elif st.session_state.waiting_for_contact_name:
                    st.session_state.pending_contact["name"] = command
                    st.session_state.waiting_for_contact_name = False
                    st.session_state.waiting_for_contact_phone = True
                    speak_and_announce(f"Contact name is {command}. Please say the phone number with country code")
                    st.rerun()
                
                elif st.session_state.waiting_for_contact_phone:
                    # Clean phone number
                    phone = ''.join(c for c in command if c.isdigit() or c == '+')
                    st.session_state.pending_contact["phone"] = phone
                    st.session_state.waiting_for_contact_phone = False
                    st.session_state.waiting_for_contact_email = True
                    speak_and_announce(f"Phone number is {phone}. Please say the email address or say skip")
                    st.rerun()
                
                elif st.session_state.waiting_for_contact_email:
                    if "skip" in command_lower:
                        st.session_state.pending_contact["email"] = ""
                    else:
                        st.session_state.pending_contact["email"] = command
                    st.session_state.waiting_for_contact_email = False
                    st.session_state.waiting_for_contact_confirm = True
                    speak_and_announce(f"Email is {st.session_state.pending_contact.get('email', 'skipped')}. Say confirm to save or cancel to cancel")
                    st.rerun()
                
                elif st.session_state.waiting_for_contact_confirm:
                    if "confirm" in command_lower or "yes" in command_lower:
                        # Save contact
                        contacts_file = os.path.join(BASE_DIR, "data", "emergency_contacts.json")
                        if os.path.exists(contacts_file):
                            with open(contacts_file, "r") as f:
                                contacts = json.load(f)
                        else:
                            contacts = []
                        
                        contacts.append({
                            "name": st.session_state.pending_contact["name"],
                            "phone": st.session_state.pending_contact["phone"],
                            "email": st.session_state.pending_contact.get("email", ""),
                            "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        with open(contacts_file, "w") as f:
                            json.dump(contacts, f, indent=2)
                        
                        speak_and_announce(f"Contact {st.session_state.pending_contact['name']} saved successfully")
                        st.session_state.pending_contact = {}
                        st.session_state.waiting_for_contact_confirm = False
                    else:
                        speak_and_announce("Contact addition cancelled")
                        st.session_state.pending_contact = {}
                        st.session_state.waiting_for_contact_confirm = False
                    st.rerun()
                
                # Handle multilingual workflow
                elif st.session_state.waiting_for_translation_text:
                    st.session_state.voice_multilingual_text = command
                    st.session_state.waiting_for_translation_text = False
                    speak_and_announce(f"Text to translate: {command}. Now say the language name or say translate")
                    st.rerun()
                
                elif st.session_state.waiting_for_language:
                    lang_map = {"english": "en", "hindi": "hi", "japanese": "ja", 
                               "french": "fr", "spanish": "es", "german": "de", "chinese": "zh"}
                    for lang_name, lang_code in lang_map.items():
                        if lang_name in command_lower:
                            st.session_state.voice_lang_selection = lang_code
                            st.session_state.waiting_for_language = False
                            speak_and_announce(f"Language set to {lang_name}")
                            st.rerun()
                            break
                
                # Handle other menu-specific actions
                else:
                    action = interpret_action_command(command, st.session_state.get("menu", "Home"))
                    if action:
                        st.session_state.voice_action = action
                        st.rerun()
                    else:
                        # Check if it's a chatbot question
                        if st.session_state.get("menu") == "Chatbot" and chatbot:
                            speak_and_announce("Let me think about that...")
                            response = chatbot.get_response(command)
                            st.session_state.chat_messages.append({"role": "user", "content": command})
                            st.session_state.chat_messages.append({"role": "assistant", "content": response})
                            speak_and_announce(response)
                            st.rerun()
                        else:
                            speak_and_announce(f"Command not recognized. Say help for available commands.")
        
        st.session_state.voice_command_listening = False
    
    # 👤 LOAD USER
    user = None
    if "username" in st.session_state and st.session_state["username"]:
        user = profile_manager.get_user(st.session_state["username"])
        if user and "theme" in user:
            st.session_state.theme = user.get("theme", "light")

    # Get background image based on theme
    bg_image = get_background_image(st.session_state.theme)
    
    # 🎨 THEME TOGGLE IN SIDEBAR (Only Light and Dark modes)
    st.sidebar.markdown("## 🎨 Appearance")
    
    # Theme selection with icons (removed Sakura mode)
    theme_options = {
        "light": "☀️ Light Mode",
        "dark": "🌙 Dark Mode"
    }
    
    selected_theme = st.sidebar.selectbox(
        "Select Theme",
        options=list(theme_options.keys()),
        format_func=lambda x: theme_options[x],
        index=list(theme_options.keys()).index(st.session_state.theme) if st.session_state.theme in theme_options else 0
    )
    
    if selected_theme != st.session_state.theme:
        st.session_state.theme = selected_theme
        st.rerun()

    background_css = get_background_css(selected_theme)
    st.markdown(background_css, unsafe_allow_html=True)
    
    # Add animation based on theme (Sakura for light, Leaves for dark)
    if selected_theme == "light":
        st.markdown(get_sakura_petals_animation(), unsafe_allow_html=True)
    else:
        st.markdown(get_leaves_animation(), unsafe_allow_html=True)
    
    # NEW: Command mode indicator in sidebar
    if st.session_state.get("command_mode", False):
        st.sidebar.success("🎤 **VOICE COMMAND MODE ACTIVE** 🎤")
        st.sidebar.info("Say 'exit command mode' to disable")
    else:
        st.sidebar.info("🎤 Say 'command mode' to enable hands-free voice control")
    
    # 🎨 THEME SPECIFIC STYLES
    if selected_theme == "dark":
        if bg_image:
            st.markdown(f"""
                <style>
                    /* Dark Mode Styles */
                    .stApp {{
                        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                        color: #ffffff;
                    }}
                    
                    .stApp::before {{
                        content: '';
                        position: fixed;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                        background: url('{bg_image}') center/cover fixed;
                        opacity: 0.2;
                        z-index: -1;
                    }}
                    
                    .main-header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        font-size: 3em;
                        font-weight: bold;
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    
                    .stButton>button {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border: none;
                        transition: all 0.3s ease;
                    }}
                    
                    .stButton>button:hover {{
                        transform: translateY(-2px);
                        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
                    }}
                    
                    .stTextInput>div>div>input, .stTextArea>div>div>textarea {{
                        background-color: rgba(255, 255, 255, 0.1);
                        color: white;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                    }}
                    
                    .stSelectbox>div>div {{
                        background-color: rgba(255, 255, 255, 0.1);
                        color: white;
                    }}
                    
                    .feature-card {{
                        background: rgba(26, 26, 46, 0.7);
                        backdrop-filter: blur(10px);
                        border-radius: 15px;
                        padding: 20px;
                        margin: 10px 0;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                        border: 1px solid rgba(102, 126, 234, 0.3);
                    }}
                </style>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <style>
                    /* Dark Mode Styles (Fallback - no image) */
                    .stApp {{
                        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
                        color: #ffffff;
                    }}
                    
                    .main-header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        font-size: 3em;
                        font-weight: bold;
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    
                    .stButton>button {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border: none;
                        transition: all 0.3s ease;
                    }}
                    
                    .stButton>button:hover {{
                        transform: translateY(-2px);
                        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
                    }}
                    
                    .stTextInput>div>div>input, .stTextArea>div>div>textarea {{
                        background-color: rgba(255, 255, 255, 0.1);
                        color: white;
                        border: 1px solid rgba(255, 255, 255, 0.2);
                    }}
                    
                    .stSelectbox>div>div {{
                        background-color: rgba(255, 255, 255, 0.1);
                        color: white;
                    }}
                    
                    .feature-card {{
                        background: rgba(26, 26, 46, 0.7);
                        backdrop-filter: blur(10px);
                        border-radius: 15px;
                        padding: 20px;
                        margin: 10px 0;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                        border: 1px solid rgba(102, 126, 234, 0.3);
                    }}
                </style>
            """, unsafe_allow_html=True)
        
    else:  # Light mode
        if bg_image:
            st.markdown(f"""
                <style>
                    /* Light Mode Styles */
                    .stApp {{
                        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                        color: #2c3e50;
                    }}
                    
                    .stApp::before {{
                        content: '';
                        position: fixed;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                        background: url('{bg_image}') center/cover fixed;
                        opacity: 0.25;
                        z-index: -1;
                    }}
                    
                    .main-header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        font-size: 3em;
                        font-weight: bold;
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    
                    .stButton>button {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border: none;
                        transition: all 0.3s ease;
                    }}
                    
                    .stButton>button:hover {{
                        transform: translateY(-2px);
                        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
                    }}
                    
                    .stTextInput>div>div>input, .stTextArea>div>div>textarea {{
                        background-color: white;
                        border: 1px solid #e0e0e0;
                        border-radius: 8px;
                    }}
                    
                    .feature-card {{
                        background: rgba(255, 255, 255, 0.8);
                        backdrop-filter: blur(10px);
                        border-radius: 15px;
                        padding: 20px;
                        margin: 10px 0;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        border: 1px solid rgba(102, 126, 234, 0.2);
                    }}
                </style>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <style>
                    /* Light Mode Styles (Fallback - no image) */
                    .stApp {{
                        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                        color: #2c3e50;
                    }}
                    
                    .main-header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        font-size: 3em;
                        font-weight: bold;
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    
                    .stButton>button {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        border: none;
                        transition: all 0.3s ease;
                    }}
                    
                    .stButton>button:hover {{
                        transform: translateY(-2px);
                        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
                    }}
                    
                    .stTextInput>div>div>input, .stTextArea>div>div>textarea {{
                        background-color: white;
                        border: 1px solid #e0e0e0;
                        border-radius: 8px;
                    }}
                    
                    .feature-card {{
                        background: rgba(255, 255, 255, 0.8);
                        backdrop-filter: blur(10px);
                        border-radius: 15px;
                        padding: 20px;
                        margin: 10px 0;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                        border: 1px solid rgba(102, 126, 234, 0.2);
                    }}
                </style>
            """, unsafe_allow_html=True)
    
    # 🎨 UI SETTINGS PANEL
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🎨 UI Settings")
    simple_mode = st.sidebar.checkbox("🧩 Simple Mode")
    high_contrast = st.sidebar.checkbox("🌗 High Contrast Mode")
    large_buttons = st.sidebar.checkbox("🔘 Large Buttons", value=True)
    
    # 🎨 ACCESSIBILITY CSS (High Contrast Override)
    if high_contrast:
        st.markdown("""
            <style>
                /* Gentle High Contrast Mode - Enhances without breaking */
                
                /* Increase contrast for all text */
                .stApp, .stApp p, .stApp label, .stMarkdown, 
                h1, h2, h3, h4, h5, h6 {
                    font-weight: 500 !important;
                }
                
                /* Make borders more visible */
                .feature-card, .stButton > button, 
                .stTextInput>div>div>input,
                .stTextArea>div>div>textarea,
                [data-testid="stSidebar"] {
                    border-width: 2px !important;
                    border-style: solid !important;
                }
                
                /* Enhance focus indicators */
                button:focus, input:focus, select:focus, textarea:focus {
                    outline: 3px solid #ffcc00 !important;
                    outline-offset: 3px !important;
                }
                
                /* Make links more obvious */
                a {
                    text-decoration: underline !important;
                    text-decoration-thickness: 2px !important;
                }
                
                /* Increase contrast for important elements */
                .stAlert, .stSuccess, .stError, .stWarning {
                    border-width: 2px !important;
                    font-weight: bold !important;
                }
            </style>
        """, unsafe_allow_html=True)

        st.markdown("""
            <script>
                // Remove animation containers
                var containers = document.getElementsByClassName('animation-container');
                for(var i = 0; i < containers.length; i++) {
                    containers[i].style.display = 'none';
                }
            </script>
        """, unsafe_allow_html=True)

    if large_buttons:
        st.markdown("""
            <style>
                button {
                    height: 60px;
                    font-size: 20px !important;
                    border-radius: 10px;
                }
            </style>
        """, unsafe_allow_html=True)
    
    # 🔍 SCREEN READER OPTIMIZATION
    st.markdown("""
        <style>
            /* Screen reader only text */
            .sr-only {
                position: absolute;
                width: 1px;
                height: 1px;
                padding: 0;
                margin: -1px;
                overflow: hidden;
                clip: rect(0, 0, 0, 0);
                white-space: nowrap;
                border: 0;
            }
            
            /* Focus indicators for keyboard navigation */
            button:focus, input:focus, select:focus {
                outline: 3px solid #ffcc00 !important;
                outline-offset: 2px !important;
            }
            
            /* Smooth transitions */
            * {
                transition: all 0.3s ease;
            }
        </style>
        
        <!-- ARIA live region for announcements -->
        <div aria-live="polite" aria-atomic="true" class="sr-only" id="announcer"></div>
    """, unsafe_allow_html=True)
    
    # 🧠 TITLE with animation
    st.markdown("""
        <div class="main-header">
            🌸 AccessHelp - Accessibility Assistant 🌸
        </div>
        <p style="text-align: center; font-size: 1.2em; margin-bottom: 30px;">
            Empowering Everyone, Everywhere
        </p>
    """, unsafe_allow_html=True)
    
    # 🧩 SIMPLE MODE MENU
    all_features = [
        "Text → Speech",
        "Speech → Text",
        "Sign Language",
        "🗣️ Speech → Sign",
        "Saved Phrases",
        "Multilingual",
        "Chatbot",
        "PDF Summarizer",
        "Text Reader",
        # "📸 OCR Scanner",
        # "🔍 Screen Reader",
        # "🌐 Browser Extension",
        "🆘 Emergency",
        "⚙️ User Profile",
        "🖐️ Haptic Braille"
    ]

    simple_features = [
        "Text → Speech",
        "Speech → Text",
        "🆘 Emergency",
        "🖐️ Haptic Braille"
    ]

    # Get the current feature list based on mode
    current_features = simple_features if simple_mode else all_features

    if "menu" not in st.session_state:
        st.session_state.menu = current_features[0]

    # Check if stored menu is in current feature list
    if st.session_state.menu not in current_features:
        # If not, reset to first feature
        st.session_state.menu = current_features[0]
    
    # Create selectbox with safe index
    try:
        current_index = current_features.index(st.session_state.menu)
    except ValueError:
        current_index = 0
        st.session_state.menu = current_features[0]
    
    selected_menu = st.sidebar.selectbox(
        "✨ Choose Feature",
        simple_features if simple_mode else all_features,
        index=(simple_features if simple_mode else all_features).index(st.session_state.menu)
    )
    st.session_state.menu = selected_menu
    menu = st.session_state.menu

    # 🎤 VOICE NAVIGATION OVERRIDE - ONLY WHEN VOICE COMMAND IS SPOKEN
    if "voice_nav" in st.session_state:
        # Only override if the voice navigation is different from current menu
        if st.session_state["voice_nav"] != menu:
            st.session_state.menu = st.session_state["voice_nav"]
        del st.session_state["voice_nav"]
        st.rerun()

    # Feature container with styling
    st.markdown('<div class="feature-card">', unsafe_allow_html=True)

    # Handle browser extension commands
    import urllib.parse
    query_params = st.query_params

    if 'action' in query_params:
        action = query_params['action']
        text = query_params.get('text', '')

        if action == 'speak' and text:
            st.toast(f"🔊 Reading from browser: {text[:100]}...")

            tts.speak(text)
            st.query_params.clear()
            st.rerun()

        elif action == 'summarize' and text:
            st.toast(f"📝 Summarizing text from browser...")
            summary = summarizer.summarize(text)
            st.success(f"📌 Summary: {summary}")
            tts.speak(summary)

            st.query_params.clear()
            st.rerun()
    
    # ============================================
    # NEW: VOICE SOS HANDLER
    # ============================================
    if menu == "🆘 Emergency" and st.session_state.get("voice_send_sos", False):
        speak_and_announce("Sending emergency alert")
        emergency.trigger_alert()
        speak_and_announce("Alert sent. Emergency contacts notified. Help is on the way")
        st.session_state.voice_send_sos = False
        st.rerun()
    
    # ============================================
    # NEW: VOICE ADD CONTACT HANDLER
    # ============================================
    if menu == "🆘 Emergency" and st.session_state.get("voice_add_contact_mode", False) and not st.session_state.waiting_for_contact_name:
        st.session_state.waiting_for_contact_name = True
        speak_and_announce("Please say the contact name")
        st.rerun()
    
    # ============================================
    # NEW: VOICE MULTILINGUAL HANDLER
    # ============================================
    if menu == "Multilingual":
        if st.session_state.get("voice_trigger_translate", False):
            if st.session_state.get("voice_multilingual_text"):
                translated = GoogleTranslator(source='auto', target=st.session_state.voice_lang_selection if st.session_state.voice_lang_selection else "en").translate(st.session_state.voice_multilingual_text)
                st.success(f"📖 Translation: {translated}")
                speak_and_announce(translated)
            st.session_state.voice_trigger_translate = False
        
        if st.session_state.get("voice_lang_selection"):
            lang = st.session_state.voice_lang_selection
            st.session_state.voice_lang_selection = None
            # Update the language selectbox value
            st.rerun()
    
    
    if menu == "Chatbot" and st.session_state.get("voice_clear_chat", False):
        st.session_state.chat_messages = []
        st.session_state.voice_clear_chat = False
        speak_and_announce("Chat cleared by voice command")
        st.rerun()
    
    
    if menu == "PDF Summarizer" and st.session_state.get("voice_trigger_summarize", False):
        # This will be handled in the PDF section
        pass
    
    # 🔊 TEXT → SPEECH
    if menu == "Text → Speech":
        st.markdown("## 🔊 Text to Speech")
        st.divider()

        # Voice command info
        st.info("💡 **Voice Commands:** Say 'Speak' to read the text")

        # Text input with manual option
        if st.session_state.get("voice_tts_text"):
            text = st.text_area("📝 Enter text to speak", value=st.session_state.voice_tts_text)
            st.session_state.voice_tts_text = ""
        else:
            text = st.text_area("📝 Enter text to speak")
        # Voice input button for text
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔊 Speak", use_container_width=True):
                if text.strip():
                    tts.speak(text)
                else:
                    st.warning("⚠️ Please enter text")
        with col2:
            if st.button("🎤 Voice Input", use_container_width=True):
                st.session_state.voice_text_mode = True
                st.info("🎤 Listening... Please speak your text")
                spoken_text = st.session_state.voice_assistant.voice_controller.listen(duration=5)
                if spoken_text:
                    st.session_state.tts_text = spoken_text
                    st.rerun()

        # Handle voice action
        if st.session_state.get("voice_trigger_speak", False):
            if text.strip():
                tts.speak(text)
            st.session_state.voice_trigger_speak = False


    # 🎤 SPEECH → TEXT
    elif menu == "Speech → Text":
        st.markdown("## 🎤 Speech to Text")
        st.divider()

        if st.button("🎙️ Record", use_container_width=True):
            with st.spinner("🎙️ Recording..."):
                audio = stt.record_audio()
                text = stt.transcribe(audio)

            st.success(f"📝 You said: {text}")
            if st.session_state.get("command_mode", False):
                speak_and_announce(f"You said {text}")

    # ✋ SIGN LANGUAGE
    elif menu == "Sign Language":
        st.markdown("## ✋ Sign Language Detection")
        st.divider()

        st.info("📷 This will open your camera for sign language detection")
        if st.button("🎥 Start Detection", use_container_width=True):
            import subprocess
            import sys

            # ui.py is in AccessHelp/app/, go up twice to reach AccessHelp/
            app_dir  = os.path.dirname(os.path.abspath(__file__))   # .../AccessHelp/app
            root_dir = os.path.dirname(app_dir)                      # .../AccessHelp

            script_path = os.path.join(root_dir, "src", "vision", "real_time_sign.py")

            if os.path.exists(script_path):
                # Run from root_dir so relative imports inside real_time_sign.py work
                subprocess.Popen(
                    [sys.executable, script_path],
                    cwd=root_dir
                )
            else:
                st.error(f"❌ Script not found at: {script_path}")

    # 🗣️ SPEECH → SIGN LANGUAGE ANIMATOR
    elif menu == "🗣️ Speech → Sign":
        st.markdown("## 🗣️ Speech to Sign Language")
        st.divider()

        st.info("""
        💡 **How it works:**
        - Speak or type a sentence
        - The app converts it to sign language animations
        - Whole words like *thank you*, *help*, *sorry* use their real sign
        - Unknown words are spelled letter by letter (A-Z finger spelling)
        - Use this so deaf/mute users can understand what you're saying
        """)

        # Input method tabs
        input_tab1, input_tab2 = st.tabs(["🎤 Speak", "⌨️ Type"])

        spoken_text = ""

        with input_tab1:
            st.markdown("#### 🎤 Speak a sentence")
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write("Click the button and speak clearly.")
            with col2:
                if st.button("🎙️ Record", use_container_width=True, key="sign_record"):
                    with st.spinner("🎙️ Listening for 5 seconds…"):
                        audio_path = stt.record_audio(duration=5)
                        if audio_path:
                            result = stt.transcribe(audio_path)
                            if result:
                                st.session_state.sign_input_text = result
                                st.success(f"📝 Heard: **{result}**")
                            else:
                                st.warning("⚠️ Could not understand. Try again.")
                        else:
                            st.error("❌ Microphone not available.")

        with input_tab2:
            st.markdown("#### ⌨️ Type a sentence")
            typed = st.text_area(
                "Type here",
                value=st.session_state.get("sign_input_text", ""),
                placeholder="e.g. Thank you I need help",
                key="sign_typed_input",
                height=80,
            )
            if typed:
                st.session_state.sign_input_text = typed

        # Show animation
        input_text = st.session_state.get("sign_input_text", "").strip()

        if input_text:
            st.markdown(f"**Converting:** *{input_text}*")

            col_play, col_speed, col_clear = st.columns([2, 2, 1])
            with col_play:
                play_btn = st.button("▶️ Show Signs", use_container_width=True,
                                     key="sign_play")
            with col_speed:
                speed_label = st.select_slider(
                    "⏱️ Speed",
                    options=["Slow", "Normal", "Fast"],
                    value=st.session_state.get("sign_speed", "Normal"),
                    key="sign_speed_slider",
                )
                st.session_state.sign_speed = speed_label
            with col_clear:
                if st.button("🗑️", use_container_width=True, key="sign_clear"):
                    st.session_state.sign_input_text = ""
                    st.session_state.sign_current_frame = 0
                    st.rerun()

            # Duration map
            speed_ms = {"Slow": 2500, "Normal": 1500, "Fast": 800}
            frame_ms  = speed_ms[st.session_state.get("sign_speed", "Normal")]

            # Build frames once (cache in session)
            cache_key = f"sign_frames_{input_text}"
            if cache_key not in st.session_state:
                frames = sign_animator.text_to_frames(input_text)
                st.session_state[cache_key]         = frames
                st.session_state.sign_current_frame = 0

            frames = st.session_state.get(cache_key, [])

            if not frames:
                st.warning("⚠️ No signs could be generated for this text.")
            else:
                total  = len(frames)
                idx    = st.session_state.get("sign_current_frame", 0)
                idx    = min(idx, total - 1)

                # Current frame display
                frame = frames[idx]

                # Progress bar
                st.progress((idx + 1) / total,
                            text=f"Sign {idx+1} of {total}")

                # Sign display card
                disp_col, nav_col = st.columns([3, 1])

                with disp_col:
                    st.markdown(
                        f"""
                        <div style="
                            background: rgba(102,126,234,0.08);
                            border: 2px solid rgba(102,126,234,0.3);
                            border-radius: 20px;
                            padding: 20px;
                            text-align: center;
                            min-height: 320px;
                            display: flex;
                            flex-direction: column;
                            align-items: center;
                            justify-content: center;
                        ">
                            <div style="font-size:1.1rem; color:#888; margin-bottom:8px;">
                                {'🔤 Finger Spelling' if frame.is_letter else '🤟 Word Sign'}
                            </div>
                            <div style="font-size:2.8rem; font-weight:800;
                                background:linear-gradient(135deg,#667eea,#764ba2);
                                -webkit-background-clip:text;
                                -webkit-text-fill-color:transparent;
                                margin-bottom:14px;">
                                {frame.label.upper()}
                            </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Show video (.mp4/.webm), image (.gif/.png), SVG, or placeholder
                    if frame.asset_path and frame.asset_type == "video":
                        # .mp4 or .webm — use st.video
                        st.video(frame.asset_path)
                    elif frame.asset_path and frame.asset_type == "image":
                        # .gif or .png — use st.image
                        st.image(frame.asset_path, width=260)
                    elif frame.asset_path and frame.asset_type == "svg":
                        # SVG placeholder
                        from pathlib import Path
                        svg_txt = Path(frame.asset_path).read_text(encoding="utf-8")
                        st.markdown(svg_txt, unsafe_allow_html=True)
                    else:
                        # No asset at all — styled text placeholder
                        st.markdown(
                            f"""
                            <div style="
                                width:240px; height:240px;
                                background:linear-gradient(135deg,
                                    rgba(102,126,234,0.15),
                                    rgba(118,75,162,0.15));
                                border-radius:16px;
                                display:flex; flex-direction:column;
                                align-items:center; justify-content:center;
                                margin:0 auto;
                                border: 2px dashed rgba(102,126,234,0.4);
                            ">
                                <div style="font-size:64px;">✋</div>
                                <div style="font-size:2rem; font-weight:800;
                                    color:#667eea; margin-top:8px;">
                                    {frame.label.upper()}
                                </div>
                                <div style="font-size:0.75rem; color:#aaa;
                                    margin-top:6px; text-align:center; padding:0 12px;">
                                    {'Finger spell' if frame.is_letter else 'Sign not yet added'}<br/>
                                    Place .mp4 in sign_assets/
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                    st.markdown("</div>", unsafe_allow_html=True)

                with nav_col:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    if st.button("⬅️ Prev", use_container_width=True,
                                 key="sign_prev", disabled=idx == 0):
                        st.session_state.sign_current_frame = idx - 1
                        st.rerun()
                    st.markdown(f"<div style='text-align:center;color:#888;"
                                f"font-size:0.8rem;margin:8px 0'>"
                                f"{idx+1}/{total}</div>",
                                unsafe_allow_html=True)
                    if st.button("➡️ Next", use_container_width=True,
                                 key="sign_next", disabled=idx >= total - 1):
                        st.session_state.sign_current_frame = idx + 1
                        st.rerun()

                # Word sequence overview
                st.markdown("#### 📋 Full Sequence")
                overview_cols = st.columns(min(total, 8))
                for i, f in enumerate(frames):
                    with overview_cols[i % min(total, 8)]:
                        is_current = i == idx
                        bg = "linear-gradient(135deg,#667eea,#764ba2)" \
                             if is_current else "rgba(102,126,234,0.1)"
                        color = "white" if is_current else "var(--text,#333)"
                        if st.button(
                            f.label.upper(),
                            key=f"sign_seq_{i}",
                            use_container_width=True,
                        ):
                            st.session_state.sign_current_frame = i
                            st.rerun()

                # Auto-play using st_autorefresh
                if play_btn:
                    st.session_state.sign_current_frame = 0
                    st.session_state.sign_auto_play     = True
                    st.rerun()

                if st.session_state.get("sign_auto_play", False):
                    try:
                        from streamlit_autorefresh import st_autorefresh
                        st_autorefresh(
                            interval=frame_ms,
                            limit=total + 1,
                            key="sign_autoplay_refresh",
                        )
                        if idx < total - 1:
                            st.session_state.sign_current_frame = idx + 1
                        else:
                            st.session_state.sign_auto_play = False
                            st.success("✅ Animation complete!")
                    except ImportError:
                        st.info(
                            "💡 For auto-play, install: "
                            "`pip install streamlit-autorefresh`\n"
                            "Then use ➡️ Next to advance manually."
                        )
                        st.session_state.sign_auto_play = False

                # Stop auto-play button
                if st.session_state.get("sign_auto_play", False):
                    if st.button("⏹ Stop Auto-play", key="sign_stop"):
                        st.session_state.sign_auto_play = False
                        st.rerun()

        # Available signs info
        with st.expander("📖 Available Word Signs", expanded=False):
            available = sign_animator.list_available_signs()
            if available:
                st.markdown(
                    "These words/phrases have dedicated sign animations:\n\n" +
                    "  ".join(f"`{w}`" for w in available)
                )
            else:
                st.info(
                    "No sign GIFs downloaded yet.\n\n"
                    "Run this command once to download them:\n"
                    "```\npython src/vision/download_signs.py\n```"
                )
            st.markdown("""
            **All other words are spelled letter-by-letter using A-Z finger spelling.**

            To add more word signs:
            1. Find a sign GIF on [Giphy](https://giphy.com/search/sign-language)
            2. Copy its direct URL
            3. Add it to `WORD_URLS` in `download_signs.py` and re-run it
            4. Add the word to `WORD_SIGNS` in `sign_animator.py`
            """)

    # 💬 SAVED PHRASES
    elif menu == "Saved Phrases":
        st.markdown("## 💬 Saved Phrases")
        st.divider()

        phrases_file = os.path.join(BASE_DIR, "data", "phrases.json")

        if os.path.exists(phrases_file):
            with open(phrases_file, "r") as f:
                phrases = json.load(f)
        else:
            phrases = []

        new_phrase = st.text_input("➕ Add new phrase")

        if st.button("💾 Save Phrase", use_container_width=True):
            if new_phrase:
                phrases.append(new_phrase)
                with open(phrases_file, "w") as f:
                    json.dump(phrases, f)
                st.rerun()

        for i, phrase in enumerate(phrases):
            col1, col2 = st.columns([4, 1])

            with col1:
                if st.button(f"🔊 {phrase}", key=i, use_container_width=True):
                    tts.speak(phrase)

            with col2:
                if st.button("❌", key=f"del{i}", use_container_width=True):
                    phrases.pop(i)
                    with open(phrases_file, "w") as f:
                        json.dump(phrases, f)
                    st.rerun()

    # 🌍 MULTILINGUAL
    elif menu == "Multilingual":
        st.markdown("## 🌍 Multilingual Translation")
        st.divider()

        st.info("💡 **Voice Commands:** Say 'Translate' to translate, or say language name (English, Hindi, Japanese, etc.)")

        # Text input with manual option
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.session_state.get("voice_multilingual_text"):
                text = st.text_area("📝 Enter text to translate", height=100, value=st.session_state.voice_multilingual_text)
                st.session_state.voice_multilingual_text = ""
            else:
                text = st.text_area("📝 Enter text to translate", height=100)
        with col2:
            if st.button("🎤 Speak Text", use_container_width=True):
                st.info("🎤 Listening... Please speak your text")
                spoken_text = st.session_state.voice_assistant.voice_controller.listen(duration=5)
                if spoken_text:
                    st.session_state.voice_multilingual_text = spoken_text
                    st.rerun()
        
        # Language selection with manual option
        lang = st.selectbox("🌐 Target Language", ["en", "hi", "ja", "fr", "es", "de", "zh"],
                            format_func=lambda x: {"en": "English", "hi": "Hindi", "ja": "Japanese",
                                                   "fr": "French", "es": "Spanish", "de": "German",
                                                   "zh": "Chinese"}.get(x, x))
        # Voice language selection button
        if st.button("🎤 Select Language by Voice", use_container_width=True):
            st.info("🎤 Say language name: English, Hindi, Japanese, French, Spanish, German, or Chinese")
            lang_command = st.session_state.voice_assistant.voice_controller.listen(duration=5)
            if lang_command:
                lang_map = {"english": "en", "hindi": "hi", "japanese": "ja", 
                           "french": "fr", "spanish": "es", "german": "de", "chinese": "zh"}
                for spoken, code in lang_map.items():
                    if spoken in lang_command.lower():
                        lang = code
                        st.rerun()
        
        # Translate button
        if st.button("🔄 Translate", use_container_width=True, key="translate_btn"):
            if text.strip():
                translated = GoogleTranslator(source='auto', target=lang).translate(text)
                st.success(f"📖 Translation: {translated}")
                tts.speak(translated)
            else:
                st.warning("⚠️ Please enter text to translate")
        
        # Handle voice actions
        if st.session_state.get("voice_trigger_translate", False):
            if text.strip():
                translated = GoogleTranslator(source='auto', target=lang).translate(text)
                st.success(f"📖 Translation: {translated}")
                tts.speak(translated)
            st.session_state.voice_trigger_translate = False

    # 🤖 CHATBOT - ENHANCED AI VERSION
    elif menu == "Chatbot":
        st.markdown("## 🤖 AccessHelp AI Assistant")
        st.divider()

        st.info("💡 **Voice Commands:** Say your question, or say 'Clear' to clear chat history")
        
        # Check if chatbot is available
        if chatbot is None:
            st.error("⚠️ AI Assistant is not available. Please check your installation.")
            st.info("To fix this, run: pip install transformers torch")
            st.info("The assistant will still work in basic mode with limited responses.")
        else:
            # Initialize session state for chat history
            if "chat_messages" not in st.session_state:
                st.session_state.chat_messages = []
            
            # Display chat history
            for message in st.session_state.chat_messages:
                if message["role"] == "user":
                    with st.chat_message("user"):
                        st.write(message["content"])
                else:
                    with st.chat_message("assistant"):
                        st.write(message["content"])
            
             # Chat input with manual and voice option
            col1, col2 = st.columns([5, 1])
            with col1:
                user_input = st.chat_input("💬 Type your question here...")
            with col2:
                if st.button("🎤 Speak", use_container_width=True):
                    st.info("🎤 Listening... Please speak your question")
                    spoken_question = st.session_state.voice_assistant.voice_controller.listen(duration=5)

                    if spoken_question:
                        user_input = spoken_question
                        st.rerun()
            if user_input:
                # Add user message
                with st.chat_message("user"):
                    st.write(user_input)
                st.session_state.chat_messages.append({"role": "user", "content": user_input})

                # Get bot response
                with st.spinner("🤔 Thinking..."):
                    response = chatbot.get_response(user_input)
                
                # Add assistant response
                with st.chat_message("assistant"):
                    st.write(response)
                st.session_state.chat_messages.append({"role": "assistant", "content": response})

                # Speak the response for blind users (auto-speak in command mode)
                if st.session_state.get("command_mode", False):
                    speak_and_announce(response)
                elif st.sidebar.checkbox("🔊 Auto-speak Responses", value=False):
                    tts.speak(response)
                st.rerun()

            # Clear history button with manual and voice option
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Clear Chat History", use_container_width=True):
                    st.session_state.chat_messages = []
                    st.rerun()
            with col2:
                if st.button("🎤 Voice Clear", use_container_width=True):
                    st.session_state.voice_clear_chat = True
            if st.session_state.get("voice_clear_chat", False):
                st.session_state.chat_messages = []
                st.session_state.voice_clear_chat = False
                st.success("Chat cleared by voice command!")
                st.rerun()
            # Quick action buttons (manual)
            st.markdown("### ⚡ Quick Actions")
            col1, col2, col3 = st.columns(3)
            quick_actions = [
                ("🚨 Emergency help for deaf", "Emergency help for deaf"),
                ("🔊 Text-to-speech apps", "Text-to-speech apps"),
                ("🖥️ Screen reader recommendations", "Screen reader recommendations"),
                ("💬 Communicating with deaf", "How to communicate with deaf person"),
                ("🔇 AAC devices for mute", "AAC devices for mute individuals"),
                ("👁️ Navigation for blind", "Navigation apps for blind")
            ]

            for i, (label, query) in enumerate(quick_actions[:3]):
                with col1 if i == 0 else col2 if i == 1 else col3:
                    if st.button(label, use_container_width=True):
                        with st.chat_message("user"):
                            st.write(query)
                        st.session_state.chat_messages.append({"role": "user", "content": query})
                        with st.spinner("🤔 Thinking..."):
                            response = chatbot.get_response(query)
                        with st.chat_message("assistant"):
                            st.write(response)
                        st.session_state.chat_messages.append({"role": "assistant", "content": response})
                        if st.session_state.get("command_mode", False):
                            speak_and_announce(response)
                        st.rerun()
            
            st.markdown("### 📚 More Resources")
            col1, col2, col3 = st.columns(3)

            for i, (label, query) in enumerate(quick_actions[3:]):
                with col1 if i == 0 else col2 if i == 1 else col3:
                    if st.button(label, use_container_width=True):
                        with st.chat_message("user"):
                            st.write(query)
                        st.session_state.chat_messages.append({"role": "user", "content": query})
                        with st.spinner("🤔 Thinking..."):
                            response = chatbot.get_response(query)
                        with st.chat_message("assistant"):
                            st.write(response)
                        st.session_state.chat_messages.append({"role": "assistant", "content": response})
                        if st.session_state.get("command_mode", False):
                            speak_and_announce(response)
                        st.rerun()
            
            with st.expander("ℹ️ About the AI Assistant"):
                st.markdown("""
                            **AccessHelp AI Assistant** is trained to help with:
                            - 🦻 **Deaf/Hard of Hearing**: Communication tools, emergency procedures, sign language resources
                            - 🔇 **Mute/Non-verbal**: Text-to-speech apps, AAC devices, communication strategies
                            - 👁️ **Blind/Visually Impaired**: Screen readers, navigation tools, document reading apps
                            - 🚨 **Emergency Guidance**: Specific protocols for each disability type
                            - 📚 **Resources**: Organizations, apps, and support groups

                            **Try asking about:**
                            - "How do I communicate with a deaf person?"
                            - "What are the best text-to-speech apps?"
                            - "Emergency help if I can't speak"
                            - "Screen readers for Windows"
                            """)

    # 📄 PDF
    elif menu == "PDF Summarizer":
        st.markdown("## 📄 PDF Summarizer")
        st.divider()

        st.info("💡 **Voice Commands:** Say 'Summarize' after uploading a PDF")

        file = st.file_uploader("📁 Upload PDF", type=['pdf'])

        if file:
            st.success(f"✅ File loaded: {file.name}")
            
            # Summarize button
            if st.button("📝 Summarize", use_container_width=True, key="summarize_btn"):
                with st.spinner("Reading PDF..."):
                    text = pdf_reader.extract_text(file)
                    summary = summarizer.summarize(text)
                st.success(f"📌 Summary: {summary}")

                # Also speak the summary for blind users
                tts.speak(f"Summary: {summary}")
            
            # Voice summarize trigger
            if st.session_state.get("voice_trigger_summarize", False):
                with st.spinner("Reading PDF..."):
                    text = pdf_reader.extract_text(file)
                    summary = summarizer.summarize(text)
                st.success(f"📌 Summary: {summary}")
                speak_and_announce(f"Summary: {summary}")
                st.session_state.voice_trigger_summarize = False

            # Voice upload instruction
            if st.session_state.get("voice_upload_pdf", False):
                st.info("📁 Please select a PDF file manually from the upload button above")
                st.session_state.voice_upload_pdf = False
        
        else:
            st.info("📁 Please upload a PDF file to summarize")

            if st.session_state.get("voice_trigger_summarize", False):
                st.warning("⚠️ Please upload a PDF file first using the upload button")
                st.session_state.voice_trigger_summarize = False

    # 📖 TEXT READER
    elif menu == "Text Reader":
        st.markdown("## 📖 Text Reader")
        st.divider()

        st.info("💡 **Voice Commands:** Say 'Play', 'Pause', 'Resume', or 'Stop'")

        text = st.text_area("📝 Enter text to read", key="text_reader_text")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if st.button("▶️ Play", use_container_width=True):
                tts.speak(text)

        with col2:
            st.button("⏸ Pause", use_container_width=True)
            tts.pause()

        with col3:
            if st.button("🔁 Resume", use_container_width=True):
                tts.resume()
        with col4:
            if st.button("⏹ Stop", use_container_width=True):
                tts.stop()
    
    # 🆘 EMERGENCY
    elif menu == "🆘 Emergency":
        st.markdown("## 🆘 Emergency System")
        st.divider()

        st.error("⚠️ ⚠️ ⚠️ USE ONLY IN EMERGENCY SITUATIONS ⚠️ ⚠️ ⚠️")

        tab1, tab2, tab3 = st.tabs(["🚨 Manual SOS", "📱 Fall Detection", "📞 Emergency Contacts"])
        with tab1:
            st.markdown("### 🚨 Manual Emergency SOS")
            st.info("Press this button in case of emergency")
            if st.button("🚨 SEND SOS", use_container_width=True, type="primary"):
                st.warning("🚨 Sending emergency alert...")
                emergency.trigger_alert()  # Now sends SMS with location!
                st.success("✅ Alert sent! Emergency contacts notified.")
                if st.session_state.get("command_mode", False):
                    speak_and_announce("Emergency alert sent. Help is on the way.")

                st.markdown("""
                            <div style="background: #FF5252; padding: 20px; border-radius: 10px; text-align: center; margin-top: 20px;">
                            <h3>🚨 EMERGENCY ALERT SENT 🚨</h3>
                            <p>✓ Emergency contacts notified via SMS</p>
                            <p>✓ Location shared via Google Maps</p>
                            <p>✓ Help is on the way</p>
                        </div>
                            """, unsafe_allow_html=True)
        
        # NEW: Voice SOS button in tab1
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🎤 Voice SOS", use_container_width=True):
                    st.session_state.voice_send_sos = True
                    st.rerun()
        
        with tab2:
            st.markdown("### 📱 Simulated Fall Detection")
            st.info("""
                    **Fall Detection Demo** - Simulates what would happen if a fall was detected.
                    📱 **How it works in real life:**
                    - Phone sensors detect sudden impact + orientation change
                    - System waits 10 seconds for user to cancel
                    - Auto-sends emergency alert if no response
                    - Shares GPS location with emergency contacts
                    """)
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🎯 SIMULATE FALL", use_container_width=True, type="secondary"):
                    st.session_state.fall_detected = True
                    st.session_state.fall_countdown = 10
                    st.rerun()
            with col2:
                if st.button("🔄 Reset Fall Simulation", use_container_width=True):
                    if "fall_detected" in st.session_state:
                        del st.session_state.fall_detected
                    if "fall_countdown" in st.session_state:
                        del st.session_state.fall_countdown
                    st.rerun()
            if "fall_detected" in st.session_state and st.session_state.fall_detected:
                st.markdown("""
                            <div style="background: #FF5252; padding: 20px; border-radius: 10px; text-align: center; margin: 20px 0;">
                            <h2>🚨 FALL DETECTED! 🚨</h2>
                            <p>⚠️ Sudden impact detected. Orientation change detected.</p>
                        </div>
                            """, unsafe_allow_html=True)
                countdown = st.session_state.fall_countdown
                st.markdown(f"""
                            <div style="background: #FF9800; padding: 20px; border-radius: 10px; text-align: center; margin: 10px 0;">
                            <h3>⏰ Sending alert in {countdown} seconds...</h3>
                            <p>If you are OK, click "I'M OK" to cancel.</p>
                            </div>
                            """, unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ I'M OK - Cancel Alert", use_container_width=True):
                        st.session_state.fall_detected = False
                        if "fall_countdown" in st.session_state:
                            del st.session_state.fall_countdown
                        st.success("✅ Alert cancelled. Glad you're okay!")
                        st.balloons()
                        st.rerun()
                with col2:
                    if st.button("🚨 SEND ALERT NOW", use_container_width=True):
                        st.warning("🚨 Sending emergency alert...")
                        emergency.trigger_fall_alert()  # Special fall alert
                        st.session_state.fall_detected = False
                        if "fall_countdown" in st.session_state:
                            del st.session_state.fall_countdown
                        st.success("✅ Alert sent! Help is on the way.")
                        st.markdown("""
                                    <div style="background: #4CAF50; padding: 20px; border-radius: 10px; text-align: center;">
                                    <h3>📱 EMERGENCY ALERT SENT</h3>
                                    <p>✓ Emergency contacts notified</p>
                                    <p>✓ Location shared</p>
                                    <p>✓ Emergency services alerted</p>
                                    </div>
                                    """, unsafe_allow_html=True)
                        st.rerun()
                
                # Auto-trigger after countdown
                if countdown <= 1:
                    st.warning("🚨 No response! Sending emergency alert...")
                    emergency.trigger_fall_alert()
                    st.session_state.fall_detected = False
                    if "fall_countdown" in st.session_state:
                        del st.session_state.fall_countdown
                    st.success("✅ Alert sent! Emergency services notified.")
                else:
                    # Decrement counter for next rerun
                    st.session_state.fall_countdown = countdown - 1
                    import time
                    time.sleep(1)
                    st.rerun()
            else:
                # Show fall detection explanation
                st.markdown("""
                            <div style="background: #E3F2FD; padding: 20px; border-radius: 10px; margin: 10px 0;">
                            <h4>📱 How Fall Detection Works:</h4>
                            <ul>
                                <li><strong>Detects:</strong> Sudden acceleration + orientation change</li>
                                <li><strong>Confirms:</strong> Post-fall inactivity (no movement)</li>
                                <li><strong>Alerts:</strong> Auto-texts emergency contacts with GPS location</li>
                                <li><strong>Cancels:</strong> 10-second grace period to cancel if false alarm</li>
                            </ul>
                            <p>💡 <strong>Click "SIMULATE FALL" to test the emergency flow!</strong></p>
                            </div>
                            """, unsafe_allow_html=True)
                # Quick fall statistics
                st.markdown("### 📊 Fall Risk Statistics")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Falls Risk for Blind", "+40%", "higher risk")
                with col2:
                    st.metric("Deaf Emergency Response", "Critical", "text-based alerts")
                with col3:
                    st.metric("Fall Detection Accuracy", "95%", "with modern sensors")
        
        with tab3:
            st.markdown("### 📞 Emergency Contacts Management")
            st.info("Add and manage emergency contacts for automatic SMS alerts")

            # Emergency contacts management
            contacts_file = os.path.join(BASE_DIR, "data", "emergency_contacts.json")
            if os.path.exists(contacts_file):
                with open(contacts_file, "r") as f:
                    emergency_contacts = json.load(f)
            else:
                emergency_contacts = []
            
            # Add new contact
            with st.expander("➕ Add New Emergency Contact", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    contact_name = st.text_input("Contact Name")
                with col2:
                    contact_phone = st.text_input("Phone Number (include country code, e.g., +1234567890)")
                contact_email = st.text_input("Email (optional)")

                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("💾 Save Contact", use_container_width=True):
                        if contact_name and contact_phone:
                            emergency_contacts.append({
                                "name": contact_name,
                                "phone": contact_phone,
                                "email": contact_email,
                                "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                            with open(contacts_file, "w") as f:
                                json.dump(emergency_contacts, f, indent=2)
                            st.success(f"✅ {contact_name} added to emergency contacts!")
                            st.rerun()
                        else:
                            st.warning("Please enter at least name and phone number")
                with col_b:
                    if st.button("🎤 Voice Add Contact", use_container_width=True):
                        st.session_state.voice_add_contact_mode = True
                        st.rerun()
            
            # Display existing contacts
            if emergency_contacts:
                st.markdown("### 📱 Your Emergency Contacts")
                for i, contact in enumerate(emergency_contacts):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        st.write(f"**{contact['name']}**")
                    with col2:
                        st.write(f"📞 {contact['phone']}")
                    with col3:
                        if st.button("❌", key=f"del_contact_{i}"):
                            emergency_contacts.pop(i)
                            with open(contacts_file, "w") as f:
                                json.dump(emergency_contacts, f, indent=2)
                            st.rerun()
                    if contact.get('email'):
                        st.caption(f"✉️ {contact['email']}")
                
                # Test alert button
                if st.button("📱 Test SMS Alert", use_container_width=True):
                    st.warning("📱 Sending test SMS to emergency contacts...")
                    with st.spinner("Sending test alerts..."):
                        for contact in emergency_contacts:
                            phone = contact.get('phone')
                            if phone:
                                # Use the emergency system to send test
                                emergency.test_alert()
                                st.info(f"✓ Test SMS sent to {contact['name']} ({phone})")
                    st.success("Test alerts sent! Check your phone.")
            
            # Emergency info for users
            with st.expander("ℹ️ Emergency Instructions by Disability Type"):
                st.markdown("""
                            ### 🦻 For Deaf Individuals:
                            - Use **text-to-911** if available
                            - Keep **medical ID card** with condition explained
                            - Use **video relay services** for interpreter
                            - Set up **visual alerts** (flashing lights)

                            ### 👁️ For Blind Individuals:
                            - **Call 911** immediately
                            - Clearly state: "I am blind"
                            - Use **voice assistant** to call for help
                            - Keep **emergency contacts** in voice-activated devices

                            ### 📱 SMS Alert Information:
                            When you trigger an alert, the following information is sent:
                            - Type of emergency (SOS or Fall)
                            - Timestamp
                            - Your approximate location (city/region)
                            - Google Maps link with your coordinates
                            """)

    # ⚙️ PROFILE
    elif menu == "⚙️ User Profile":
        st.markdown("## ⚙️ User Profile")
        st.divider()

        # Create tabs for different profile actions
        profile_tab1, profile_tab2, profile_tab3 = st.tabs(["👤 My Profile", "💾 Saved Phrases", "📊 Statistics"])

        with profile_tab1:
            st.markdown("### 👤 User Profile Management")

            # Username input with validation
            username = st.text_input("👤 Username",
                                     placeholder="Enter your username",
                                     help="Username must be at least 3 characters")
            if username:
                if len(username) < 3:
                    st.warning("⚠️ Username must be at least 3 characters")
                else:
                    st.session_state["username"] = username
                    user_data = profile_manager.get_user(username) or {}

                    # Profile settings
                    st.markdown("#### ⚙️ Profile Settings")
                    col1, col2 = st.columns(2)

                    with col1:
                        tts_speed = st.slider("⚡ TTS Speed", 0.5, 2.0,
                                              user_data.get("tts_speed", 1.0),
                                              0.05,
                                              help="Adjust text-to-speech speed")
                    
                    with col2:
                        font_size = st.selectbox("📏 Font Size",
                                                 ["small", "medium", "large"],
                                                 index=["small", "medium", "large"].index(
                                                     user_data.get("font_size", "medium")
                                                     ))
                    
                    # Theme preference (only light/dark now)
                    theme = st.selectbox("🎨 Default Theme",
                                         ["light", "dark"],
                                         index=["light", "dark"].index(
                                             user_data.get("theme", "light")
                                             ))
                    # Save button
                    col1, col2, col3 = st.columns([1, 1, 1])
                    with col2:
                        if st.button("💾 Save Profile", use_container_width=True, type="primary"):
                            profile_manager.create_or_update_user(
                                username,
                                {
                                    "tts_speed": tts_speed,
                                    "theme": theme,
                                    "font_size": font_size
                                }
                            )
                            st.success("✅ Profile saved successfully!")
                            st.balloons()
                            import time
                            time.sleep(1)
                            st.rerun()
                    
                    # Delete profile option
                    with st.expander("⚠️ Danger Zone"):
                        st.warning("⚠️ This action cannot be undone!")
                        if st.button("🗑️ Delete My Profile", use_container_width=True):
                            if profile_manager.delete_user(username):
                                # Clear session state
                                if "username" in st.session_state:
                                    del st.session_state["username"]
                                st.success("✅ Profile deleted successfully!")
                                st.rerun()
                            else:
                                st.error("❌ Could not delete profile")
        
        with profile_tab2:
            st.markdown("### 💬 Saved Phrases")
            st.info("Save frequently used phrases for quick access")
            if "username" not in st.session_state or not st.session_state["username"]:
                st.warning("⚠️ Please enter a username in the 'My Profile' tab first")
            else:
                username = st.session_state["username"]
                saved_phrases = profile_manager.get_phrases(username)

                # Add new phrase
                st.markdown("#### ➕ Add New Phrase")
                col1, col2 = st.columns([3, 1])
                with col1:
                    new_phrase = st.text_input("New phrase",
                                               placeholder="e.g., I need water, please",
                                               key="new_phrase_input")
                with col2:
                    if st.button("➕ Add", use_container_width=True):
                        if new_phrase and new_phrase.strip():
                            profile_manager.add_phrase(username, new_phrase.strip())
                            st.success(f"✅ Added: {new_phrase}")
                            st.rerun()
                        else:
                            st.warning("⚠️ Please enter a phrase")
                
                # Display saved phrases
                if saved_phrases:
                    st.markdown(f"#### 📝 Your Saved Phrases ({len(saved_phrases)})")
                    for i, phrase in enumerate(saved_phrases):
                        col1, col2, col3 = st.columns([4, 1, 1])
                        with col1:
                            if st.button(f"🔊 {phrase}", key=f"speak_phrase_{i}", use_container_width=True):
                                tts.speak(phrase)
                        with col2:
                            if st.button(f"📋 Copy", key=f"copy_phrase_{i}", use_container_width=True):
                                st.write(f"✅ Copied to clipboard: {phrase}")
                                # For actual clipboard, I have to do some additional setup
                        with col3:
                            if st.button(f"❌", key=f"del_phrase_{i}", use_container_width=True):
                                profile_manager.delete_phrase(username, i)
                                st.rerun()
                else:
                    st.info("💡 No saved phrases yet. Add your first phrase above!")
        
        with profile_tab3:
            st.markdown("### 📊 User Statistics")
            if "username" not in st.session_state or not st.session_state["username"]:
                st.warning("⚠️ Please enter a username in the 'My Profile' tab first")
            else:
                username = st.session_state["username"]
                stats = profile_manager.get_user_stats(username)

                if stats:
                    # Display statistics in columns
                    col1, col2, col3 = st.columns(3)
                    with col1:
                         st.metric("👤 Username", stats["username"])
                    with col2:
                        st.metric("💬 Saved Phrases", stats["saved_phrases_count"])
                    with col3:
                        st.metric("⚡ TTS Speed", f"{stats['tts_speed']}x")
                    
                    # Account info
                    st.markdown("#### 📅 Account Information")
                    if stats.get("created_at"):
                        created = datetime.fromisoformat(stats["created_at"]).strftime("%Y-%m-%d %H:%M")
                        st.info(f"📅 Account created: {created}")
                    
                    if stats.get("last_updated"):
                        updated = datetime.fromisoformat(stats["last_updated"]).strftime("%Y-%m-%d %H:%M")
                        st.info(f"🔄 Last updated: {updated}")
                    
                    # Settings summary
                    st.markdown("#### 🎨 Current Settings")
                    settings_col1, settings_col2 = st.columns(2)
                    with settings_col1:
                        st.write(f"🎨 Theme: **{stats['theme'].title()}**")
                    with settings_col2:
                        st.write(f"📏 Font Size: **{stats['font_size'].title()}**")
                
                else:
                    st.warning("⚠️ No profile data found. Please save your profile first.")
    
    # 🖐️ HAPTIC BRAILLE - With Visual Feedback for Laptops
    elif menu == "🖐️ Haptic Braille":
        st.markdown("## 🖐️ Haptic Braille Reader")
        st.divider()
        
        # Add device detection info
        st.info("""
        **📱 Device Compatibility:**
        - **Mobile/Tablet**: You'll feel actual vibrations! 📳
        - **Laptop/Desktop**: You'll hear **beep sounds** and see **visual pulses** 🔔
        
        Each beep/visual flash = Braille dot
                
        💡 **Voice Commands:** 
            - "Record speech" - Convert speech to Braille
            - "Play" - Play vibration/beep pattern
            - "Stop" - Stop playing
            - "Text" - Enter text manually
            - "Learn" - Go to Learn Braille tab
        """)
        
        # Settings for laptop users
        with st.expander("⚙️ Feedback Settings"):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔊 Enable Beep Sounds", use_container_width=True):
                    haptic.enable_beep()
                    st.success("Beep sounds enabled")
            with col2:
                if st.button("🔇 Disable Beep Sounds", use_container_width=True):
                    haptic.disable_beep()
                    st.warning("Beep sounds disabled")
        
        # Tabs for different input methods
        tab1, tab2, tab3 = st.tabs(["🎤 Speech to Braille", "📝 Text to Braille", "📖 Learn Braille"])

        # Voice command triggers for tabs
        if st.session_state.get("voice_learn_braille", False):
            st.session_state.voice_learn_braille = False
            # This will set the active tab, but we need JavaScript for that
            st.info("📖 Go to Learn Braille tab to practice")
        
        with tab1:
            st.markdown("### 🎤 Convert Speech to Haptic Feedback")
            
            if st.button("🎙️ Record Speech", use_container_width=True) or st.session_state.get("voice_trigger_speech_record", False):
                if st.session_state.get("voice_trigger_speech_record", False):
                    st.session_state.voice_trigger_speech_record = False

                with st.spinner("🎙️ Listening..."):
                    audio = stt.record_audio()
                    text = stt.transcribe(audio)
                
                if text:
                    st.success(f"📝 Recognized: {text}")
                    
                    # Show visual Braille representation
                    st.markdown("### 📖 Braille Representation")
                    st.markdown(braille_display.show_pattern(text), unsafe_allow_html=True)
                    
                    # Play haptic feedback
                    st.markdown("### 🔔 Haptic Feedback")
                    st.info("💡 **On Laptop:** You'll hear beeps | **On Mobile:** You'll feel vibrations")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("▶️ Play as Vibration/Beep", use_container_width=True) or st.session_state.get("voice_trigger_haptic", False):
                            if st.session_state.get("voice_trigger_haptic", False):
                                st.session_state.voice_trigger_haptic = False

                            with st.spinner("Playing feedback..."):
                                if haptic.play_text(text):
                                    st.success("✅ Playing... Listen for beeps or feel vibrations!")
                                    # Show visual indicator
                                    st.markdown("""
                                    <div style="background: #4CAF50; padding: 10px; border-radius: 10px; text-align: center;">
                                        🔔 Playing Braille pattern... 🔔
                                    </div>
                                    """, unsafe_allow_html=True)
                                else:
                                    st.warning("Already playing, please wait")
                    
                    with col2:
                        speed = st.slider("⚡ Reading Speed", 0.5, 2.0, 1.0, 0.1, key="speed_slider_1")
                        haptic.set_speed(speed)
                    
                    with col3:
                        if st.button("⏹️ Stop", use_container_width=True) or st.session_state.get("voice_stop_haptic", False):
                            haptic.stop()
                            st.info("Stopped")
                    
                    # Alternative: Touch-based reading (visual feedback for laptop)
                    st.markdown("### 👆 Touch to Read (Click letters)")
                    st.info("Click each character below to hear its Braille pattern")
                    
                    chars_per_row = min(len(text), 10)
                    cols = st.columns(chars_per_row)
                    for i, char in enumerate(text):
                        if i < chars_per_row:
                            col_idx = i % chars_per_row
                            with cols[col_idx]:
                                # Create a styled button for visual feedback
                                button_key = f"char_{i}_{char}"
                                if st.button(f"🔊 {char}", key=button_key, use_container_width=True):
                                    pattern = BraillePattern.get_pattern(char)
                                    letter_pattern = VibrationPattern.letter_vibration(pattern)
                                    haptic.play_pattern(letter_pattern)
                                    
                                    # Visual feedback
                                    st.markdown(f"""
                                    <div style="background: #FF9800; padding: 5px; border-radius: 5px; text-align: center;">
                                        Feeling letter: <strong>{char}</strong>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Show pattern visually
                                    pattern_text = "".join(["●" if p else "○" for p in pattern])
                                    st.caption(f"Pattern: {pattern_text}")
        
        with tab2:
            st.markdown("### 📝 Type Text for Haptic Feedback")
            # Voice input for text
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.session_state.get("voice_haptic_text"):
                    text_input = st.text_area("Enter text to convert to Braille vibrations", height=100, value=st.session_state.voice_haptic_text)
                    st.session_state.voice_haptic_text = ""
                else:
                    text_input = st.text_area("Enter text to convert to Braille vibrations", height=100)
            with col2:
                if st.button("🎤 Speak Text", use_container_width=True) or st.session_state.get("voice_text_input_mode", False):
                    if st.session_state.get("voice_text_input_mode", False):
                        st.session_state.voice_text_input_mode = False
                    st.info("🎤 Listening... Please speak your text")
                    spoken_text = st.session_state.voice_assistant.voice_controller.listen(duration=5)

                    if spoken_text:
                        st.session_state.voice_haptic_text = spoken_text
                        st.rerun()

            # Get the text input from session state if available
            if st.session_state.get("haptic_text_input"):
                text_input = st.session_state.haptic_text_input
            
            if text_input:
                # Show visual Braille
                st.markdown("### 📖 Braille Representation")
                st.markdown(braille_display.show_pattern(text_input), unsafe_allow_html=True)
                
                # Haptic controls
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔔 Play Vibration Pattern", use_container_width=True) or st.session_state.get("voice_trigger_haptic", False):
                        if st.session_state.get("voice_trigger_haptic", False):
                            st.session_state.voice_trigger_haptic = False
                            
                        if haptic.play_text(text_input):
                            st.success("Playing... Listen for beeps!")
                            # Visual feedback
                            st.markdown("""
                            <div style="background: #4CAF50; padding: 10px; border-radius: 10px; text-align: center; animation: pulse 1s;">
                                🔔 Playing Braille pattern... 🔔
                            </div>
                            <style>
                            @keyframes pulse {
                                0% { opacity: 1; }
                                50% { opacity: 0.5; }
                                100% { opacity: 1; }
                            }
                            </style>
                            """, unsafe_allow_html=True)
                        else:
                            st.warning("Already playing")
                
                with col2:
                    if st.button("⏹️ Stop", use_container_width=True) or st.session_state.get("voice_stop_haptic", False):
                        if st.session_state.get("voice_stop_haptic", False):
                            st.session_state.voice_stop_haptic = False

                        haptic.stop()
                        st.info("Stopped")
                
                # Word by word reading with visual feedback
                st.markdown("### 🔤 Read Word by Word")
                words = text_input.split()
                word_cols = st.columns(min(len(words), 5))
                
                for i, word in enumerate(words):
                    col_idx = i % 5
                    with word_cols[col_idx]:
                        if st.button(f"🔊 {word}", key=f"word_{i}", use_container_width=True):
                            haptic.play_text(word)
                            st.toast(f"Reading: {word}")
                            # Visual flash
                            st.markdown(f"""
                            <div style="background: #FFC107; padding: 5px; border-radius: 5px; text-align: center;">
                                🔔 Playing: {word}
                            </div>
                            """, unsafe_allow_html=True)
                
                # Save to saved phrases
                if st.button("💾 Save to Saved Phrases", use_container_width=True):
                    phrases_file = os.path.join(BASE_DIR, "data", "phrases.json")
                    if os.path.exists(phrases_file):
                        with open(phrases_file, "r") as f:
                            phrases = json.load(f)
                    else:
                        phrases = []
                    phrases.append(f"[HAPTIC] {text_input}")
                    with open(phrases_file, "w") as f:
                        json.dump(phrases, f)
                    st.success("Saved! Find it in Saved Phrases")
        
        with tab3:
            st.markdown("### 📖 Learn Braille Through Touch")
            
            st.markdown("""
            **Braille Alphabet Reference:**
            
            Each letter is represented by 6 dots in a 3x2 grid:
            - Dots 1,2,3 in left column
            - Dots 4,5,6 in right column
            - **Beep/Vibration = Dot present**
            - **Silence/Pause = No dot**
            """)
            
            # Interactive Braille learning
            letters = list("abcdefghijklmnopqrstuvwxyz")
            
            st.markdown("### Practice Letters")
            letter_cols = st.columns(8)
            
            for i, letter in enumerate(letters):
                col_idx = i % 8
                with letter_cols[col_idx]:
                    if st.button(letter.upper(), key=f"learn_{letter}"):
                        pattern = BraillePattern.get_pattern(letter)
                        letter_pattern = VibrationPattern.letter_vibration(pattern)
                        haptic.play_pattern(letter_pattern)
                        
                        # Show pattern visually
                        pattern_text = "".join(["●" if p else "○" for p in pattern])
                        st.caption(f"Pattern: {pattern_text}")
                        st.toast(f"Feeling letter: {letter} (beeps = dots)")
                        
                        # Play beep for demonstration
                        st.markdown(f"""
                        <div style="background: #E91E63; padding: 5px; border-radius: 5px; text-align: center;">
                            🔔 Playing Braille for <strong>{letter}</strong>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.markdown("### Practice Common Words")
            common_words = ["hello", "help", "yes", "no", "thank", "emergency", "water", "food"]
            
            word_cols = st.columns(4)
            for i, word in enumerate(common_words):
                col_idx = i % 4
                with word_cols[col_idx]:
                    if st.button(f"🔊 {word}", key=f"word_learn_{word}"):
                        haptic.play_text(word)
                        st.toast(f"Reading: {word}")
        
        # Settings
        with st.expander("⚙️ Haptic Settings"):
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🔔 Enable Beep Sounds", use_container_width=True):
                    haptic.enable_beep()
                    st.success("Beep sounds enabled")
            
            with col2:
                if st.button("🔕 Disable Beep Sounds", use_container_width=True):
                    haptic.disable_beep()
                    st.warning("Beep sounds disabled")
            
            st.markdown("**Reading Speed:**")
            speed = st.slider("Adjust reading speed", 0.5, 2.0, 1.0, 0.05, key="settings_speed")
            haptic.set_speed(speed)
            
            st.markdown("**Test Feedback:**")
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🎵 Test Beep Pattern", use_container_width=True):
                    # Play a test pattern
                    test_pattern = VibrationPattern.start_pattern() + [(0.05, 0.05), (0.05, 0.05), (0.05, 0)]
                    haptic.play_pattern(test_pattern)
                    st.toast("Test beep pattern sent! Listen for beeps")
                    st.markdown("""
                    <div style="background: #2196F3; padding: 10px; border-radius: 10px; text-align: center;">
                        🔔 Beep pattern: short-short-short (start) → long pause
                    </div>
                    """, unsafe_allow_html=True)
            
            with col_b:
                if st.button("🔊 Test Braille 'A'", use_container_width=True):
                    pattern = BraillePattern.get_pattern('a')
                    letter_pattern = VibrationPattern.letter_vibration(pattern)
                    haptic.play_pattern(letter_pattern)
                    st.toast("Feeling letter: A (dot 1 only)")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # 🌟 GLOBAL VOICE COMMAND HANDLER (inside menus)
    # Process voice actions for current menu
    if st.session_state.get("voice_action"):
        action = st.session_state.voice_action
        process_voice_action(action, menu)
        st.session_state.voice_action = None
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 🎤 VOICE CONTROL SECTION (Enhanced)
    st.sidebar.markdown("---")
    st.sidebar.markdown("## 🎤 Voice Control")
    
    # NEW: Command mode toggle in sidebar
    command_mode_toggle = st.sidebar.checkbox(
        "🎙️ Command Mode (Hands-Free)",
        value=st.session_state.get("command_mode", False),
        help="Enable for blind users - everything can be controlled by voice"
    )
    
    if command_mode_toggle != st.session_state.get("command_mode", False):
        st.session_state.command_mode = command_mode_toggle
        if command_mode_toggle:
            speak_and_announce("Command mode activated via sidebar")
        else:
            speak_and_announce("Command mode deactivated")
        st.rerun()
    
    # Wake word toggle
    wake_word_enabled = st.sidebar.checkbox(
        "🔊 Wake Word (\"Hey Access\")",
        value=st.session_state.get("wake_word_enabled", False),
        help="Say 'Hey Access' to activate, then speak your command"
    )
    
    if wake_word_enabled != st.session_state.get("wake_word_enabled", False):
        st.session_state.wake_word_enabled = wake_word_enabled
        
        if wake_word_enabled:
            # Start wake word detection
            if not st.session_state.wake_word_detector:
                from src.voice.wake_word import WakeWordDetector
                
                def on_wake_word(command=""):
                    st.session_state.voice_assistant.activate()
                    st.session_state.voice_listen_trigger = True
                    tts.speak("Yes")
                    st.rerun()
                
                st.session_state.wake_word_detector = WakeWordDetector()
                st.session_state.wake_word_detector.start_listening(on_wake_word)
                st.sidebar.success("✅ Wake word active - Say 'Hey Access'")
        else:
            if st.session_state.wake_word_detector:
                st.session_state.wake_word_detector.stop_listening()
                st.session_state.wake_word_detector = None
    
    # Voice command button
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("🎤 Click to Speak", use_container_width=True, type="primary"):
            st.session_state.voice_assistant.activate()
            st.session_state.voice_listen_trigger = True
            st.rerun()
    
    with col2:
        if st.button("🔇 Cancel", use_container_width=True):
            st.session_state.voice_assistant.deactivate()
            if "voice_listen_trigger" in st.session_state:
                del st.session_state.voice_listen_trigger
    
    # Voice status indicator
    if st.session_state.voice_assistant.is_active:
        st.sidebar.info("🎤 Listening... Speak your command")
        
        if st.session_state.get("voice_listen_trigger", False) and not st.session_state.get("voice_command_listening", False):
            st.session_state.voice_listen_trigger = False
            
            voice_placeholder = st.sidebar.empty()
            voice_placeholder.info("🎙️ Speak now...")
            
            command = st.session_state.voice_assistant.voice_controller.listen(duration=5)
            
            if command:
                voice_placeholder.success(f"📢 '{command}'")
                
                # Check for command mode activation first
                command_lower = command.lower()
                if "command mode" in command_lower or "command mode initiated" in command_lower:
                    st.session_state.command_mode = True
                    speak_and_announce("Command mode activated. You can now control everything with your voice.")
                    st.rerun()
                elif "exit command mode" in command_lower or "disable command mode" in command_lower:
                    st.session_state.command_mode = False
                    speak_and_announce("Command mode deactivated.")
                    st.rerun()
                elif st.session_state.get("command_mode", False):
                    # In command mode, process navigation
                    feature = interpret_command(command)
                    if feature:
                        voice_placeholder.success(f"✅ Opening {feature}")
                        speak_and_announce(f"Opening {feature}")
                        st.session_state["voice_nav"] = feature
                        st.rerun()
                    else:
                        # Check for menu-specific actions
                        action = interpret_action_command(command, menu)
                        if action:
                            voice_placeholder.success(f"✅ Action: {action}")
                            st.session_state["voice_action"] = action
                            st.rerun()
                        else:
                            voice_placeholder.error(f"❌ Command not recognized")
                            speak_and_announce("Command not recognized")
                else:
                    # Not in command mode, just show the command
                    voice_placeholder.info(f"Command heard: {command}")
            else:
                voice_placeholder.warning("⚠️ No command detected")
            
            st.session_state.voice_assistant.deactivate()
    
    # Voice help section
    with st.sidebar.expander("💡 Voice Commands Help", expanded=False):
        st.markdown("""
        **How to use Command Mode:**
        1. Say **"Command Mode"** or enable in sidebar
        2. Once activated, you can say:
        
        **Navigation:**
        - "Open chatbot"
        - "Open emergency"
        - "Open multilingual"
        - "Open pdf summarizer"
        - "Open text to speech"
        - "Open speech to text"
        - "Open haptic braille"
        - "Open speech to sign"
        
        **In Emergency:**
        - "Send SOS"
        - "Add contact" (then follow voice prompts)
        
        **In Chatbot:**
        - Just ask your question!
        - "Clear chat"
        
        **In Multilingual:**
        - Speak your text, then say language name, then "translate"
        
        **Exit Command Mode:**
        - "Exit command mode"
        """)
    
    # 🎧 Audio feedback
    if st.sidebar.checkbox("🔊 Voice Feedback", value=True):
        if menu != st.session_state.get("last_menu", ""):
            st.session_state.last_menu = menu
            if not st.session_state.get("command_mode", False):
                tts.speak(f"Opened {menu}")

    
    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; font-size: 0.8em;'>🌸 Made with ❤️ for Accessibility | Empowering Everyone 🌸</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    run_app()