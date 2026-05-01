#!/usr/bin/env python3
# src/vision/download_signs.py
"""
Sign language asset checker for AccessHelp.

Since you have collected alphabet signs as .mp4 files (a.mp4, b.mp4 ...),
this script checks which files are present and creates SVG placeholders
for anything still missing, so the app never crashes.

HOW TO USE
----------
1. Place your alphabet .mp4 files in:
       AccessHelp/src/vision/sign_assets/
   Files should be named:  a.mp4, b.mp4, c.mp4 ... z.mp4

2. For word signs, download manually from:
       https://www.handspeak.com/word/
   Search each word, save the video/GIF, rename to the filename
   shown in the MISSING report below.
   Supported formats for each file: .mp4, .gif, .png, .webm

3. Run this script to check status:
       python src/vision/download_signs.py

The app works immediately with SVG placeholders for missing files.
Real videos make the animations accurate and useful for deaf users.
"""

from pathlib import Path

# ── Asset directory ───────────────────────────────────────────────────────────
HERE      = Path(__file__).resolve().parent
ASSET_DIR = HERE / "sign_assets"
ASSET_DIR.mkdir(exist_ok=True)

# ── Accepted video/image formats (checked in this priority order) ─────────────
# .mp4 is checked first since that is what you collected for the alphabet.
ACCEPTED_EXTENSIONS = [".mp4", ".gif", ".webm", ".png", ".jpg", ".jpeg"]

# ── Expected alphabet files ───────────────────────────────────────────────────
ALPHABET_LETTERS = list("abcdefghijklmnopqrstuvwxyz")

# ── Expected word sign base names (without extension) ────────────────────────
# sign_animator.py will look for these.
# For each name the script checks all ACCEPTED_EXTENSIONS automatically.
WORD_SIGN_NAMES = [
    "hello", "goodbye", "thankyou", "please", "sorry",
    "help", "yes", "no", "iloveyou", "good",
    "bad", "water", "food", "emergency", "stop",
    "wait", "more", "finished", "want", "need",
    "i", "you", "happy", "sad", "doctor",
    "hospital", "howareyou", "goodmorning", "goodnight", "ineedhelp",
    "danger", "love", "eat", "drink", "bathroom",
    "home", "school", "work", "pain", "sick",
    "tired", "angry", "hot", "cold", "know",
    "understand", "come", "go", "call", "family",
    "friend", "mother", "father", "time", "today",
    "morning", "night", "money", "my", "your",
    "he", "she", "we", "they", "name",
    "where", "what", "when", "why", "how",
    "who", "speak", "read", "write", "learn",
    "think", "feel", "see", "hear", "again",
    "remember", "forget", "tomorrow", "yesterday",
]


def find_asset(base_name: str) -> Path | None:
    """
    Return the path to an existing asset file for base_name,
    checking all accepted extensions in priority order.
    Returns None if no file found.
    """
    for ext in ACCEPTED_EXTENSIONS:
        path = ASSET_DIR / f"{base_name}{ext}"
        if path.exists():
            return path
    return None


def _make_placeholder(label: str, base_name: str):
    """
    Create an SVG placeholder for a missing sign.
    Written with encoding='utf-8' (fixes Windows cp1252 crash).
    Uses XML entity for hand emoji so SVG content is pure ASCII.
    """
    svg_path = ASSET_DIR / f"{base_name}.svg"
    if svg_path.exists():
        return   # already has a placeholder

    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<svg width="300" height="300" xmlns="http://www.w3.org/2000/svg">'
        '<rect width="300" height="300" rx="20" fill="#667eea" opacity="0.10"/>'
        '<rect x="10" y="10" width="280" height="280" rx="15"'
        ' fill="none" stroke="#667eea" stroke-width="2.5"/>'
        '<text x="150" y="125" text-anchor="middle" font-size="72"'
        ' font-family="Arial, sans-serif">&#x270B;</text>'
        f'<text x="150" y="200" text-anchor="middle" font-size="32"'
        f' font-family="Arial, sans-serif" font-weight="bold"'
        f' fill="#2c3e50">{label.upper()}</text>'
        '<text x="150" y="235" text-anchor="middle" font-size="12"'
        ' font-family="Arial, sans-serif" fill="#999">'
        'Download from handspeak.com</text>'
        '</svg>'
    )
    svg_path.write_text(svg, encoding="utf-8")


def check_and_create_placeholders():
    print(f"\nChecking sign assets in:\n  {ASSET_DIR}\n")
    print(f"Accepted formats: {', '.join(ACCEPTED_EXTENSIONS)}\n")

    # ── Alphabet ──────────────────────────────────────────────────────────────
    print("── Alphabet (A-Z) ──────────────────────────────────────────")
    print("   You said you have a.mp4 ... z.mp4 — place them in sign_assets/\n")

    alphabet_ok      = []
    alphabet_missing = []

    for letter in ALPHABET_LETTERS:
        found = find_asset(letter)
        if found:
            print(f"  [OK]      {found.name}")
            alphabet_ok.append(letter)
        else:
            print(f"  [MISSING] {letter}.mp4  <-- copy your file here")
            alphabet_missing.append(letter)
            _make_placeholder(letter, letter)

    # ── Word signs ────────────────────────────────────────────────────────────
    print(f"\n── Word signs ({len(WORD_SIGN_NAMES)} words) ─────────────────────────────────")
    print("   Download from: https://www.handspeak.com/word/\n")

    words_ok      = []
    words_missing = []

    for name in WORD_SIGN_NAMES:
        found = find_asset(name)
        if found:
            print(f"  [OK]      {found.name}")
            words_ok.append(name)
        else:
            print(f"  [MISSING] {name}.mp4  (or .gif / .webm)")
            words_missing.append(name)
            _make_placeholder(name, name)

    # ── Summary ───────────────────────────────────────────────────────────────
    total_ok      = len(alphabet_ok) + len(words_ok)
    total_missing = len(alphabet_missing) + len(words_missing)
    total         = len(ALPHABET_LETTERS) + len(WORD_SIGN_NAMES)

    print(f"\n{'='*60}")
    print(f"  Ready  : {total_ok} / {total} sign assets")
    print(f"  Missing: {total_missing}  (SVG placeholders created)")
    print(f"{'='*60}")

    if alphabet_missing:
        print(f"\n  Alphabet still missing ({len(alphabet_missing)} letters):")
        print(f"  {', '.join(l.upper() for l in alphabet_missing)}")
        print(f"\n  Copy your .mp4 files here: {ASSET_DIR}")

    if words_missing:
        print(f"\n  Word signs still missing ({len(words_missing)}):")
        for w in words_missing:
            word_display = w.replace("thankyou","thank you")\
                            .replace("iloveyou","i love you")\
                            .replace("howareyou","how are you")\
                            .replace("goodmorning","good morning")\
                            .replace("goodnight","good night")\
                            .replace("ineedhelp","i need help")
            print(f"    {(w+'.mp4'):25s}  search '{word_display}' on handspeak.com/word")
        print(f"\n  Save each video/GIF using the exact filename shown above.")

    print(f"\n  App works now with SVG placeholders for missing signs.")
    print(f"  Run this script again after adding files to update the report.\n")


if __name__ == "__main__":
    check_and_create_placeholders()