# src/haptic/haptic_feedback.py
#
# PLATFORM DETECTION & VIBRATION STRATEGY
# ─────────────────────────────────────────────────────────────────────────────
#
# This file supports THREE platforms automatically:
#
#   1. LAPTOP / DESKTOP
#      → Plays beep sounds via winsound (Windows) or system bell (Mac/Linux)
#      → Visual pulse animation shown on screen
#      → Used for: sighted developers, deaf-blind users on desktop
#
#   2. MOBILE BROWSER (phone opening the Streamlit app in Chrome/Safari)
#      → Uses the Web Vibration API via JavaScript injected into the page
#      → st.components.v1.html() sends vibration commands to the browser
#      → Supported on: Android Chrome, Firefox Mobile
#      → NOT supported on: iPhone Safari (Apple blocks Web Vibration API)
#      → Used for: deaf-blind users feeling Braille patterns as vibrations
#
#   3. FUTURE: NATIVE MOBILE APP (React Native / Flutter)
#      → See the commented section at the bottom of this file
#      → Would use the device's native vibration motor directly
#      → Supports complex patterns, intensity control, haptic feedback
#
# HOW MOBILE VIBRATION WORKS (Web Vibration API):
#   navigator.vibrate([200, 100, 200])
#   → vibrate 200ms, pause 100ms, vibrate 200ms
#   Each Braille dot = short vibration pulse
#   Each "no dot" = silence (pause only)
#   Letter boundary = longer pause
#   Word boundary = distinct double-pulse
#
# ─────────────────────────────────────────────────────────────────────────────

import time
import threading
import platform as _platform
import streamlit as st
import streamlit.components.v1 as components


# ═════════════════════════════════════════════════════════════════════════════
# BRAILLE PATTERNS
# ═════════════════════════════════════════════════════════════════════════════

class BraillePattern:
    """
    Standard Grade-1 Braille dot patterns.
    Each letter is a list of 6 values (0 or 1) representing dots:
        [dot1, dot2, dot3, dot4, dot5, dot6]
    Physical layout on a Braille cell:
        dot1  dot4
        dot2  dot5
        dot3  dot6
    """

    patterns = {
        'a': [1, 0, 0, 0, 0, 0],
        'b': [1, 1, 0, 0, 0, 0],
        'c': [1, 0, 0, 1, 0, 0],
        'd': [1, 0, 0, 1, 1, 0],
        'e': [1, 0, 0, 0, 1, 0],
        'f': [1, 1, 0, 1, 0, 0],
        'g': [1, 1, 0, 1, 1, 0],
        'h': [1, 1, 0, 0, 1, 0],
        'i': [0, 1, 0, 1, 0, 0],
        'j': [0, 1, 0, 1, 1, 0],
        'k': [1, 0, 1, 0, 0, 0],
        'l': [1, 1, 1, 0, 0, 0],
        'm': [1, 0, 1, 1, 0, 0],
        'n': [1, 0, 1, 1, 1, 0],
        'o': [1, 0, 1, 0, 1, 0],
        'p': [1, 1, 1, 1, 0, 0],
        'q': [1, 1, 1, 1, 1, 0],
        'r': [1, 1, 1, 0, 1, 0],
        's': [0, 1, 1, 1, 0, 0],
        't': [0, 1, 1, 1, 1, 0],
        'u': [1, 0, 1, 0, 0, 1],
        'v': [1, 1, 1, 0, 0, 1],
        'w': [0, 1, 0, 1, 1, 1],
        'x': [1, 0, 1, 1, 0, 1],
        'y': [1, 0, 1, 1, 1, 1],
        'z': [1, 0, 1, 0, 1, 1],
        ' ': [0, 0, 0, 0, 0, 0],
        '.': [0, 0, 1, 0, 0, 1],
        ',': [0, 1, 0, 0, 0, 0],
        '?': [0, 1, 1, 0, 0, 1],
        '!': [0, 1, 1, 0, 1, 0],
        '0': [0, 1, 0, 1, 1, 1],
        '1': [1, 0, 0, 0, 0, 0],
        '2': [1, 1, 0, 0, 0, 0],
        '3': [1, 0, 0, 1, 0, 0],
        '4': [1, 0, 0, 1, 1, 0],
        '5': [1, 0, 0, 0, 1, 0],
        '6': [1, 1, 0, 1, 0, 0],
        '7': [1, 1, 0, 1, 1, 0],
        '8': [1, 1, 0, 0, 1, 0],
        '9': [0, 1, 0, 1, 0, 0],
    }

    @classmethod
    def get_pattern(cls, char: str) -> list:
        """Return the 6-dot Braille pattern for a character."""
        return cls.patterns.get(char.lower(), cls.patterns[' '])


