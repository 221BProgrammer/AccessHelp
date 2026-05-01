"""
Browser Extension API for AccessHelp
Provides backend services for Chrome/Firefox extension
"""

import json
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import webbrowser
from datetime import datetime

# Add root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.text.tts import TextToSpeech
from src.text.summarizer import TextSummarizer
from src.chatbot.bot import AccessibilityChatbot

class BrowserExtensionAPI:
    """REST API for browser extension"""
    
    def __init__(self, port=5000):
        self.app = Flask(__name__)
        CORS(self.app)  # Enable CORS for extension
        
        self.tts = TextToSpeech()
        self.summarizer = TextSummarizer()
        self.chatbot = None
        
        # Initialize chatbot if available
        try:
            self.chatbot = AccessibilityChatbot()
            print("✅ Chatbot initialized for extension")
        except:
            print("⚠️ Chatbot not available")
        
        self.setup_routes()
        self.port = port
    
    def setup_routes(self):
        """Setup API routes"""
        
        @self.app.route('/api/speak', methods=['POST'])
        def speak():
            """Speak text from webpage"""
            data = request.json
            text = data.get('text', '')
            if text:
                self.tts.speak(text)
                return jsonify({'status': 'success', 'message': 'Speaking text'})
            return jsonify({'status': 'error', 'message': 'No text provided'})
        
        @self.app.route('/api/summarize', methods=['POST'])
        def summarize():
            """Summarize webpage content"""
            data = request.json
            text = data.get('text', '')
            if text:
                summary = self.summarizer.summarize(text)
                return jsonify({'status': 'success', 'summary': summary})
            return jsonify({'status': 'error', 'message': 'No text provided'})
        
        @self.app.route('/api/translate', methods=['POST'])
        def translate():
            """Translate webpage content"""
            data = request.json
            text = data.get('text', '')
            target_lang = data.get('target_lang', 'en')
            
            if text:
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source='auto', target=target_lang)
                translated = translator.translate(text)
                return jsonify({'status': 'success', 'translated': translated})
            return jsonify({'status': 'error', 'message': 'No text provided'})
        
        @self.app.route('/api/chat', methods=['POST'])
        def chat():
            """Chat with AI about webpage"""
            data = request.json
            question = data.get('question', '')
            context = data.get('context', '')
            
            if self.chatbot and question:
                full_question = f"Context from webpage: {context}\n\nQuestion: {question}"
                response = self.chatbot.get_response(full_question)
                return jsonify({'status': 'success', 'response': response})
            return jsonify({'status': 'error', 'message': 'Chatbot not available'})
        
        @self.app.route('/api/highlight', methods=['POST'])
        def highlight():
            """Highlight text on webpage"""
            data = request.json
            text = data.get('text', '')
            # This will be handled by the extension
            return jsonify({'status': 'success', 'message': 'Highlighting text'})
        
        @self.app.route('/api/read-aloud', methods=['POST'])
        def read_aloud():
            """Read selected text aloud"""
            data = request.json
            text = data.get('text', '')
            if text:
                self.tts.speak(text)
                return jsonify({'status': 'success'})
            return jsonify({'status': 'error'})
        
        @self.app.route('/api/status', methods=['GET'])
        def status():
            """Check if API is running"""
            return jsonify({
                'status': 'online',
                'version': '1.0',
                'features': ['tts', 'summarizer', 'translate', 'chatbot'],
                'timestamp': datetime.now().isoformat()
            })
    
    def start(self):
        """Start the Flask server"""
        print(f"🌐 Browser Extension API starting on http://localhost:{self.port}")
        print("📱 Install Chrome/Firefox extension to connect")
        
        # Open browser with instructions
        webbrowser.open(f"http://localhost:{self.port}")
        
        self.app.run(host='localhost', port=self.port, debug=False, threaded=True)

# Initialize API
extension_api = BrowserExtensionAPI()

def start_extension_api():
    """Start API in separate thread"""
    api_thread = threading.Thread(target=extension_api.start, daemon=True)
    api_thread.start()
    return api_thread