"""
Screen Reader and Magnification Module
Provides screen reading, zoom, and high contrast modes
"""

import os
import sys
import threading
import pyautogui
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import tkinter as tk
from tkinter import ttk
import queue
import time
import pyperclip
import cv2
import pytesseract

# Add root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from src.text.tts import TextToSpeech

if sys.platform == "win32":
    # Common Tesseract installation paths
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    for path in possible_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            print(f"✅ Found Tesseract at: {path}")
            break

class ScreenReader:
    """Screen reader with magnification and reading capabilities"""
    
    def __init__(self):
        self.tts = TextToSpeech()
        self.magnification_active = False
        self.reading_active = False
        self.high_contrast_active = False
        self.zoom_level = 2.0
        self.magnifier_window = None
        self.read_queue = queue.Queue()
        
    def read_screen_text(self, region=None):
        """
        Read text from screen using OCR
        
        Args:
            region: Tuple (x, y, width, height) or None for full screen
        """
        if region:
            screenshot = pyautogui.screenshot(region=region)
        else:
            screenshot = pyautogui.screenshot()
        
        # Convert to numpy array for OCR
        import cv2
        import pytesseract
        
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        
        # Extract text
        text = pytesseract.image_to_string(img)
        
        if text.strip():
            self.tts.speak(text)
            return text
        else:
            self.tts.speak("No text detected on screen")
            return ""
    
    def read_selected_text(self):
        """Read text currently selected by user"""
        try:
            # Get selected text (platform-specific)
            if sys.platform == "darwin":  # macOS
                import subprocess
                result = subprocess.run(['osascript', '-e', 'tell application "System Events" to keystroke "c" using command down'], 
                                      capture_output=True)
                import time
                time.sleep(0.1)
                selected_text = pyperclip.paste()
            elif sys.platform == "win32":  # Windows
                import pyperclip
                import ctypes
                ctypes.windll.user32.keybd_event(0x11, 0, 0, 0)  # Ctrl down
                ctypes.windll.user32.keybd_event(0x43, 0, 0, 0)  # C down
                ctypes.windll.user32.keybd_event(0x43, 0, 2, 0)  # C up
                ctypes.windll.user32.keybd_event(0x11, 0, 2, 0)  # Ctrl up
                time.sleep(0.1)
                selected_text = pyperclip.paste()
            else:  # Linux
                import pyperclip
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.1)
                selected_text = pyperclip.paste()
            
            if selected_text:
                self.tts.speak(selected_text)
                return selected_text
            else:
                self.tts.speak("No text selected")
                return ""
        except Exception as e:
            print(f"Error reading selected text: {e}")
            return ""
    
    def start_magnifier(self, zoom=2.0):
        """
        Start screen magnifier in a background thread.

        BUG FIXES
        ---------
        1. The original file had TWO definitions of start_magnifier —
           a broken stub inside the class and a correct one outside it.
           The stub shadowed the correct version and called a non-existent
           _magnifier_loop method, raising AttributeError immediately.
           Both are replaced here with a single correct implementation.
        2. _magnifier_loop is no longer needed — the loop runs inline
           inside run_magnifier() which is cleaner and avoids the missing
           method crash.
        """
        if self.magnifier_window:
            self.stop_magnifier()

        self.zoom_level = zoom
        self.magnification_active = True

        def run_magnifier():
            try:
                import tkinter as tk
                from tkinter import ttk
                from PIL import ImageTk

                root = tk.Tk()
                root.title("Screen Magnifier — AccessHelp")
                root.attributes("-topmost", True)
                root.geometry("400x400+100+100")

                def on_closing():
                    self.magnification_active = False
                    root.destroy()

                root.protocol("WM_DELETE_WINDOW", on_closing)

                canvas = tk.Canvas(root, width=400, height=400)
                canvas.pack()

                control_frame = ttk.Frame(root)
                control_frame.pack(pady=5)

                ttk.Label(control_frame, text="Zoom:").pack(side=tk.LEFT)
                zoom_var = tk.DoubleVar(value=self.zoom_level)
                zoom_scale = ttk.Scale(
                    control_frame, from_=1.0, to=5.0,
                    variable=zoom_var, orient=tk.HORIZONTAL, length=150,
                )
                zoom_scale.pack(side=tk.LEFT, padx=5)
                zoom_scale.configure(command=lambda _: setattr(self, "zoom_level", zoom_var.get()))

                ttk.Button(control_frame, text="Stop", command=on_closing).pack(
                    side=tk.LEFT, padx=5
                )

                def update_magnifier():
                    if not self.magnification_active:
                        return
                    try:
                        x, y        = pyautogui.position()
                        size        = 200
                        left        = max(0, x - size // 2)
                        top         = max(0, y - size // 2)
                        screenshot  = pyautogui.screenshot(region=(left, top, size, size))
                        new_size    = (int(size * self.zoom_level), int(size * self.zoom_level))
                        magnified   = screenshot.resize(new_size, Image.Resampling.LANCZOS)
                        photo       = ImageTk.PhotoImage(magnified)
                        canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                        canvas.image = photo  # keep reference to avoid GC
                    except Exception as e:
                        print(f"Magnifier update error: {e}")
                    if self.magnification_active:
                        root.after(50, update_magnifier)

                update_magnifier()
                self.magnifier_window = root
                root.mainloop()

            except Exception as e:
                print(f"Magnifier error: {e}")
                self.magnification_active = False

        self.magnifier_thread = threading.Thread(target=run_magnifier, daemon=True)
        self.magnifier_thread.start()

    def stop_magnifier(self):
        """Stop screen magnifier."""
        self.magnification_active = False
        if self.magnifier_window:
            self.magnifier_window.quit()
            self.magnifier_window = None
    
    def enable_high_contrast(self):
        """Enable high contrast mode for better visibility"""
        self.high_contrast_active = True
        
        if sys.platform == "win32":
            # Windows high contrast
            import ctypes
            SPI_SETHIGHCONTRAST = 0x0043
            HC_HOTKEYS = 0x0001
            class HIGHCONTRAST(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint),
                           ("dwFlags", ctypes.c_uint),
                           ("lpszDefaultScheme", ctypes.c_wchar_p)]
            
            hc = HIGHCONTRAST()
            hc.cbSize = ctypes.sizeof(hc)
            hc.dwFlags = HC_HOTKEYS
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETHIGHCONTRAST, hc.cbSize, ctypes.byref(hc), 0)
            
        elif sys.platform == "darwin":
            # macOS - use accessibility settings
            os.system("defaults write com.apple.universalaccess reduceTransparency -bool true")
            os.system("defaults write com.apple.universalaccess increaseContrast -bool true")
            
        self.tts.speak("High contrast mode enabled")
    
    def disable_high_contrast(self):
        """Disable high contrast mode"""
        self.high_contrast_active = False
        
        if sys.platform == "win32":
            import ctypes
            SPI_SETHIGHCONTRAST = 0x0043
            HC_HOTKEYS = 0x0001
            class HIGHCONTRAST(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint),
                           ("dwFlags", ctypes.c_uint),
                           ("lpszDefaultScheme", ctypes.c_wchar_p)]
            
            hc = HIGHCONTRAST()
            hc.cbSize = ctypes.sizeof(hc)
            hc.dwFlags = 0
            ctypes.windll.user32.SystemParametersInfoW(SPI_SETHIGHCONTRAST, hc.cbSize, ctypes.byref(hc), 0)
            
        self.tts.speak("High contrast mode disabled")
    
    def continuous_reading(self, interval=5):
        """Continuously read screen changes"""
        self.reading_active = True
        last_text = ""
        
        def read_loop():
            while self.reading_active:
                current_text = self.read_screen_text()
                if current_text and current_text != last_text:
                    last_text = current_text
                time.sleep(interval)
        
        self.reading_thread = threading.Thread(target=read_loop, daemon=True)
        self.reading_thread.start()

# Initialize screen reader
screen_reader = ScreenReader()