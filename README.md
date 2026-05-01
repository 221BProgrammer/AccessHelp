# 🌸 AccessHelp — AI-Powered Accessibility Assistant

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32%2B-red?logo=streamlit)
![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10%2B-green?logo=google)
![License](https://img.shields.io/badge/License-MIT-yellow)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange)

**Empowering Everyone, Everywhere**

*An open-source AI platform designed to bridge communication gaps for people who are deaf, blind, or mute — combining speech recognition, sign language detection, text-to-speech, haptic Braille, and emergency alerting in one unified application.*

</div>

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Who This Helps](#-who-this-helps)
- [Features](#-features)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [How to Run](#-how-to-run)
- [Sign Language Model Training](#-sign-language-model-training)
- [Voice Control](#-voice-control)
- [Emergency System](#-emergency-system)
- [Limitations](#-known-limitations)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🧭 Overview

**AccessHelp** is a multi-modal accessibility assistant built with Python and Streamlit. It uses computer vision, natural language processing, speech recognition, and machine learning to help people with disabilities communicate, navigate information, and stay safe in emergencies.

The application was built with three primary user groups in mind:

| User Group | Core Barrier | How AccessHelp Helps |
|---|---|---|
| **Blind / Visually Impaired** | Cannot read screens or navigate visually | Voice control, text-to-speech, haptic Braille |
| **Deaf / Hard of Hearing** | Cannot hear speech or audio alerts | Speech-to-sign animation, visual captions, SMS + call emergency alerts |
| **Mute / Non-verbal** | Cannot speak to communicate | Sign language detection → sentence formation, text-to-speech output |

---

## 👥 Who This Helps

### 👁️ Blind / Visually Impaired Users
- **Fully hands-free**: Say *"Hey Access"* or *"Command Mode"* — the entire app is controllable by voice
- **Text-to-speech**: Any text, PDF, or chatbot response is read aloud automatically
- **Haptic Braille**: Text is converted to vibration patterns — real phone vibration on Android, beep sounds on laptop
- **PDF summarisation**: Upload a PDF and hear a spoken summary without reading

### 🦻 Deaf / Hard of Hearing Users
- **Speech to Sign Language**: When someone speaks near the microphone, their words are automatically converted to sign language animations frame by frame
- **Real-time captions**: Speech is transcribed to text in real time
- **Emergency SMS with live GPS**: SOS button sends your exact Google Maps location to all saved contacts via SMS, and calls their phone so it rings
- **Visual emergency alerts**: All emergency events are shown visually on screen

### 🔇 Mute / Non-verbal Users
- **Sign language detection**: Show ASL signs to the camera — letters and words are detected in real time and formed into sentences with NLP autocomplete
- **Finger spelling with autocomplete**: Sign letters one by one; the app suggests word completions, handles proper names gracefully, and builds grammatically structured sentences
- **Saved phrases**: Pre-save frequently used phrases and play them as speech with one tap
- **AAC-style communication**: Type or sign → speak via text-to-speech

---

## ✨ Features

### 🔊 Text → Speech
Convert any typed text to natural-sounding speech using Google TTS. Supports multiple languages including English, Hindi, Japanese, French, Spanish, German, and Chinese. Includes play, pause, resume, and stop controls.

### 🎤 Speech → Text
Real-time speech transcription powered by OpenAI Whisper with Google Speech Recognition fallback. Works offline after initial model download.

### ✋ Sign Language Detection (Camera → Text → Sentence)
- Trained on the ASL Alphabet Kaggle dataset (87,000+ images) plus word-level sign datasets
- Detects **A-Z letters**, **0-9 numbers**, and **whole-word signs** (hello, help, sorry, thank you, etc.)
- Letter-by-letter word building with NLP autocomplete powered by NLTK's 236,000-word English dictionary
- Intelligent name detection: proper nouns and names disable autocomplete so users can spell freely
- Sentence spoken aloud on demand

### 🗣️ Speech → Sign Language Animation
When someone speaks to a deaf user, the app:
1. Transcribes speech in real time
2. Identifies known word signs (hello, sorry, help, thank you, etc.)
3. Falls back to A-Z finger spelling for unknown words
4. Plays sign animations frame by frame with speed control and prev/next navigation
5. Shows the full sign sequence overview so the deaf user can follow along

### 🌍 Multilingual Translation
Translate text between 7 languages with automatic TTS playback of the translation result.

### 🤖 AI Chatbot (AccessHelp AI)
Accessibility-focused conversational AI powered by **Ollama (local LLM)** — runs completely offline with no API key. Uses `llama3` by default. Answers questions about:
- Assistive technology recommendations
- Emergency procedures by disability type
- Communication strategies for each disability
- Screen reader setup, AAC devices, navigation apps

Falls back to a curated smart response system when Ollama is not available.

### 📄 PDF Summariser
Upload any PDF → extracted text is summarised using Facebook's BART-large-CNN model → summary is read aloud. Handles password-protected and image-only PDFs with clear error messages.

### 🖐️ Haptic Braille
Converts text to Braille vibration patterns:
- **Android Chrome/Firefox**: Real phone motor vibration via the Web Vibration API
- **iPhone**: Apple blocks the Web Vibration API — beep sounds used instead
- **Laptop/Desktop**: Beep tones via system audio
- Interactive A-Z learning: click any letter to feel its Braille dot pattern
- Word-by-word playback at adjustable speed

### 🆘 Emergency System
- **Manual SOS**: One button sends GPS-located SMS to all emergency contacts + makes a Twilio alarm call to their phones
- **Fall Detection Simulation**: 10-second countdown with auto-send if no cancellation — simulates what an accelerometer-based system would trigger
- **Emergency Contacts Manager**: Add, remove, and test contacts (requires country code e.g. +91)
- **Live GPS Location**: Every alert includes a Google Maps link with exact coordinates
- **Disability-specific guidance**: On-screen emergency instructions tailored to deaf, blind, and mute users

### ⚙️ User Profile
Save per-user preferences: TTS speed, theme, font size. Manage saved phrases per user. Profile data stored locally as JSON.

### 💬 Saved Phrases
Pre-save frequently needed sentences for instant one-tap speech playback. Useful for non-verbal users communicating common needs.

### 📖 Text Reader
Paste any text and listen to it with full playback controls.

### 🎨 Themes
- **Light Mode**: Soft gradient background with sakura petal falling animation
- **Dark Mode**: Dark interface with autumn leaves blowing in the wind animation

---

## 🏗️ Architecture

```
AccessHelp/
│
├── app/
│   ├── main.py                        ← FastAPI backend (REST + WebSocket API)
│   └── ui.py                          ← Streamlit frontend, all features
│
├── assets/
│   └── images/
│       ├── dark-bg.jpg                ← Dark mode background
│       └── light-bg.jpg               ← Light mode background
│
├── data/                              ← Runtime data (gitignored)
│   ├── alphabets/                     ← Extracted alphabet landmark data
│   ├── signs/                         ← Extracted word sign landmark data
│   ├── alphabets.json                 ← Alphabet metadata
│   └── phrases.json                   ← Saved user phrases
│
├── datasets/                          ← Training datasets (gitignored, 1GB+)
│   ├── asl_alphabet_train/
│   └── wlasl_words/
│
├── src/
│   ├── browser/
│   │   └── extension_api.py           ← Flask REST API for Chrome extension [currently unused]
│   │
│   ├── chatbot/
│   │   └── bot.py                     ← Ollama LLM + smart fallback responses
│   │
│   ├── emergency/
│   │   └── alert.py                   ← Twilio SMS + voice call + GPS location
│   │
│   ├── extension/                     ← Chrome extension files [currently unused]
│   │   ├── background.js
│   │   ├── content.js
│   │   ├── manifest.json
│   │   ├── popup.html
│   │   └── style.css
│   │
│   ├── haptic/
│   │   └── haptic_feedback.py         ← Braille → vibration/beep patterns
│   │
│   ├── mute/
│   │   └── phrases.py                 ← Saved phrases manager for mute users
│   │
│   ├── speech/
│   │   └── stt.py                     ← Whisper + SpeechRecognition
│   │
│   ├── text/
│   │   ├── pdf_reader.py              ← PyPDF2 text extraction
│   │   ├── summarizer.py              ← BART-large-CNN summarisation
│   │   └── tts.py                     ← Google TTS + pygame playback
│   │
│   ├── user/
│   │   └── profile_manager.py         ← Atomic JSON profile storage
│   │
│   ├── utils/
│   │   └── error_handler.py           ← Global error handling + logging
│   │
│   ├── vision/
│   │   ├── dataset_from_images.py     ← Extract landmarks from Kaggle datasets
│   │   ├── download_signs.py          ← Sign asset checker + placeholder generator
│   │   ├── hand_tracker.py            ← MediaPipe hands (2-hand support)
│   │   ├── landmarks_utils.py         ← Landmark normalisation + aggregation
│   │   ├── ocr_enhanced.py            ← EasyOCR + Tesseract multi-language OCR
│   │   ├── real_time_sign.py          ← Live sign detection + sentence builder
│   │   ├── screen_reader.py           ← Screen magnifier + screen reader
│   │   ├── sentence_processor.py      ← LetterBuffer + NLP autocomplete
│   │   ├── sign_animator.py           ← Speech → sign animation engine
│   │   ├── train.py                   ← RandomForest training
│   │   └── wlasl_extract.py           ← WLASL video → frame extractor
│   │
│   └── voice/
│       ├── voice_assistant.py         ← Session manager
│       ├── voice_controller.py        ← Command dispatcher + navigation parser
│       └── wake_word.py               ← "Hey Access" background detector
│
├── sign_model.pkl                     ← Trained model (gitignored, ~95MB)
├── README.md
└── .gitignore
```

---

## 💻 Installation

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | 3.11 recommended |
| RAM | 8 GB minimum | 16 GB recommended (for LLM) |
| OS | Windows 10+, macOS, Ubuntu | All supported |
| Webcam | Any USB/built-in | For sign language detection |
| Microphone | Any | For voice control and STT |

### System Dependencies

**Tesseract OCR** (for OCR feature):
```bash
# Windows: Download installer from https://github.com/UB-Mannheim/tesseract/wiki
# macOS:   brew install tesseract
# Linux:   sudo apt-get install tesseract-ocr
```

**Ollama** (for AI chatbot):
```bash
# Download from https://ollama.com and install
# Then pull the model:
ollama pull llama3
```

### Python Setup

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/AccessHelp.git
cd AccessHelp

# 2. Create virtual environment
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download NLTK data (one time)
python -c "import nltk; nltk.download('words'); nltk.download('wordnet')"
```

### Environment Variables (for Emergency SMS feature)

Create a `.env` file in the project root or set these before running:

```bash
# Get these from https://www.twilio.com (free trial available)
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token_here"
export TWILIO_PHONE_NUMBER="+1xxxxxxxxxx"

# Optional — for email alerts
export SENDER_EMAIL="your@gmail.com"
export SENDER_PASSWORD="your_app_password"
```

---

## 🚀 How to Run

```bash
# Activate virtual environment first
# Windows:  venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# Run the app
streamlit run main.py
```

Open your browser at `http://localhost:8501`

---

## 🤖 Sign Language Model Training

The sign language detection model must be trained before use. Two approaches:

### Approach 1 — Kaggle Dataset (Recommended, ~95% accuracy)

```bash
# Step 1: Download datasets
# Alphabet + Numbers (A-Z, 0-9):
#   https://www.kaggle.com/datasets/grassknoted/asl-alphabet
# Word Signs (WLASL):
#   https://www.kaggle.com/datasets/risangbaskoro/wlasl-processed

# Step 2: Place unzipped folders in datasets/ (in project root)
# AccessHelp/datasets/asl_alphabet_train/A/, B/, ..., 0/, ..., 9/
# AccessHelp/datasets/wlasl_words/hello/, help/, sorry/, ...

# Step 3: Extract landmarks from alphabet + numbers dataset
python src/vision/dataset_from_images.py \
    --data-dir datasets/asl_alphabet_train \
    --output-dir data/signs \
    --max-per-class 500

# Step 4: Extract landmarks from word signs dataset
python src/vision/dataset_from_images.py \
    --data-dir datasets/wlasl_words \
    --output-dir data/signs \
    --max-per-class 300

# Step 5: Train the model (uses all CPU cores)
python src/vision/train.py

# Step 6: Test live detection
python src/vision/real_time_sign.py
```

### Approach 2 — Manual Collection (~75-85% accuracy)

```bash
# Record 50 samples per letter/word yourself
python src/vision/dataset.py

# Then train
python src/vision/train.py
```

### Sign Animation Assets

The Speech-to-Sign feature needs sign video/GIF files:

```bash
# Check what's missing and create placeholders
python src/vision/download_signs.py

# Download A-Z alphabet signs manually from:
#   https://www.handspeak.com/learn/index.php?id=asl-alphabet
# Save as: a.mp4, b.mp4 ... z.mp4
# Place in: src/vision/sign_assets/

# Download word signs from:
#   https://www.handspeak.com/word/
# Save as: hello.mp4, help.mp4, thankyou.mp4 etc.
# Place in: src/vision/sign_assets/
```

---

## 🎤 Voice Control (To be worked on later)

AccessHelp supports fully hands-free operation for blind users:

### Wake Word
Say **"Hey Access"** at any time to activate voice control (no clicking needed).

### Command Mode
Say **"Command Mode"** to enable persistent voice control where every utterance is treated as a command.

### Navigation Commands
```
"Open chatbot"           → navigates to AI chatbot
"Open emergency"         → navigates to emergency panel
"Open multilingual"      → navigates to translation
"Open text to speech"    → navigates to TTS
"Open speech to sign"    → navigates to sign animator
"Open haptic braille"    → navigates to Braille
```

### In-Feature Commands
```
"Send SOS"              → triggers emergency alert
"Add contact"           → voice-guided contact addition
"Translate"             → translates current text
"Summarize"             → summarises loaded PDF
"Clear chat"            → clears chatbot history
"Play"                  → plays Braille pattern
```

### Exit Command Mode
```
"Exit command mode"
```

---

## 🆘 Emergency System

When SOS is triggered, the system:

1. **Gets your live GPS coordinates** via IP geolocation or device GPS
2. **Sends SMS** to all saved emergency contacts with:
   - Alert type (SOS or Fall Detected)
   - Timestamp
   - Google Maps link with exact coordinates
   - Area name (city, region)
3. **Calls their phone** via Twilio — when they answer they hear a spoken alert message
4. **Opens Google Maps** in your browser showing your location
5. **Logs the event** to `data/emergency_log.txt`

Phone numbers must include country code (e.g. `+91` for India, `+1` for USA).

---

## ⚠️ Known Limitations

### Sign Language Detection
- Trained on **ASL (American Sign Language)** — may not be accurate for ISL (Indian Sign Language) or BSL (British Sign Language) without retraining on appropriate datasets
- Accuracy drops in **low lighting conditions** or when the hand is partially out of frame
- Similar-looking signs (M/N, U/V, S/A) may be confused — collect more training data for these specific pairs
- **Two-handed signs** that require both hands to move simultaneously are not fully supported; currently both hands' landmarks are detected but the model was trained on single-hand datasets

### Speech to Sign Animation
- **Not all English words have dedicated sign animations**. Words like *grandmother*, *grandfather*, *engineer*, *electricity*, *beautiful*, *comfortable*, *government*, *university*, and thousands of others do not have sign GIFs/videos in the current asset set. For these words, the app falls back to **letter-by-letter finger spelling**
- Adding sign animations for new words requires manually downloading a GIF/MP4 from a sign language resource (e.g. handspeak.com), naming it correctly, placing it in `src/vision/sign_assets/`, and adding it to `WORD_SIGNS` in `sign_animator.py`
- Sign animations are sourced manually — there is no automated download for correct, verified sign videos due to the absence of a reliable free API with stable URLs
- **iPhone users**: The Web Vibration API is blocked by Apple on all iOS browsers. Haptic Braille vibration does not work on iPhone — beep sounds are used instead

### Voice Control
- Streamlit's architecture requires a page rerun to process voice commands. There is a **0.5–1 second delay** between speaking and the app responding. For truly real-time voice control, the React + FastAPI migration (code included) removes this constraint
- Wake word detection requires `streamlit-autorefresh` to be installed for the page to auto-rerun when the wake word is detected
- Voice control feature is not activated now. This feature will be worked on later.

### AI Chatbot
- Requires **Ollama** to be installed and running locally. Without it, the app uses a curated keyword-based fallback which covers common accessibility questions but is not conversational
- First response after starting Ollama may take **10-30 seconds** as the model loads into memory

### OCR
- Scanned image PDFs cannot be read by PyPDF2 — use the OCR Scanner feature instead
- OCR accuracy depends heavily on image quality and font clarity

### Emergency System
- Requires a **Twilio account** (free trial available). Without Twilio, no SMS or calls are sent
- TextBelt (the free fallback) does not work for Indian phone numbers
- GPS accuracy depends on the device: IP-based location is accurate to city level only (~5-10 km radius). A device GPS gives metre-level accuracy

### Platform
- Haptic vibration feedback on the laptop uses beep sounds — actual motor vibration requires a mobile device
- Screen magnifier and screen reader features require a desktop environment (not available in headless server deployments)

---

## 🗂️ Project Structure Summary

```
AccessHelp/
├── main.py                         ← App entry point
├── ui.py                           ← Complete Streamlit UI
├── requirements.txt                ← Python dependencies
├── .gitignore                      ← Git ignore rules
├── README.md                       ← This file
│
├── src/
│   ├── chatbot/bot.py              ← Ollama AI + fallback
│   ├── emergency/alert.py          ← Twilio SMS/call + GPS
│   ├── haptic/haptic_feedback.py   ← Braille vibration/beep
│   ├── speech/stt.py               ← Whisper transcription
│   ├── text/
│   │   ├── tts.py                  ← Google TTS
│   │   ├── pdf_reader.py           ← PDF extraction
│   │   └── summarizer.py           ← BART summarisation
│   ├── user/profile_manager.py     ← User profiles
│   ├── vision/
│   │   ├── hand_tracker.py         ← MediaPipe hand detection
│   │   ├── landmarks_utils.py      ← Feature engineering
│   │   ├── dataset_from_images.py  ← Dataset landmark extraction
│   │   ├── dataset.py              ← Manual data collection
│   │   ├── train.py                ← Model training
│   │   ├── real_time_sign.py       ← Live detection
│   │   ├── sentence_processor.py  ← Word building + NLP
│   │   ├── sign_animator.py        ← Speech → sign frames
│   │   └── download_signs.py       ← Asset checker
│   └── voice/
│       ├── voice_controller.py     ← Command parsing
│       ├── voice_assistant.py      ← Session management
│       └── wake_word.py            ← "Hey Access" detector
│
├── assets/images/                  ← Background images
├── data/                           ← Runtime JSON data (gitignored)
├── datasets/                       ← Training datasets (gitignored)
└── logs/                           ← Error logs (gitignored)
```

---

## 🤝 Contributing

Contributions are welcome, especially in these areas:

1. **More sign language GIFs/MP4s** — adding animations for common words
2. **ISL / BSL support** — training data for Indian or British Sign Language
3. **Mobile app** — React Native or Flutter implementation using the FastAPI backend
4. **Better word-sign dataset** — higher quality WLASL training pipeline
5. **Improved name detection** — multilingual proper noun recognition

To contribute:
```bash
git fork https://github.com/YOUR_USERNAME/AccessHelp
git checkout -b feature/your-feature-name
# make changes
git commit -m "Add: description of change"
git push origin feature/your-feature-name
# Open a Pull Request
```


## 🙏 Acknowledgements

- [OpenAI Whisper](https://github.com/openai/whisper) — speech transcription
- [MediaPipe](https://mediapipe.dev) — hand landmark detection
- [Ollama](https://ollama.com) — local LLM inference
- [Kaggle ASL Alphabet Dataset](https://www.kaggle.com/datasets/grassknoted/asl-alphabet) — sign language training data
- [WLASL Dataset](https://github.com/dxli94/WLASL) — word-level ASL data
- [HandSpeak](https://www.handspeak.com) — sign language reference and animations
- [Twilio](https://twilio.com) — SMS and voice call emergency alerts
- [Facebook BART](https://huggingface.co/facebook/bart-large-cnn) — text summarisation

---

<div align="center">

**🌸 Made with ❤️ for Accessibility — Empowering Everyone, Everywhere 🌸**

*If this project helped you or someone you care about, please consider giving it a ⭐ on GitHub.*

</div>