# ═════════════════════════════════════════════════════════════════════════════
# VIBRATION PATTERNS
# ═════════════════════════════════════════════════════════════════════════════

class VibrationPattern:
    """
    Converts Braille dot patterns into timed vibration sequences.

    Format used throughout this class:
        List of (vibrate_ms, pause_ms) tuples
        vibrate_ms = 0 means silence for that slot (dot is 0)
    """

    # Timings (milliseconds) — tweak these if vibration feels too fast/slow
    DOT_VIBRATE_MS    = 60    # duration of one Braille dot vibration
    DOT_PAUSE_MS      = 30    # gap between dots within a letter
    LETTER_PAUSE_MS   = 120   # gap between letters
    WORD_PAUSE_MS     = 300   # gap between words
    SENTENCE_PAUSE_MS = 500   # gap after sentence-ending punctuation

    @staticmethod
    def letter_vibration(dot_pattern: list) -> list:
        """
        Turn a 6-dot Braille pattern into a (vibrate_ms, pause_ms) sequence.
        dot present  → short vibration + pause
        dot absent   → silence + pause
        """
        sequence = []
        for dot in dot_pattern:
            if dot:
                sequence.append((VibrationPattern.DOT_VIBRATE_MS,
                                  VibrationPattern.DOT_PAUSE_MS))
            else:
                sequence.append((0, VibrationPattern.DOT_PAUSE_MS))
        # Inter-letter gap (extra pause after all 6 dots)
        sequence.append((0, VibrationPattern.LETTER_PAUSE_MS))
        return sequence

    @staticmethod
    def word_separator() -> list:
        """Distinct double-pulse to mark a word boundary."""
        return [
            (80, 60),
            (80, VibrationPattern.WORD_PAUSE_MS),
        ]

    @staticmethod
    def sentence_end() -> list:
        """Long single pulse to mark end of sentence."""
        return [(200, VibrationPattern.SENTENCE_PAUSE_MS)]

    @staticmethod
    def start_pattern() -> list:
        """Two quick pulses played before text begins — signals 'reading starts'."""
        return [(60, 60), (60, 120)]

    @staticmethod
    def error_pattern() -> list:
        """Three rapid pulses — signals an error or unrecognised character."""
        return [(80, 40), (80, 40), (80, 0)]


# ═════════════════════════════════════════════════════════════════════════════
# PLATFORM DETECTION
# ═════════════════════════════════════════════════════════════════════════════

def _is_windows() -> bool:
    return _platform.system() == "Windows"


def _sequence_to_js_array(sequence: list) -> str:
    """
    Convert a (vibrate_ms, pause_ms) sequence into the flat integer array
    expected by the Web Vibration API:
        navigator.vibrate([v1, p1, v2, p2, ...])
    Zeros in the vibrate slot are kept as 1ms (minimum) because the API
    needs alternating on/off values — a 0ms "on" would collapse the pattern.
    Silent dots are represented by a very short pulse (1ms) which the phone
    motor cannot produce, effectively acting as silence.
    """
    flat = []
    for vib_ms, pause_ms in sequence:
        flat.append(max(1, vib_ms))   # vibration duration (≥1 to keep alternating)
        flat.append(pause_ms)         # pause duration
    # Remove trailing pause if present
    if flat and flat[-1] == 0:
        flat.pop()
    return str(flat)


# ═════════════════════════════════════════════════════════════════════════════
# HAPTIC FEEDBACK — MAIN CLASS
# ═════════════════════════════════════════════════════════════════════════════

