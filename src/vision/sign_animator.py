# src/vision/sign_animator.py
"""
Speech-to-Sign Language Animator
==================================
Converts spoken/typed text into a sequence of sign language
animations to display in the UI.

SUPPORTED ASSET FORMATS (checked in this priority order)
---------------------------------------------------------
  .mp4   — video (you collected alphabet as .mp4)
  .gif   — animated image
  .webm  — web video
  .png   — still image
  .jpg   — still image
  .svg   — SVG placeholder (auto-generated when real asset missing)

ASSET FOLDER
------------
All sign files live in:
    src/vision/sign_assets/

Alphabet naming  :  a.mp4, b.mp4 ... z.mp4  (or .gif etc.)
Word sign naming :  hello.mp4, help.mp4, thankyou.mp4 ...

ADDING MORE SIGNS
-----------------
1. Download a sign video/GIF from https://www.handspeak.com/word/
2. Rename it to the word name (e.g. morning.mp4)
3. Drop it in src/vision/sign_assets/
4. Add the word to WORD_SIGNS below if not already there
"""

from __future__ import annotations
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# ── Asset directory ───────────────────────────────────────────────────────────
_HERE     = Path(__file__).resolve().parent
ASSET_DIR = _HERE / "sign_assets"
ASSET_DIR.mkdir(exist_ok=True)

# ── Format priority ───────────────────────────────────────────────────────────
# .mp4 is checked first because that is what you collected for the alphabet.
ACCEPTED_EXTENSIONS = [".mp4", ".gif", ".webm", ".png", ".jpg", ".jpeg", ".svg"]

# ── Word → base filename mapping ──────────────────────────────────────────────
# Keys   : lowercase words / phrases (spaces → underscore for lookup)
# Values : base filename WITHOUT extension (extension is auto-detected)
WORD_SIGNS: dict[str, str] = {
    # ── Common words ──────────────────────────────────────────────────────────
    "hello":        "hello",
    "hi":           "hello",
    "goodbye":      "goodbye",
    "bye":          "goodbye",
    "yes":          "yes",
    "no":           "no",
    "please":       "please",
    "sorry":        "sorry",
    "thank":        "thankyou",
    "thankyou":     "thankyou",
    "thank_you":    "thankyou",
    "thanks":       "thankyou",
    "help":         "help",
    "emergency":    "emergency",
    "danger":       "danger",
    "stop":         "stop",
    "wait":         "wait",
    "good":         "good",
    "bad":          "bad",
    "love":         "love",
    "iloveyou":     "iloveyou",
    "i_love_you":   "iloveyou",
    "water":        "water",
    "food":         "food",
    "eat":          "eat",
    "drink":        "drink",
    "bathroom":     "bathroom",
    "toilet":       "bathroom",
    "home":         "home",
    "school":       "school",
    "work":         "work",
    "hospital":     "hospital",
    "doctor":       "doctor",
    "police":       "police",
    "pain":         "pain",
    "sick":         "sick",
    "tired":        "tired",
    "happy":        "happy",
    "sad":          "sad",
    "angry":        "angry",
    "scared":       "scared",
    "hot":          "hot",
    "cold":         "cold",
    "more":         "more",
    "finished":     "finished",
    "done":         "finished",
    "want":         "want",
    "need":         "need",
    "have":         "have",
    "know":         "know",
    "understand":   "understand",
    "name":         "name",
    "where":        "where",
    "what":         "what",
    "when":         "when",
    "why":          "why",
    "how":          "how",
    "who":          "who",
    "come":         "come",
    "go":           "go",
    "again":        "again",
    "call":         "call",
    "hear":         "hear",
    "see":          "see",
    "speak":        "speak",
    "talk":         "speak",
    "write":        "write",
    "read":         "read",
    "learn":        "learn",
    "remember":     "remember",
    "forget":       "forget",
    "think":        "think",
    "feel":         "feel",
    "mother":       "mother",
    "father":       "father",
    "family":       "family",
    "friend":       "friend",
    "baby":         "baby",
    "man":          "man",
    "woman":        "woman",
    "boy":          "boy",
    "girl":         "girl",
    "money":        "money",
    "time":         "time",
    "today":        "today",
    "tomorrow":     "tomorrow",
    "yesterday":    "yesterday",
    "morning":      "morning",
    "night":        "night",
    # ── Pronouns ──────────────────────────────────────────────────────────────
    "i":            "i",
    "me":           "i",
    "you":          "you",
    "he":           "he",
    "she":          "she",
    "we":           "we",
    "they":         "they",
    "my":           "my",
    "your":         "your",
}

# ── Multi-word phrases checked BEFORE splitting into individual words ──────────
PHRASE_SIGNS: dict[str, str] = {
    "thank you":            "thankyou",
    "i love you":           "iloveyou",
    "how are you":          "howareyou",
    "good morning":         "goodmorning",
    "good night":           "goodnight",
    "good afternoon":       "goodafternoon",
    "i need help":          "ineedhelp",
    "nice to meet you":     "nicetomeetyou",
    "excuse me":            "excuseme",
    "i am sorry":           "sorry",
    "call the police":      "callpolice",
    "call a doctor":        "calldoctor",
    "what is your name":    "whatisyourname",
    "my name is":           "mynameis",
}


