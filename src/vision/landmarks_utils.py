# src/vision/landmarks_utils.py
import numpy as np

LANDMARKS_ONE_HAND  = 21    # 21 points × 3 = 63 features
LANDMARKS_TWO_HANDS = 42    # 42 points × 3 = 126 features


def normalize_landmarks(landmarks, pad_to_two_hands: bool = True) -> np.ndarray:
    """
    Normalise a single frame of raw landmark data from HandTracker.

    Returns a 1-D array of 126 features (padded if one hand).
    This is used frame-by-frame during both recording and live detection.
    """
    lm = np.array(landmarks, dtype=np.float32)

    # Translate so wrist (landmark 0) is the origin
    base = lm[0].copy()
    lm   = lm - base

    # Scale to [-1, 1]
    max_val = np.max(np.abs(lm))
    if max_val != 0:
        lm = lm / max_val

    flat = lm.flatten()

    # Pad single-hand to two-hand length for consistent shape
    if pad_to_two_hands and len(flat) == LANDMARKS_ONE_HAND * 3:
        flat = np.concatenate(
            [flat, np.zeros(LANDMARKS_ONE_HAND * 3, dtype=np.float32)]
        )

    return flat


def aggregate_sequence(frames: np.ndarray) -> np.ndarray:
    """
    Convert a variable-length sequence of landmark frames into a single
    fixed-size feature vector suitable for the classifier.

    This is the KEY function that lets us support unlimited recording time.
    Instead of requiring exactly N frames, we summarise the entire sequence
    using statistical descriptors per feature:
        mean, std, min, max  →  4 values per feature

    So for 126 landmark features:
        output size = 126 × 4 = 504 features  (always, regardless of length)

    Parameters
    ----------
    frames : np.ndarray, shape (num_frames, 126)
        Stack of normalised landmark vectors from a recording session.

    Returns
    -------
    np.ndarray, shape (504,)
        Fixed-size feature vector for the classifier.
    """
    if frames.ndim == 1:
        # Single frame passed — wrap it
        frames = frames.reshape(1, -1)

    mean = np.mean(frames, axis=0)
    std  = np.std(frames,  axis=0)
    mn   = np.min(frames,  axis=0)
    mx   = np.max(frames,  axis=0)

    return np.concatenate([mean, std, mn, mx]).astype(np.float32)


def aggregate_live_window(window: list) -> np.ndarray:
    """
    Convenience wrapper for live detection.
    Takes a Python list of recent normalised landmark frames
    and returns the aggregated feature vector.

    Parameters
    ----------
    window : list of np.ndarray
        Recent frames collected in the live detection loop.

    Returns
    -------
    np.ndarray, shape (504,)
    """
    return aggregate_sequence(np.array(window, dtype=np.float32))