class HapticFeedback:
    """
    Cross-platform haptic/beep feedback for the AccessHelp Braille reader.

    On laptop  → winsound beeps (Windows) or system bell (Mac/Linux)
    On mobile browser → Web Vibration API via injected JavaScript
    """

    def __init__(self):
        self.vibration_enabled = True
        self.beep_enabled      = True
        self.speed             = 1.0      # 0.5 (slow) to 2.0 (fast)
        self.is_playing        = False

        # Auto-detect: if running on Windows we can use winsound
        self._windows = _is_windows()

        print("✅ HapticFeedback initialised")
        print("💡 Laptop: beep sounds | Mobile browser: phone vibration")
        print("🎵 Each pulse/beep = one Braille dot")

    # ── BEEP (laptop) ─────────────────────────────────────────────────────────

    def _beep(self, duration_ms: int, frequency: int = 1000):
        """Play a beep on the laptop speaker."""
        if not self.beep_enabled:
            return
        try:
            if self._windows:
                import winsound
                winsound.Beep(frequency, duration_ms)
            else:
                # Mac / Linux: print ASCII bell character
                print('\a', end='', flush=True)
                time.sleep(duration_ms / 1000)
        except Exception as e:
            print(f"Beep error: {e}")

    # ── MOBILE VIBRATION (browser) ────────────────────────────────────────────

    def _vibrate_mobile(self, sequence: list):
        """
        Inject JavaScript into the Streamlit page to trigger the phone's
        vibration motor using the Web Vibration API.

        IMPORTANT: This only works when the user opens the app in a
        mobile browser (Android Chrome / Firefox Mobile).
        iPhone Safari does NOT support navigator.vibrate() — Apple blocks it.

        The injected script:
          1. Checks if navigator.vibrate is available
          2. Calls navigator.vibrate([v1, p1, v2, p2, ...])
          3. Shows a small on-screen indicator so the user knows it fired
        """
        js_array = _sequence_to_js_array(sequence)

        js_code = f"""
        <script>
        (function() {{
            // Check Web Vibration API support
            if (!navigator.vibrate) {{
                // Show a warning if vibration is not supported (e.g. iPhone)
                var msg = document.getElementById('vib-status');
                if (msg) {{
                    msg.innerText = '⚠️ Vibration not supported on this browser/device.';
                    msg.style.color = 'orange';
                }}
                console.warn('Web Vibration API not supported.');
                return;
            }}

            // Fire the vibration pattern
            var pattern = {js_array};
            navigator.vibrate(pattern);

            // Visual confirmation pulse (for deafblind users who may not
            // always feel the first vibration clearly)
            var indicator = document.getElementById('vib-status');
            if (indicator) {{
                indicator.innerText = '📳 Vibrating...';
                indicator.style.color = 'green';
                setTimeout(function() {{
                    indicator.innerText = '✅ Pattern complete';
                }}, {sum(v + p for v, p in sequence)});
            }}
        }})();
        </script>
        <div id="vib-status" style="
            font-size: 14px;
            padding: 6px 12px;
            background: #e8f5e9;
            border-radius: 8px;
            display: inline-block;
            margin-top: 6px;">
            📳 Sending vibration to phone...
        </div>
        """

        # height=60 keeps the injected element small but visible
        components.html(js_code, height=60)

    # ── SINGLE VIBRATE/BEEP ────────────────────────────────────────────────────

    def vibrate(self, duration_ms: int):
        """
        Single pulse — plays a beep on laptop OR vibrates the phone.
        Frequency varies with duration to make patterns more distinguishable.
        """
        if not self.vibration_enabled:
            return

        if duration_ms <= 0:
            return

        # Laptop beep
        freq = 1000 if duration_ms <= 60 else (800 if duration_ms <= 120 else 600)
        self._beep(duration_ms, freq)

        # Mobile vibration (single pulse: [duration_ms])
        self._vibrate_mobile([(duration_ms, 0)])

    # ── PATTERN PLAYBACK ──────────────────────────────────────────────────────

    def play_pattern(self, sequence: list):
        """
        Play a full (vibrate_ms, pause_ms) sequence.

        On laptop  : plays each beep with time.sleep() between them
        On mobile  : sends the whole sequence to the JS API in one call
                     (more efficient and avoids multiple script injections)
        """
        if not self.vibration_enabled:
            return

        # ── Mobile: send entire sequence to browser in one JS call ────────────
        # Filter to only slots with actual vibration (non-zero vib_ms)
        has_vibration = any(v > 0 for v, _ in sequence)
        if has_vibration:
            self._vibrate_mobile(sequence)

        # ── Laptop: play beeps sequentially ───────────────────────────────────
        for vib_ms, pause_ms in sequence:
            if vib_ms > 0:
                freq = 1000 if vib_ms <= 60 else (800 if vib_ms <= 120 else 600)
                self._beep(vib_ms, freq)
            if pause_ms > 0:
                time.sleep((pause_ms / 1000) * (1 / self.speed))

    # ── TEXT PLAYBACK ─────────────────────────────────────────────────────────

    def text_to_sequence(self, text: str) -> list:
        """Convert a text string into a full vibration/beep sequence."""
        sequence = list(VibrationPattern.start_pattern())

        words = text.split()
        for w_idx, word in enumerate(words):
            for char in word:
                if char.isalnum() or char in '.,?!':
                    dot_pattern   = BraillePattern.get_pattern(char)
                    letter_seq    = VibrationPattern.letter_vibration(dot_pattern)
                    sequence.extend(letter_seq)

            # Word separator between words (not after the last word)
            if w_idx < len(words) - 1:
                sequence.extend(VibrationPattern.word_separator())

        sequence.extend(VibrationPattern.sentence_end())
        return sequence

    def play_text(self, text: str, on_complete=None) -> bool:
        """
        Play text as a Braille vibration/beep sequence in a background thread.
        Returns False immediately if already playing.
        """
        if self.is_playing:
            return False

        self.is_playing = True

        # For mobile: send the whole sequence JS call immediately
        # (components.html must be called from the main Streamlit thread)
        sequence = self.text_to_sequence(text)
        has_vibration = any(v > 0 for v, _ in sequence)
        if has_vibration:
            self._vibrate_mobile(sequence)

        # Laptop beep playback runs in a thread so the UI stays responsive
        def _play_beeps():
            try:
                for vib_ms, pause_ms in sequence:
                    if not self.is_playing:
                        break
                    if vib_ms > 0:
                        freq = 1000 if vib_ms <= 60 else (800 if vib_ms <= 120 else 600)
                        self._beep(vib_ms, freq)
                    if pause_ms > 0:
                        time.sleep((pause_ms / 1000) * (1 / self.speed))
                if on_complete:
                    on_complete()
            finally:
                self.is_playing = False

        threading.Thread(target=_play_beeps, daemon=True).start()
        return True

    # ── CONTROLS ──────────────────────────────────────────────────────────────

    def stop(self):
        self.is_playing = False

    def set_speed(self, speed: float):
        """Set playback speed multiplier (0.5 = slow, 2.0 = fast)."""
        self.speed = max(0.5, min(2.0, speed))

    def enable(self):
        self.vibration_enabled = True

    def disable(self):
        self.vibration_enabled = False
        self.stop()

    def enable_beep(self):
        self.beep_enabled = True
        print("🔊 Beep sounds enabled")

    def disable_beep(self):
        self.beep_enabled = False
        print("🔇 Beep sounds disabled")