# ── Data class: one animation step ───────────────────────────────────────────
@dataclass
class SignFrame:
    label:       str             # word or letter to display
    asset_path:  Optional[str]   # absolute path to video/image, or None
    asset_type:  str             # "video", "image", "svg", or "placeholder"
    is_letter:   bool  = False   # True = A-Z finger spelling
    duration_ms: int   = 1500    # display duration in milliseconds


# ── Main class ────────────────────────────────────────────────────────────────
class SignAnimator:
    """
    Converts text into an ordered list of SignFrame objects for the UI.

    Usage
    -----
    animator = SignAnimator()
    frames   = animator.text_to_frames("Thank you I need help")
    """

    def __init__(self):
        self.asset_dir = ASSET_DIR
        missing = self._count_missing()
        if missing > 0:
            print(f"ℹ️  SignAnimator: {missing} sign assets not yet downloaded.")
            print(f"   Run: python src/vision/download_signs.py  for a full report.")
        else:
            print("✅ SignAnimator: all sign assets present.")

    # ── Asset lookup ──────────────────────────────────────────────────────────

    def find_asset(self, base_name: str) -> tuple[Optional[str], str]:
        """
        Find an asset file for base_name, trying all accepted extensions.

        Returns (absolute_path, asset_type) or (None, "placeholder").
        asset_type is one of: "video", "image", "svg", "placeholder"
        """
        video_exts = {".mp4", ".gif", ".webm"}
        image_exts = {".png", ".jpg", ".jpeg"}

        for ext in ACCEPTED_EXTENSIONS:
            path = self.asset_dir / f"{base_name}{ext}"
            if path.exists():
                if ext in video_exts:
                    return str(path), "video"
                elif ext == ".svg":
                    return str(path), "svg"
                elif ext in image_exts:
                    return str(path), "image"

        return None, "placeholder"

    # ── Text → frames ─────────────────────────────────────────────────────────

    def text_to_frames(self, text: str) -> list[SignFrame]:
        """Convert a sentence into an ordered list of SignFrames."""
        if not text or not text.strip():
            return []
        tokens = self._tokenise(text)
        frames = []
        for token in tokens:
            frames.extend(self._token_to_frames(token))
        return frames

    def _tokenise(self, text: str) -> list[str]:
        """
        Split text into tokens, greedily matching multi-word phrases first.
        Longest phrases are matched first (greedy).
        """
        text  = text.lower().strip()
        text  = re.sub(r"[^\w\s']", " ", text)
        text  = re.sub(r"\s+", " ", text).strip()
        words = text.split()

        sorted_phrases = sorted(
            PHRASE_SIGNS.keys(),
            key=lambda p: len(p.split()),
            reverse=True,
        )

        tokens: list[str] = []
        i = 0
        while i < len(words):
            matched = False
            for phrase in sorted_phrases:
                pw  = phrase.split()
                end = i + len(pw)
                if words[i:end] == pw:
                    tokens.append(phrase)
                    i = end
                    matched = True
                    break
            if not matched:
                tokens.append(words[i])
                i += 1
        return tokens

    def _token_to_frames(self, token: str) -> list[SignFrame]:
        """
        Convert one token to SignFrame(s).
        Whole-word/phrase sign found → 1 frame.
        No whole-word sign → finger-spell letter by letter.
        """
        # Multi-word phrase
        if token in PHRASE_SIGNS:
            base              = PHRASE_SIGNS[token]
            path, asset_type  = self.find_asset(base)
            return [SignFrame(
                label       = token,
                asset_path  = path,
                asset_type  = asset_type,
                is_letter   = False,
                duration_ms = 2200,
            )]

        # Single word
        key = token.replace(" ", "_")
        if key in WORD_SIGNS:
            base             = WORD_SIGNS[key]
            path, asset_type = self.find_asset(base)
            return [SignFrame(
                label       = token,
                asset_path  = path,
                asset_type  = asset_type,
                is_letter   = False,
                duration_ms = 1800,
            )]

        # Finger spelling fallback
        frames = []
        for ch in token:
            if ch.isalpha():
                path, asset_type = self.find_asset(ch.lower())
                frames.append(SignFrame(
                    label       = ch.upper(),
                    asset_path  = path,
                    asset_type  = asset_type,
                    is_letter   = True,
                    duration_ms = 1000,
                ))
        return frames

    # ── Utility ───────────────────────────────────────────────────────────────

    def list_available_signs(self) -> list[str]:
        """Return words/phrases that have real sign assets (not just placeholders)."""
        available = []
        all_signs = {**PHRASE_SIGNS, **WORD_SIGNS}
        for word, base in all_signs.items():
            path, asset_type = self.find_asset(base)
            if path and asset_type != "placeholder":
                available.append(word)
        # Also include letters
        for letter in "abcdefghijklmnopqrstuvwxyz":
            path, asset_type = self.find_asset(letter)
            if path and asset_type != "placeholder":
                available.append(letter.upper())
        return sorted(set(available))

    def _count_missing(self) -> int:
        """Count how many expected assets are missing."""
        missing = 0
        for letter in "abcdefghijklmnopqrstuvwxyz":
            path, t = self.find_asset(letter)
            if t == "placeholder":
                missing += 1
        for base in set(WORD_SIGNS.values()):
            path, t = self.find_asset(base)
            if t == "placeholder":
                missing += 1
        return missing