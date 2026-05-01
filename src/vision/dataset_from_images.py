# src/vision/dataset_from_images.py
"""
Extract MediaPipe hand landmarks from downloaded sign language datasets.

FOLDER PLACEMENT
----------------
Put your unzipped dataset FOLDERS (not just files) inside a `datasets/`
folder in your project ROOT — NOT inside src/vision/:

    AccessHelp/                          ← project root
    ├── datasets/                        ← create this folder
    │   ├── asl_alphabet_train/          ← your alphabet+numbers dataset
    │   │   ├── A/  (images)
    │   │   ├── B/  (images)
    │   │   ...
    │   │   ├── 0/  (images)
    │   │   ...
    │   │   └── 9/  (images)
    │   └── wlasl_words/                 ← word signs dataset
    │       ├── hello/  (images/frames)
    │       ├── help/
    │       ...
    ├── src/
    ├── data/
    └── main.py

DATASETS TO DOWNLOAD (both from Kaggle)
----------------------------------------
1. Alphabet + Numbers (A-Z, 0-9):
   https://www.kaggle.com/datasets/grassknoted/asl-alphabet
   Unzip → you get folder: asl_alphabet_train/
   Place it at: AccessHelp/datasets/asl_alphabet_train/

2. Word Signs (WLASL — 2000 ASL words):
   https://www.kaggle.com/datasets/risangbaskoro/wlasl-processed
   Unzip → you get folder with word subfolders
   Place it at: AccessHelp/datasets/wlasl_words/

HOW TO RUN
----------
# Step 1 — Process alphabet + numbers dataset:
    python src/vision/dataset_from_images.py \\
        --data-dir datasets/asl_alphabet_train \\
        --output-dir data/signs \\
        --max-per-class 500

# Step 2 — Process word signs dataset (run separately, same output folder):
    python src/vision/dataset_from_images.py \\
        --data-dir datasets/wlasl_words \\
        --output-dir data/signs \\
        --max-per-class 300

# Step 3 — Train on combined data:
    python src/vision/train.py

NOTE: Run both commands with the SAME --output-dir so all landmarks
end up in one place for combined training.

WHAT IT DOES
------------
For each image:
  1. Runs MediaPipe hand detection
  2. Extracts 21 landmarks (x, y, z) = 126 values
  3. Normalises them
  4. Saves as data/signs/<LABEL>_<n>.npy

Images where no hand is detected are skipped automatically.
Typically 70-85% of images will have a detectable hand.
"""

import cv2
import numpy as np
import sys
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.vision.hand_tracker    import HandTracker
from src.vision.landmarks_utils import normalize_landmarks

# ── Default output ────────────────────────────────────────────────────────────
DEFAULT_OUTPUT = BASE_DIR / "data" / "signs"

# ── Labels to skip entirely ───────────────────────────────────────────────────
# These are non-sign classes that appear in some datasets
SKIP_LABELS = {
    "nothing", "del", "space", "background",
    "blank", "other", "unknown", "no_gesture",
}

# ── Label normalisation map ───────────────────────────────────────────────────
# Maps raw dataset folder names → clean label used in the model.
# Handles different naming conventions across datasets.
# Numbers are kept as-is ("0", "1" ... "9").
# Letters are kept as uppercase single chars ("A", "B" ... "Z").
# Words are normalised to lowercase no-spaces.
LABEL_MAP: dict[str, str] = {
    # ── Alphabet remappings (most datasets use uppercase already) ─────────────
    "a": "A", "b": "B", "c": "C", "d": "D", "e": "E",
    "f": "F", "g": "G", "h": "H", "i": "I", "j": "J",
    "k": "K", "l": "L", "m": "M", "n": "N", "o": "O",
    "p": "P", "q": "Q", "r": "R", "s": "S", "t": "T",
    "u": "U", "v": "V", "w": "W", "x": "X", "y": "Y",
    "z": "Z",

    # ── Number remappings ─────────────────────────────────────────────────────
    # Keep numbers as single digit strings
    "zero":  "0", "one": "1", "two": "2", "three": "3",
    "four":  "4", "five": "5", "six": "6", "seven": "7",
    "eight": "8", "nine": "9",

    # ── Common word sign remappings ───────────────────────────────────────────
    # WLASL and other datasets may use different folder name conventions.
    # Add more as needed for your specific dataset.
    "thank_you":        "thankyou",
    "thank you":        "thankyou",
    "i_love_you":       "iloveyou",
    "i love you":       "iloveyou",
    "how_are_you":      "howareyou",
    "how are you":      "howareyou",
    "good_morning":     "goodmorning",
    "good morning":     "goodmorning",
    "good_night":       "goodnight",
    "good night":       "goodnight",
    "good_afternoon":   "goodafternoon",
    "good afternoon":   "goodafternoon",
    "i_need_help":      "ineedhelp",
    "i need help":      "ineedhelp",
    "excuse_me":        "excuseme",
    "excuse me":        "excuseme",
    "nice_to_meet_you": "nicetomeetyou",
    "nice to meet you": "nicetomeetyou",
    # Single words — normalise to lowercase
    "hello":        "hello",
    "goodbye":      "goodbye",
    "bye":          "goodbye",
    "yes":          "yes",
    "no":           "no",
    "please":       "please",
    "sorry":        "sorry",
    "help":         "help",
    "emergency":    "emergency",
    "danger":       "danger",
    "stop":         "stop",
    "wait":         "wait",
    "good":         "good",
    "bad":          "bad",
    "love":         "love",
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
    "hot":          "hot",
    "cold":         "cold",
    "more":         "more",
    "finished":     "finished",
    "done":         "finished",
    "want":         "want",
    "need":         "need",
    "know":         "know",
    "understand":   "understand",
    "come":         "come",
    "go":           "go",
    "again":        "again",
    "call":         "call",
    "family":       "family",
    "friend":       "friend",
    "mother":       "mother",
    "father":       "father",
    "time":         "time",
    "today":        "today",
    "tomorrow":     "tomorrow",
    "yesterday":    "yesterday",
    "morning":      "morning",
    "night":        "night",
    "money":        "money",
    "name":         "name",
    "where":        "where",
    "what":         "what",
    "when":         "when",
    "why":          "why",
    "how":          "how",
    "who":          "who",
    "i":            "i",
    "me":           "i",
    "you":          "you",
    "he":           "he",
    "she":          "she",
    "we":           "we",
    "they":         "they",
    "my":           "my",
    "your":         "your",
    "happy":        "happy",
    "sad":          "sad",
}


