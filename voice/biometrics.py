"""
Voice Biometrics — Fingerprints the user's voice using MFCC analysis.
Used to identify "Aansh" vs. strangers.
"""

import os
import numpy as np
from scipy.fftpack import dct
from typing import Optional


class VoiceBiometrics:
    PROFILE_PATH = os.path.expanduser("~/Teni/voice_profile.npy")

    def __init__(self):
        self.enrolled_fingerprint = self._load_profile()

    def _load_profile(self) -> Optional[np.ndarray]:
        if os.path.exists(self.PROFILE_PATH):
            try:
                return np.load(self.PROFILE_PATH)
            except Exception:
                return None
        return None

    def enroll(self, audio_data: np.ndarray, sample_rate: int = 16000):
        """Save a voice fingerprint from an audio snippet."""
        fingerprint = self._calculate_mfcc(audio_data, sample_rate)
        np.save(self.PROFILE_PATH, fingerprint)
        self.enrolled_fingerprint = fingerprint
        print(f"👤 Voice Biometrics: Enrolled fingerprint for Aansh.")

    def verify(self, audio_data: np.ndarray, sample_rate: int = 16000) -> float:
        """Compare audio snippet to the enrolled fingerprint. Returns similarity (0.0 to 1.0)."""
        if self.enrolled_fingerprint is None:
            return 1.0  # Default to authorized if no profile exists yet

        current_fingerprint = self._calculate_mfcc(audio_data, sample_rate)
        
        # Simple Euclidean distance normalized
        dist = np.linalg.norm(self.enrolled_fingerprint - current_fingerprint)
        # Convert distance to similarity (rough heuristic)
        similarity = 1.0 / (1.0 + dist)
        return similarity

    def is_aansh(self, audio_data: np.ndarray, threshold: float = 0.65) -> bool:
        """Check if the audio belongs to Aansh."""
        sim = self.verify(audio_data)
        return sim >= threshold

    def _calculate_mfcc(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """Calculate a simplified MFCC fingerprint with better normalization."""
        audio = audio.astype(np.float32)
        # Power Spectrum
        spectrum = np.abs(np.fft.rfft(audio))**2
        log_spectrum = np.log(spectrum + 1e-10)
        # Discrete Cosine Transform (DCT)
        mfcc = dct(log_spectrum, type=2, axis=-1, norm='ortho')[:20]
        
        # Z-score normalization (Mean subtraction, standard deviation division)
        # This makes the fingerprint robust to volume and noise
        mean = np.mean(mfcc)
        std = np.std(mfcc) + 1e-6
        mfcc = (mfcc - mean) / std
        
        return mfcc

