# src/vision/train.py
"""
Train the AccessHelp sign language classifier.

Handles three types of labels:
  - Letters  : A-Z  (single uppercase char)
  - Numbers  : 0-9  (single digit char)
  - Words    : hello, help, thankyou, sorry ...  (lowercase string)

All come from the same data/signs/ folder produced by dataset_from_images.py.
"""

import numpy as np
import sys
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
import joblib

BASE_DIR   = Path(__file__).resolve().parent.parent.parent
DATA_DIR   = BASE_DIR / "data" / "signs"
MODEL_PATH = BASE_DIR / "sign_model.pkl"

sys.path.insert(0, str(BASE_DIR))
from src.vision.landmarks_utils import aggregate_sequence

# ── Load data ─────────────────────────────────────────────────────────────────
print(f"📊 Loading data from: {DATA_DIR}")

if not DATA_DIR.exists():
    print(f"❌ {DATA_DIR} not found.")
    print("   Run dataset_from_images.py first:")
    print("     python src/vision/dataset_from_images.py --data-dir datasets/asl_alphabet_train --output-dir data/signs")
    sys.exit(1)

X:            list = []
y:            list = []
label_counts: dict = {}
skipped             = 0

for npy_file in sorted(DATA_DIR.iterdir()):
    if npy_file.suffix != ".npy":
        continue

    # Label = everything before the last _N  e.g. "thankyou_23.npy" → "thankyou"
    parts = npy_file.stem.rsplit("_", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        skipped += 1
        continue
    label = parts[0]

    try:
        data = np.load(str(npy_file), allow_pickle=False)
    except Exception as e:
        print(f"  ⚠️  Cannot load {npy_file.name}: {e}")
        skipped += 1
        continue

    # Normalise shape: accept (126,), (504,), (1,126), (N,126), (B,N,126)
    if data.ndim == 1:
        flat_len = data.shape[0]
        if flat_len == 504:
            # Already aggregated — use directly
            X.append(data.astype(np.float32))
            y.append(label)
            label_counts[label] = label_counts.get(label, 0) + 1
        elif flat_len == 126:
            # Single normalised frame — wrap and aggregate
            feat = aggregate_sequence(data.reshape(1, -1))
            X.append(feat)
            y.append(label)
            label_counts[label] = label_counts.get(label, 0) + 1
        else:
            print(f"  ⚠️  Unexpected flat shape ({flat_len},) in {npy_file.name} — skipping")
            skipped += 1
        continue

    if data.ndim == 2:
        # Shape (N, 126) — one sample with N frames
        if data.shape[1] != 126:
            print(f"  ⚠️  Expected 126 features, got {data.shape[1]} in {npy_file.name} — skipping")
            skipped += 1
            continue
        feat = aggregate_sequence(data)
        X.append(feat)
        y.append(label)
        label_counts[label] = label_counts.get(label, 0) + 1

    elif data.ndim == 3:
        # Shape (B, N, 126) — batch of samples
        for sample in data:
            X.append(aggregate_sequence(sample))
            y.append(label)
        label_counts[label] = label_counts.get(label, 0) + len(data)
    else:
        print(f"  ⚠️  Unexpected shape {data.shape} in {npy_file.name} — skipping")
        skipped += 1

# ── Verify all feature vectors are the same size before stacking ──────────────
if X:
    sizes = set(len(v) for v in X)
    if len(sizes) > 1:
        print(f"\n⚠️  Inconsistent feature sizes found: {sizes}")
        print(f"   Keeping only samples with size 504 (the standard aggregate size)...")
        paired   = [(xi, yi) for xi, yi in zip(X, y) if len(xi) == 504]
        if not paired:
            print("❌ No samples with size 504 found after filtering.")
            print("   Delete data/signs/ and re-run dataset_from_images.py")
            sys.exit(1)
        X, y = zip(*paired)
        X = list(X)
        y = list(y)
        print(f"   Kept {len(X):,} samples after size normalisation.")

# ── Validate ──────────────────────────────────────────────────────────────────
if not X:
    print("❌ No samples loaded.")
    sys.exit(1)

unique_labels = sorted(set(y))
if len(unique_labels) < 2:
    print(f"❌ Need at least 2 classes, found: {unique_labels}")
    sys.exit(1)

X_arr = np.array(X, dtype=np.float32)
y_arr = np.array(y)

# ── Report ────────────────────────────────────────────────────────────────────
letter_labels = [l for l in unique_labels if len(l) == 1 and l.isalpha()]
number_labels = [l for l in unique_labels if len(l) == 1 and l.isdigit()]
word_labels   = [l for l in unique_labels if l not in letter_labels and l not in number_labels]

print(f"\n✅ {len(X_arr):,} samples  |  {len(unique_labels)} classes  |  {X_arr.shape[1]} features")
print(f"   Letters : {len(letter_labels)}  ({', '.join(sorted(letter_labels))})")
print(f"   Numbers : {len(number_labels)}  ({', '.join(sorted(number_labels))})")
print(f"   Words   : {len(word_labels)}   ({', '.join(sorted(word_labels)[:10])}{'...' if len(word_labels) > 10 else ''})")
if skipped:
    print(f"   Skipped : {skipped} files")

print("\n📊 Samples per class:")
for lbl in sorted(label_counts):
    count = label_counts[lbl]
    bar   = "█" * min(count // max(len(X_arr) // 600, 1), 45)
    print(f"  {lbl:20s}: {bar} ({count:,})")

low = [l for l, c in label_counts.items() if c < 20]
if low:
    print(f"\n⚠️  Low sample count for: {low}")

# ── Split ─────────────────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X_arr, y_arr, test_size=0.2, random_state=42, stratify=y_arr
)
print(f"\n🔀 Train: {len(X_train):,}  |  Test: {len(X_test):,}")

# ── Train ─────────────────────────────────────────────────────────────────────
n          = len(X_train)
n_trees    = 300 if n > 10_000 else 200
max_depth  = 25  if n > 10_000 else 20

est_time = "1-3 min" if n < 5_000 else "3-8 min" if n < 20_000 else "8-20 min"
print(f"\n🚀 Training Random Forest ({n_trees} trees, max_depth={max_depth})...")
print(f"   Estimated time: {est_time}  (all CPU cores used)")

model = RandomForestClassifier(
    n_estimators      = n_trees,
    max_depth         = max_depth,
    min_samples_split = 4,
    min_samples_leaf  = 2,
    max_features      = "sqrt",
    class_weight      = "balanced",   # handles imbalance between letters and words
    random_state      = 42,
    n_jobs            = -1,
    verbose           = 1,
)
model.fit(X_train, y_train)

# ── Evaluate ──────────────────────────────────────────────────────────────────
y_pred   = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"\n✅ Overall Accuracy: {accuracy * 100:.2f}%")

if accuracy >= 0.93:
    print("🎉 Excellent! Model is ready for production use.")
elif accuracy >= 0.85:
    print("👍 Good accuracy. Real-time detection will work well.")
elif accuracy >= 0.75:
    print("⚠️  Acceptable. Try --max-per-class 1000 for more data.")
else:
    print("❌ Low accuracy. Check dataset quality and class balance.")

# Per-class report
print("\n📋 Classification Report:")
print(classification_report(y_test, y_pred, zero_division=0))

# ── Save ──────────────────────────────────────────────────────────────────────
joblib.dump(model, str(MODEL_PATH))
print(f"🔥 Model saved: {MODEL_PATH}")
print(f"   Classes in model: {list(model.classes_)[:10]}{'...' if len(model.classes_)>10 else ''}")
print(f"\n   Test live:  python src/vision/real_time_sign.py")