def _normalise_label(raw: str) -> str | None:
    """
    Convert a raw dataset folder name to a clean model label.
    Returns None if the label should be skipped.
    """
    raw_lower = raw.lower().strip()

    # Skip non-sign classes
    if raw_lower in SKIP_LABELS:
        return None

    # Check label map first
    if raw_lower in LABEL_MAP:
        return LABEL_MAP[raw_lower]
    if raw in LABEL_MAP:
        return LABEL_MAP[raw]

    # Single uppercase letter → keep as-is (A, B, C...)
    if len(raw) == 1 and raw.isalpha():
        return raw.upper()

    # Single digit → keep as-is (0, 1, 2...)
    if len(raw) == 1 and raw.isdigit():
        return raw

    # Lowercase word not in map → use as-is (covers WLASL word labels)
    return raw_lower


def _augment_image(img: np.ndarray) -> list[np.ndarray]:
    """
    Return the original image plus several augmented versions.
    This makes the model robust to real-world cameras which have
    different backgrounds, lighting, and angles than dataset images.

    Augmentations applied:
    - Brightness variation  (darker / brighter)
    - Horizontal flip       (mirror image)
    - Slight blur           (simulates low-quality cameras)
    - Random noise          (simulates grainy footage)
    - Slight rotation       (±10 degrees)
    """
    results = [img]   # always include the original

    # 1. Darker version
    darker = np.clip(img.astype(np.int16) - 40, 0, 255).astype(np.uint8)
    results.append(darker)

    # 2. Brighter version
    brighter = np.clip(img.astype(np.int16) + 40, 0, 255).astype(np.uint8)
    results.append(brighter)

    # 3. Horizontal flip (mirror)
    results.append(cv2.flip(img, 1))

    # 4. Slight blur (simulates lower-quality webcam)
    blurred = cv2.GaussianBlur(img, (3, 3), 0)
    results.append(blurred)

    # 5. Random noise
    noise = np.random.randint(-20, 20, img.shape, dtype=np.int16)
    noisy = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    results.append(noisy)

    # 6. Slight rotation +8 degrees
    h, w  = img.shape[:2]
    M     = cv2.getRotationMatrix2D((w // 2, h // 2), 8, 1.0)
    rot_p = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    results.append(rot_p)

    # 7. Slight rotation -8 degrees
    M     = cv2.getRotationMatrix2D((w // 2, h // 2), -8, 1.0)
    rot_n = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    results.append(rot_n)

    return results   # 8 images total per original


def extract_from_image(
    tracker: HandTracker,
    image_path: str,
    augment: bool = True,
) -> list[np.ndarray]:
    """
    Load image, optionally augment, detect hand in each version.
    Returns a list of normalised 126-feature vectors (one per successful detection).
    """
    img = cv2.imread(image_path)
    if img is None:
        return []

    img = cv2.resize(img, (320, 320))

    images = _augment_image(img) if augment else [img]
    results = []
    for im in images:
        lm, _ = tracker.get_hand_landmarks(im)
        if lm is not None:
            results.append(normalize_landmarks(lm))
    return results


def process_dataset(
    data_dir:      Path,
    output_dir:    Path,
    max_per_class: int = 500,
    min_per_class: int = 30,
):
    """
    Walk data_dir subfolders, extract landmarks, save .npy files.

    Expected structure:
        data_dir/
            ClassFolderA/  (e.g. "A", "0", "hello")
                img1.jpg
                img2.png
                ...
            ClassFolderB/
                ...
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    tracker = HandTracker()

    class_dirs = sorted([d for d in data_dir.iterdir() if d.is_dir()])
    if not class_dirs:
        print(f"❌ No class subdirectories found in: {data_dir}")
        print(f"   Expected: {data_dir}/A/, {data_dir}/B/, {data_dir}/hello/ etc.")
        return

    print(f"\n📂 {len(class_dirs)} class folders found in {data_dir.name}")
    print(f"📊 Max samples per class: {max_per_class}")
    print(f"💾 Saving landmarks to: {output_dir}\n")

    total_saved   = 0
    total_skipped = 0
    class_counts: dict[str, int] = {}

    for class_dir in class_dirs:
        # Normalise label
        label = _normalise_label(class_dir.name)
        if label is None:
            print(f"  [SKIP]  {class_dir.name}")
            continue

        # Collect image files (also handles video frame folders)
        image_files: list[Path] = []
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.bmp",
                    "*.JPG", "*.JPEG", "*.PNG", "*.BMP"):
            image_files.extend(class_dir.glob(ext))
            # Also check one level deep (some datasets have subfolders per video)
            image_files.extend(class_dir.glob(f"*/{ext}"))

        if not image_files:
            print(f"  [SKIP]  {class_dir.name} — no images found")
            continue

        # Shuffle for variety, oversample to account for detection failures
        rng = np.random.default_rng(42)
        rng.shuffle(image_files := list(image_files))
        image_files = image_files[: max_per_class * 4]

        print(f"  {label:20s} ({len(image_files)} images)...", end="", flush=True)

        # Check how many samples already exist for this label
        existing = len(list(output_dir.glob(f"{label}_*.npy")))

        saved_this_run = 0
        for img_path in image_files:
            vectors = extract_from_image(tracker, str(img_path), augment=True)
            for lm_vec in vectors:
                arr  = lm_vec.reshape(1, -1)   # shape (1, 126)
                path = output_dir / f"{label}_{existing + saved_this_run + 1}.npy"
                np.save(str(path), arr)
                saved_this_run += 1
                if saved_this_run >= max_per_class:
                    break
            if saved_this_run >= max_per_class:
                break

        no_hand = len(image_files) - (saved_this_run // 8 or 1)

        if saved_this_run < min_per_class:
            print(f" ⚠️  only {saved_this_run} detected (need {min_per_class}) — skipping class")
            # Delete the few files we saved
            for p in output_dir.glob(f"{label}_{existing + 1}_{existing + saved_this_run + 1}.npy"):
                p.unlink(missing_ok=True)
            total_skipped += saved_this_run
            continue

        print(f" ✅ {saved_this_run} saved  ({no_hand} no-hand skips)")
        class_counts[label] = existing + saved_this_run
        total_saved += saved_this_run
        total_skipped += no_hand

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Saved   : {total_saved:,} new samples")
    print(f"  Skipped : {total_skipped:,} images (no hand detected)")
    print(f"  Classes : {len(class_counts)}")
    print(f"  Output  : {output_dir}")
    print(f"{'='*60}")

    print("\n📊 Samples per class:")
    for lbl in sorted(class_counts):
        bar = "█" * min(class_counts[lbl] // 10, 50)
        print(f"  {lbl:20s}: {bar} ({class_counts[lbl]:,})")

    low = [l for l, c in class_counts.items() if c < min_per_class]
    if low:
        print(f"\n⚠️  Low count classes: {low}")
        print("   Try: --max-per-class 1000")

    print(f"\n✅ Done!  Next step:  python src/vision/train.py")


def main():
    parser = argparse.ArgumentParser(
        description="Extract hand landmarks from a sign language image dataset."
    )
    parser.add_argument(
        "--data-dir", type=str, required=True,
        help="Dataset folder (contains one subfolder per sign label)",
    )
    parser.add_argument(
        "--output-dir", type=str, default=str(DEFAULT_OUTPUT),
        help=f"Where to save .npy files (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--max-per-class", type=int, default=500,
        help="Max samples per class (default 500 — good balance of speed vs accuracy)",
    )
    parser.add_argument(
        "--min-per-class", type=int, default=30,
        help="Min samples to keep a class (default 30)",
    )
    args   = parser.parse_args()
    d_dir  = Path(args.data_dir)
    o_dir  = Path(args.output_dir)

    if not d_dir.exists():
        print(f"❌ Dataset folder not found: {d_dir}")
        print(f"   Make sure you placed it at: AccessHelp/{d_dir}")
        sys.exit(1)

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║   AccessHelp — Landmark Extractor                            ║
╠══════════════════════════════════════════════════════════════╣
║  Dataset   : {str(d_dir.name)[:48]:48s}  ║
║  Output    : {str(o_dir)[:48]:48s}  ║
║  Max/class : {args.max_per_class:<4d}                                          ║
╚══════════════════════════════════════════════════════════════╝
""")

    process_dataset(d_dir, o_dir, args.max_per_class, args.min_per_class)


if __name__ == "__main__":
    main()