# ═════════════════════════════════════════════════════════════════════════════
# BRAILLE DISPLAY EMULATOR  (visual HTML widget shown in the Streamlit UI)
# ═════════════════════════════════════════════════════════════════════════════

class BrailleDisplayEmulator:
    """Renders a visual HTML Braille cell grid for each character in a string."""

    def show_pattern(self, text: str) -> str:
        html = """
        <div style="background:#f0f0f0; padding:20px; border-radius:10px; margin:10px 0;">
            <h4>📖 Braille Display</h4>
            <div style="display:flex; flex-wrap:wrap; gap:16px; font-family:monospace;">
        """
        for char in text:
            pattern = BraillePattern.get_pattern(char)
            dots = ["●" if d else "○" for d in pattern]
            html += f"""
            <div style="text-align:center;">
                <div style="display:grid; grid-template-columns:repeat(2,20px);
                            gap:4px; font-size:20px;">
                    <div>{dots[0]}</div><div>{dots[3]}</div>
                    <div>{dots[1]}</div><div>{dots[4]}</div>
                    <div>{dots[2]}</div><div>{dots[5]}</div>
                </div>
                <div style="font-size:11px; margin-top:4px;">{char}</div>
            </div>
            """
        html += "</div></div>"
        return html


# ═════════════════════════════════════════════════════════════════════════════
# ▼▼▼  FUTURE: NATIVE MOBILE APP IMPLEMENTATION  ▼▼▼
# ═════════════════════════════════════════════════════════════════════════════
#
# When you are ready to build a dedicated mobile app (React Native or Flutter),
# replace the Web Vibration API approach with the native code below.
# The Python logic (BraillePattern, VibrationPattern) stays exactly the same —
# only the "output layer" changes.
#
# ─────────────────────────────────────────────────────────────────────────────
# OPTION A: REACT NATIVE  (JavaScript / TypeScript)
# ─────────────────────────────────────────────────────────────────────────────
#
# Install:  npm install react-native-haptic-feedback
#           npm install @react-native-community/async-storage
#
# // BrailleHaptic.js
# import ReactNativeHapticFeedback from 'react-native-haptic-feedback';
# import { Vibration } from 'react-native';
#
# // Single dot pulse
# export function vibrateDot() {
#   Vibration.vibrate(60);           // 60ms pulse = one Braille dot
# }
#
# // Play a full (vibrate_ms, pause_ms) sequence
# // sequence: array of [vibrateMs, pauseMs] pairs
# export async function playSequence(sequence) {
#   for (const [vibrateMs, pauseMs] of sequence) {
#     if (vibrateMs > 0) {
#       Vibration.vibrate(vibrateMs);
#     }
#     // Wait for vibrate + pause before next pulse
#     await new Promise(r => setTimeout(r, vibrateMs + pauseMs));
#   }
# }
#
# // Convert text to Braille vibration sequence and play it
# // (Mirror the Python BraillePattern + VibrationPattern logic here)
# export async function playText(text) {
#   const sequence = textToSequence(text);  // implement same logic as Python
#   await playSequence(sequence);
# }
#
# // Advanced haptic (uses haptic engine, not just motor — iPhone XR+)
# export function hapticImpact(style = 'medium') {
#   // style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'
#   ReactNativeHapticFeedback.trigger(`impact${style.charAt(0).toUpperCase() + style.slice(1)}`);
# }
#
# ─────────────────────────────────────────────────────────────────────────────
# OPTION B: FLUTTER  (Dart)
# ─────────────────────────────────────────────────────────────────────────────
#
# In pubspec.yaml add:
#   dependencies:
#     vibration: ^1.8.4         # cross-platform vibration with pattern support
#     flutter_haptic: ^1.0.0    # haptic engine for iPhone
#
# // braille_haptic.dart
# import 'package:vibration/vibration.dart';
#
# class BrailleHaptic {
#
#   // Check if device supports vibration
#   static Future<bool> hasVibrator() async {
#     return await Vibration.hasVibrator() ?? false;
#   }
#
#   // Play a single dot pulse
#   static Future<void> vibrateDot() async {
#     Vibration.vibrate(duration: 60);   // 60ms = one Braille dot
#     await Future.delayed(Duration(milliseconds: 90));  // 60ms vib + 30ms pause
#   }
#
#   // Play a full pattern: List of [vibrateMs, pauseMs] pairs
#   // Vibration package accepts flat [on, off, on, off] list directly:
#   static Future<void> playSequence(List<List<int>> sequence) async {
#     // Flatten to [v1, p1, v2, p2, ...]
#     List<int> flat = [];
#     List<int> amps = [];    // 0 = no vibration, 255 = full strength
#     for (var pair in sequence) {
#       flat.add(pair[0] > 0 ? pair[0] : 1);   // vibration duration
#       flat.add(pair[1]);                       // pause duration
#       amps.add(pair[0] > 0 ? 255 : 0);        // amplitude
#       amps.add(0);                             // no vibration during pause
#     }
#     // vibrate() with pattern plays the whole sequence at once (most efficient)
#     Vibration.vibrate(pattern: flat, intensities: amps);
#   }
#
#   // Convert text → Braille sequence → play
#   // (Reuse the same dot patterns from the Python BraillePattern dict above)
#   static Future<void> playText(String text) async {
#     List<List<int>> sequence = _textToSequence(text);
#     await playSequence(sequence);
#   }
#
#   // NOTE: Implement _textToSequence() in Dart by porting
#   //       BraillePattern + VibrationPattern from this Python file.
#   //       The timing constants (DOT_VIBRATE_MS etc.) are the same.
# }
#
# ─────────────────────────────────────────────────────────────────────────────
# IPHONE NOTE (both React Native and Flutter):
#   iPhone XR and later have a Taptic Engine — use haptic feedback APIs
#   (UIImpactFeedbackGenerator) for richer tactile patterns.
#   Older iPhones only support simple on/off vibration.
#   React Native: ReactNativeHapticFeedback.trigger('impactMedium')
#   Flutter:      HapticFeedback.mediumImpact()
# ─────────────────────────────────────────────────────────────────────────────