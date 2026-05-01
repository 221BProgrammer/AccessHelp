# src/vision/hand_tracker.py
import cv2
import mediapipe as mp


class HandTracker:
    """
    Tracks up to two hands using MediaPipe.

    get_hand_landmarks() returns landmarks for ALL detected hands,
    not just the first one, so two-handed signs are fully supported.
    """

    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,                  # supports two hands
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.mp_draw = mp.solutions.drawing_utils

    def get_hand_landmarks(self, frame):
        """
        Detect hand landmarks in a frame.

        Returns
        -------
        landmarks_list : list of [x, y, z] points, or None
            If one hand detected  → 21 points  (63 values when flattened)
            If two hands detected → 42 points  (126 values when flattened)
            Returns None if no hand is detected.
        frame : numpy.ndarray
            The frame with landmarks drawn on it for all detected hands.

        BUG FIXES
        ---------
        1. Frame validity check — None/empty frames no longer crash cvtColor.
        2. ALL detected hands are drawn and returned, not just hand[0].
        3. Two-hand landmarks are concatenated so downstream normalize_landmarks
           and the model receive the full picture.
        """
        # Fix 1: guard against None / empty frame
        if frame is None or frame.size == 0:
            return None, frame

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(img_rgb)

        landmarks_list = []

        if results.multi_hand_landmarks:
            # Fix 2 + 3: iterate ALL detected hands
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw this hand's skeleton on the frame
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
                )
                # Append all 21 landmark points for this hand
                for lm in hand_landmarks.landmark:
                    landmarks_list.append([lm.x, lm.y, lm.z])

        if landmarks_list:
            return landmarks_list, frame
        return None, frame