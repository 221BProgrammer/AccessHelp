# src/vision/real_time_sign.py
"""
Real-time sign language recognition.

Handles all three sign types in one loop:
  - Letters  A-Z  → added to letter buffer for word building + autocomplete
  - Numbers  0-9  → added directly to sentence as a token
  - Words    (hello, help, thankyou...) → added directly as a confirmed word

The model's classes determine what is detected.
Training on alphabet+numbers+words means all three work simultaneously.

Controls
--------
  SPACE      → confirm current word (uses top suggestion if available)
  1/2/3      → pick autocomplete suggestion
  b          → backspace (remove last signed letter)
  w          → remove last completed word from sentence
  s          → speak current sentence aloud
  r          → reset everything
  h          → show sentence history
  q          → quit
"""

import cv2
import numpy as np
import os
import sys
import time
import threading
import tempfile
from pathlib import Path

import pygame
from gtts import gTTS

# ── Model ─────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    import joblib
    model   = joblib.load(str(BASE_DIR / "sign_model.pkl"))
    CLASSES = list(model.classes_)
    print(f"✅ Model loaded — {len(CLASSES)} classes")
except FileNotFoundError:
    print("❌ sign_model.pkl not found.")
    print("   1. python src/vision/dataset_from_images.py --data-dir datasets/asl_alphabet_train --output-dir data/signs")
    print("   2. python src/vision/dataset_from_images.py --data-dir datasets/wlasl_words --output-dir data/signs")
    print("   3. python src/vision/train.py")
    sys.exit(1)
except Exception as e:
    print(f"❌ Model load error: {e}")
    sys.exit(1)

from src.vision.hand_tracker       import HandTracker
from src.vision.landmarks_utils    import normalize_landmarks, aggregate_live_window
from src.vision.sentence_processor import LetterBuffer

# ── Classify each model class ─────────────────────────────────────────────────
LETTER_CLASSES = {c for c in CLASSES if len(c) == 1 and c.isalpha()}
NUMBER_CLASSES = {c for c in CLASSES if len(c) == 1 and c.isdigit()}
WORD_CLASSES   = {c for c in CLASSES
                  if c not in LETTER_CLASSES and c not in NUMBER_CLASSES}

print(f"   Letters : {sorted(LETTER_CLASSES)}")
print(f"   Numbers : {sorted(NUMBER_CLASSES)}")
print(f"   Words   : {sorted(WORD_CLASSES)}")

# ── Init ──────────────────────────────────────────────────────────────────────
pygame.mixer.init()
tracker = HandTracker()
buffer  = LetterBuffer()
cap     = cv2.VideoCapture(0)
if not cap.isOpened():
    print("❌ Camera not found.")
    sys.exit(1)

# ── Detection config ──────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = 0.45   # lowered from 0.65 — dataset images have clean
                               # backgrounds but real cameras don't; 0.45 gives
                               # visible predictions while still filtering noise
WINDOW_SIZE          = 20     # rolling frames for prediction
STABLE_FRAMES        = 15     # consecutive agreeing frames before adding letter
SIGN_COOLDOWN        = 1.2    # seconds before same sign can repeat

# ── State ─────────────────────────────────────────────────────────────────────
frame_window    : list  = []
stable_count    : int   = 0
current_pred    : str   = ""
last_added      : str   = ""
last_added_time : float = 0.0
sentence_history: list  = []
state           : dict  = buffer._state()

print("\n🚀 AccessHelp — Real-Time Sign Detection")
print("SPACE=confirm  1/2/3=pick  b=back  w=del-word  s=speak  r=reset  q=quit\n")


# ── TTS helper ────────────────────────────────────────────────────────────────
def speak_text(text: str):
    def _run():
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                tmp = f.name
            gTTS(text=text, lang="en").save(tmp)
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            pygame.mixer.music.unload()
            os.unlink(tmp)
        except Exception as e:
            print(f"TTS: {e}")
    threading.Thread(target=_run, daemon=True).start()


