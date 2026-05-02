"""
Gesture Control — Hand gesture recognition using OpenCV + basic contour analysis.
Uses a simple approach that works with any version of dependencies.
Runs on a background thread, watches the webcam for hand gestures.
Toggle on/off with 'gestures' command.
"""

import threading
import cv2
import numpy as np
from typing import Callable, Optional


class GestureController:
    """
    Detects simple hand gestures via webcam using contour analysis:
    - Open palm (5 fingers)  → "stop"
    - Fist (0 fingers)       → "confirm"
    - Thumbs up (1 finger)   → "approve"
    - Peace sign (2 fingers) → "next"
    """

    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self._running = False
        self._thread = None
        self.last_gesture = None
        self._cooldown = 0  # prevent spamming

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._detect_loop, daemon=True)
        self._thread.start()
        print("✋ Gesture control active — show your hand to the camera.")

    def stop(self):
        self._running = False

    def _detect_loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("✋ Gesture error: Cannot access webcam.")
            self._running = False
            return

        while self._running:
            ret, frame = cap.read()
            if not ret:
                continue

            frame = cv2.flip(frame, 1)

            # Region of interest (right side of frame)
            h, w = frame.shape[:2]
            roi = frame[50:h-50, w//2:w-20]

            # Skin detection in HSV
            hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            lower_skin = np.array([0, 30, 60], dtype=np.uint8)
            upper_skin = np.array([20, 150, 255], dtype=np.uint8)
            mask = cv2.inRange(hsv, lower_skin, upper_skin)

            # Clean up mask
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.dilate(mask, kernel, iterations=2)
            mask = cv2.erode(mask, kernel, iterations=2)
            mask = cv2.GaussianBlur(mask, (5, 5), 0)

            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            if contours:
                max_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(max_contour)

                if area > 5000:  # Meaningful hand detection
                    hull = cv2.convexHull(max_contour, returnPoints=False)
                    try:
                        defects = cv2.convexityDefects(max_contour, hull)
                    except Exception:
                        defects = None

                    finger_count = 0
                    if defects is not None:
                        for i in range(defects.shape[0]):
                            s, e, f, d = defects[i, 0]
                            start = tuple(max_contour[s][0])
                            end = tuple(max_contour[e][0])
                            far = tuple(max_contour[f][0])

                            # Triangle sides
                            a = np.linalg.norm(np.array(start) - np.array(end))
                            b = np.linalg.norm(np.array(start) - np.array(far))
                            c = np.linalg.norm(np.array(end) - np.array(far))

                            # Angle at the defect
                            angle = np.arccos((b**2 + c**2 - a**2) / (2*b*c + 1e-5))
                            if angle <= np.pi / 2 and d > 5000:
                                finger_count += 1

                    finger_count = min(finger_count + 1, 5)  # +1 for the thumb approximation
                    gesture = self._classify(finger_count)

                    if self._cooldown <= 0 and gesture and gesture != self.last_gesture:
                        self.last_gesture = gesture
                        self._cooldown = 30  # ~1 second cooldown at 30fps
                        print(f"✋ Gesture: {gesture} ({finger_count} fingers)")
                        if self.callback:
                            self.callback(gesture)

            if self._cooldown > 0:
                self._cooldown -= 1

            cv2.waitKey(33)  # ~30fps

        cap.release()

    def _classify(self, fingers: int) -> Optional[str]:
        if fingers <= 1:
            return "confirm"
        elif fingers == 2:
            return "next"
        elif fingers == 3:
            return "approve"
        elif fingers >= 4:
            return "stop"
        return None
