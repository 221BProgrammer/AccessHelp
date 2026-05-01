#!/usr/bin/env python3
# src/vision/wlasl_extract.py
"""
WLASL Frame Extractor for AccessHelp.

Reads WLASL_v0.3.json to find which video IDs correspond to which words,
then extracts frames from whatever videos you have already downloaded.
You do NOT need all 21,000 videos — it works with however many you have.

USAGE
-----
    python src/vision/wlasl_extract.py

Place your WLASL folder at:
    AccessHelp/datasets/WLASL/
        ├── videos/           ← your downloaded .mp4 files (64414.mp4 etc.)
        └── WLASL_v0.3.json   ← the label mapping file

Output goes to:
    AccessHelp/datasets/wlasl_frames/
        ├── hello/
        │   ├── frame_001.jpg
        │   └── frame_002.jpg
        ├── help/
        └── ...

Then run dataset_from_images.py pointing to wlasl_frames/:
    python src/vision/dataset_from_images.py
        --data-dir datasets/wlasl_frames
        --output-dir data/signs
        --max-per-class 300

HOW MANY FRAMES TO EXTRACT
---------------------------
Each video is typically 1-3 seconds at 25fps = 25-75 frames.
We extract one frame every N frames (stride) to avoid redundancy.
Default stride=5 gives ~5-15 frames per video — plenty for training.
"""

import cv2
import json
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent.parent.parent
WLASL_DIR    = BASE_DIR / "datasets" / "WLASL"
VIDEO_DIR    = WLASL_DIR / "videos"
JSON_FILE    = WLASL_DIR / "WLASL_v0.3.json"
OUTPUT_DIR   = BASE_DIR / "datasets" / "wlasl_frames"

# ── Config ────────────────────────────────────────────────────────────────────
FRAME_STRIDE      = 5      # extract 1 frame every N frames
MAX_FRAMES_PER_VIDEO = 20  # cap per video to keep class sizes balanced
MIN_VIDEOS_PER_WORD  = 2   # skip words with too few videos

# ── Words to extract ──────────────────────────────────────────────────────────
# If empty, extracts ALL words found in the JSON.
# To extract only specific words, list them here:
TARGET_WORDS: set[str] = set()   # empty = extract all available


def extract_frames(video_path: Path, out_dir: Path, stride: int, max_frames: int):
    """Extract frames from a video at given stride into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return 0

    frame_idx   = 0
    saved       = 0
    existing    = len(list(out_dir.glob("*.jpg")))

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % stride == 0:
            fname = out_dir / f"frame_{existing + saved + 1:04d}.jpg"
            cv2.imwrite(str(fname), frame)
            saved += 1
            if saved >= max_frames:
                break
        frame_idx += 1

    cap.release()
    return saved


def main():
    # ── Validate paths ────────────────────────────────────────────────────────
    if not WLASL_DIR.exists():
        print(f"❌ WLASL folder not found: {WLASL_DIR}")
        print(f"   Place your WLASL folder at: {WLASL_DIR}")
        sys.exit(1)

    if not JSON_FILE.exists():
        print(f"❌ JSON file not found: {JSON_FILE}")
        print(f"   Expected: {JSON_FILE}")
        sys.exit(1)

    if not VIDEO_DIR.exists():
        print(f"❌ Videos folder not found: {VIDEO_DIR}")
        print(f"   Expected: {VIDEO_DIR}")
        sys.exit(1)

    # ── Load JSON ─────────────────────────────────────────────────────────────
    print(f"📖 Reading: {JSON_FILE.name}")
    with open(JSON_FILE, encoding="utf-8") as f:
        data = json.load(f)

    print(f"   {len(data)} words defined in WLASL dataset")

    # ── Find available videos ─────────────────────────────────────────────────
    available_videos = {p.stem for p in VIDEO_DIR.glob("*.mp4")}
    print(f"   {len(available_videos)} videos found in {VIDEO_DIR.name}/")

    # ── Extract frames ────────────────────────────────────────────────────────
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_words    = 0
    total_frames   = 0
    skipped_words  = 0
    word_summary: dict[str, int] = {}

    for entry in data:
        gloss     = entry.get("gloss", "").lower().strip()
        instances = entry.get("instances", [])

        if not gloss or not instances:
            continue

        # Filter to target words if specified
        if TARGET_WORDS and gloss not in TARGET_WORDS:
            continue

        # Find which video IDs we actually have
        available = [
            inst for inst in instances
            if inst.get("video_id") in available_videos
        ]

        if len(available) < MIN_VIDEOS_PER_WORD:
            skipped_words += 1
            continue

        word_dir     = OUTPUT_DIR / gloss
        frames_saved = 0

        for inst in available:
            vid_id    = inst["video_id"]
            vid_path  = VIDEO_DIR / f"{vid_id}.mp4"
            saved     = extract_frames(
                vid_path, word_dir,
                stride     = FRAME_STRIDE,
                max_frames = MAX_FRAMES_PER_VIDEO,
            )
            frames_saved += saved

        if frames_saved > 0:
            word_summary[gloss] = frames_saved
            total_words  += 1
            total_frames += frames_saved
            print(f"  ✅ {gloss:20s} — {frames_saved} frames from {len(available)} videos")
        else:
            skipped_words += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  Words extracted : {total_words}")
    print(f"  Words skipped   : {skipped_words} (no videos available)")
    print(f"  Total frames    : {total_frames:,}")
    print(f"  Output folder   : {OUTPUT_DIR}")
    print(f"{'='*60}")

    if total_words == 0:
        print("\n❌ No frames extracted.")
        print("   Check that your video files are in:", VIDEO_DIR)
        print("   And that WLASL_v0.3.json is in:", WLASL_DIR)
        sys.exit(1)

    print(f"\n✅ Done! Now run:")
    print(f"   python src/vision/dataset_from_images.py "
          f"--data-dir datasets/wlasl_frames --output-dir data/signs --max-per-class 300")


if __name__ == "__main__":
    main()