# ── HUD drawing ───────────────────────────────────────────────────────────────
def draw_hud(frame, pred: str, conf: float):
    h, w = frame.shape[:2]

    # ── Sign type label and colour ────────────────────────────────────────────
    if pred in WORD_CLASSES:
        sign_type = "[WORD]"
        hi_color  = (0, 200, 255)    # cyan
    elif pred in NUMBER_CLASSES:
        sign_type = "[NUM]"
        hi_color  = (255, 165, 0)    # orange
    else:
        sign_type = ""
        hi_color  = (0, 255, 0)      # green

    # Always show the current best prediction and its confidence
    # so the user can see what the model is detecting even below threshold
    if pred:
        above = conf >= CONFIDENCE_THRESHOLD
        disp  = f"{sign_type} {pred}".strip()
        color = hi_color if above else (160, 160, 160)   # grey = below threshold
        cv2.putText(frame, disp,
                    (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 1.9, color, 3)
        # Confidence percentage always visible
        conf_color = hi_color if above else (100, 100, 100)
        cv2.putText(frame, f"{conf:.0%}{'  OK' if above else '  low'}",
                    (10, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.7, conf_color, 2)
    else:
        cv2.putText(frame, "Waiting...",
                    (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (80, 80, 80), 2)

    # Stability bar
    bw = int((stable_count / STABLE_FRAMES) * 210)
    cv2.rectangle(frame, (10, 104), (220, 118), (45, 45, 45), -1)
    cv2.rectangle(frame, (10, 104), (10 + bw, 118),
                  (0, 255, 0) if bw >= 210 else (0, 160, 255), -1)
    cv2.putText(frame, "stability", (224, 117),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, (130, 130, 130), 1)

    # Bottom info panel
    ov = frame.copy()
    cv2.rectangle(ov, (0, h - 178), (w, h), (18, 18, 18), -1)
    cv2.addWeighted(ov, 0.65, frame, 0.35, 0, frame)

    y       = h - 163
    cw      = state["current_word"]
    is_name = state["is_name"]

    # Current spelling buffer
    tag = "  [NAME — spelling freely]" if is_name else ""
    cv2.putText(frame, f"Spelling: {cw}{tag}", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.70,
                (0, 255, 255) if is_name else (255, 255, 255), 2)
    y += 32

    # Autocomplete suggestions
    sugs = state["suggestions"]
    if sugs and not is_name:
        s_str = "   ".join(f"[{i+1}]{s}" for i, s in enumerate(sugs[:3]))
        cv2.putText(frame, s_str, (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (255, 210, 50), 2)
    elif is_name:
        cv2.putText(frame, "Autocomplete OFF (name mode)", (10, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (130, 100, 255), 1)
    y += 30

    # Sentence
    sentence = state["sentence"]
    cv2.putText(frame, sentence if sentence else "—", (10, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (100, 255, 100), 2)
    y += 28

    cv2.putText(
        frame,
        "SPC=confirm word  1/2/3=suggestion  b=back  w=del-word  s=speak  r=reset  q=quit",
        (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (120, 120, 120), 1,
    )


# ── Main loop ─────────────────────────────────────────────────────────────────
pred       = ""
confidence = 0.0

while True:
    ret, frame = cap.read()
    if not ret or frame is None:
        continue

    frame     = cv2.flip(frame, 1)
    lm, frame = tracker.get_hand_landmarks(frame)

    if lm:
        norm = normalize_landmarks(lm)
        frame_window.append(norm)
        if len(frame_window) > WINDOW_SIZE:
            frame_window.pop(0)

        if len(frame_window) >= 5:
            feat       = aggregate_live_window(frame_window).reshape(1, -1)
            probs      = model.predict_proba(feat)[0]
            confidence = float(np.max(probs))
            pred       = model.classes_[int(np.argmax(probs))]

            if confidence >= CONFIDENCE_THRESHOLD:
                if pred == current_pred:
                    stable_count += 1
                else:
                    current_pred = pred
                    stable_count = 1
            else:
                stable_count = 0

            now         = time.time()
            cooldown_ok = not (pred == last_added and
                               (now - last_added_time) < SIGN_COOLDOWN)

            if stable_count >= STABLE_FRAMES and cooldown_ok:
                last_added      = pred
                last_added_time = now
                stable_count    = 0
                frame_window    = []

                if pred in WORD_CLASSES:
                    # Whole-word sign → add directly to sentence
                    buffer.sentence_words.append(pred.lower())
                    state = buffer._state()
                    print(f"🤟 Word: '{pred}'  → {state['sentence']}")

                elif pred in NUMBER_CLASSES:
                    # Number → add directly to sentence as a token
                    buffer.sentence_words.append(pred)
                    state = buffer._state()
                    print(f"🔢 Number: '{pred}'  → {state['sentence']}")

                else:
                    # Letter → add to letter buffer for word building
                    state = buffer.add_letter(pred)
                    print(f"✍  Letter: {pred}  word={state['current_word']}"
                          f"{'  [NAME]' if state['is_name'] else ''}"
                          f"  suggest={state['suggestions']}")
    else:
        stable_count  = 0
        current_pred  = ""
        pred          = ""
        confidence    = 0.0
        frame_window  = []

    draw_hud(frame, pred, confidence)

    if not lm:
        cv2.putText(frame, "No hand detected", (10, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.80, (0, 140, 255), 2)

    cv2.imshow("AccessHelp — Sign Language", frame)
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    elif key == ord(" "):
        # SPACE always confirms the raw spelled word as-is.
        # If you want a suggestion instead, press 1, 2, or 3.
        if state["current_word"]:
            print(f"✅ Confirmed word: '{state['current_word']}'")
            state = buffer.confirm_word()   # uses raw letters, ignores suggestions

    elif key == ord("1") and len(state["suggestions"]) >= 1:
        state = buffer.confirm_suggestion(state["suggestions"][0])
    elif key == ord("2") and len(state["suggestions"]) >= 2:
        state = buffer.confirm_suggestion(state["suggestions"][1])
    elif key == ord("3") and len(state["suggestions"]) >= 3:
        state = buffer.confirm_suggestion(state["suggestions"][2])

    elif key == ord("b"):
        state = buffer.delete_last_letter()

    elif key == ord("w"):
        state = buffer.delete_last_word()

    elif key == ord("s"):
        s = state["sentence"]
        if s:
            speak_text(s)
            sentence_history.append(s)
            if len(sentence_history) > 10:
                sentence_history.pop(0)
            print(f"🔊 {s}")

    elif key == ord("r"):
        state        = buffer.clear_all()
        frame_window = []
        stable_count = 0
        print("🧹 Reset")

    elif key == ord("h"):
        print("\n📜 History:")
        for i, s in enumerate(sentence_history[-5:], 1):
            print(f"  {i}. {s}")

cap.release()
cv2.destroyAllWindows()
pygame.mixer.quit()
print(f"\n🎉 Done — last sentence: {state['sentence']}")