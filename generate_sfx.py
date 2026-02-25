"""
SvaanVox SFX Generator — Synthesizes basic sound effect WAV files.

Run this once to populate static/sfx/ with copyright-free, numpy-generated
sound effects that can be inserted into audiobook productions.
"""

import os
import numpy as np
from scipy.io.wavfile import write as write_wav

SAMPLE_RATE = 24_000
SFX_DIR = os.path.join(os.path.dirname(__file__), "static", "sfx")


def _fade(audio: np.ndarray, fade_ms: int = 50) -> np.ndarray:
    """Apply fade-in and fade-out to avoid clicks."""
    fade_samples = int(SAMPLE_RATE * fade_ms / 1000)
    if len(audio) < fade_samples * 2:
        return audio
    audio = audio.copy()
    audio[:fade_samples] *= np.linspace(0, 1, fade_samples)
    audio[-fade_samples:] *= np.linspace(1, 0, fade_samples)
    return audio


def _save(name: str, audio: np.ndarray) -> None:
    """Normalise to int16 and save as WAV."""
    audio = _fade(audio)
    peak = np.max(np.abs(audio)) + 1e-9
    audio_int16 = np.int16(audio / peak * 32767)
    write_wav(os.path.join(SFX_DIR, f"{name}.wav"), SAMPLE_RATE, audio_int16)
    print(f"  ✓ {name}.wav")


# ---------------------------------------------------------------------------
# SFX generators
# ---------------------------------------------------------------------------

def gen_thunder() -> np.ndarray:
    """Low rumble with noise burst."""
    dur = 2.5
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), dtype=np.float32)
    rumble = 0.6 * np.sin(2 * np.pi * 40 * t) * np.exp(-t / 1.5)
    noise = 0.4 * np.random.randn(len(t)).astype(np.float32) * np.exp(-t / 0.8)
    return rumble + noise


def gen_rain() -> np.ndarray:
    """Continuous white noise with gentle filtering."""
    dur = 3.0
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), dtype=np.float32)
    noise = 0.3 * np.random.randn(len(t)).astype(np.float32)
    # Simple low-pass via rolling mean
    kernel = np.ones(20) / 20
    return np.convolve(noise, kernel, mode="same").astype(np.float32)


def gen_door() -> np.ndarray:
    """Short thud + creak."""
    dur = 0.8
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), dtype=np.float32)
    thud = 0.8 * np.sin(2 * np.pi * 80 * t) * np.exp(-t / 0.1)
    creak = 0.3 * np.sin(2 * np.pi * 600 * t + 5 * np.sin(2 * np.pi * 3 * t)) * np.exp(-t / 0.3)
    return thud + creak


def gen_footsteps() -> np.ndarray:
    """Rhythmic taps."""
    dur = 2.0
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), dtype=np.float32)
    audio = np.zeros_like(t)
    for step_time in np.arange(0, dur, 0.4):
        step = np.exp(-((t - step_time) ** 2) / 0.002) * 0.7
        step *= np.sin(2 * np.pi * 200 * t)
        audio += step
    return audio


def gen_wind() -> np.ndarray:
    """Whooshing noise."""
    dur = 3.0
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), dtype=np.float32)
    noise = np.random.randn(len(t)).astype(np.float32)
    mod = 0.3 * (1 + 0.5 * np.sin(2 * np.pi * 0.5 * t))
    kernel = np.ones(40) / 40
    filtered = np.convolve(noise * mod, kernel, mode="same").astype(np.float32)
    return filtered


def gen_applause() -> np.ndarray:
    """Crowd clapping — layered noise bursts."""
    dur = 2.5
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), dtype=np.float32)
    noise = 0.4 * np.random.randn(len(t)).astype(np.float32)
    envelope = 0.5 + 0.5 * np.sin(2 * np.pi * 4 * t)
    return noise * envelope


def gen_bell() -> np.ndarray:
    """Single bell chime."""
    dur = 2.0
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), dtype=np.float32)
    fundamental = 0.5 * np.sin(2 * np.pi * 800 * t)
    overtone1 = 0.3 * np.sin(2 * np.pi * 1600 * t)
    overtone2 = 0.15 * np.sin(2 * np.pi * 2400 * t)
    decay = np.exp(-t / 0.8)
    return (fundamental + overtone1 + overtone2) * decay


def gen_heartbeat() -> np.ndarray:
    """Rhythmic double-pulse heartbeat."""
    dur = 3.0
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), dtype=np.float32)
    audio = np.zeros_like(t)
    for beat in np.arange(0, dur, 0.8):
        for offset in [0, 0.15]:
            pulse_t = beat + offset
            pulse = np.exp(-((t - pulse_t) ** 2) / 0.003) * 0.8
            pulse *= np.sin(2 * np.pi * 50 * t)
            audio += pulse
    return audio


def gen_silence() -> np.ndarray:
    """1 second of silence (used as a spacer)."""
    return np.zeros(SAMPLE_RATE, dtype=np.float32)


def gen_whoosh() -> np.ndarray:
    """Quick swoosh for transitions."""
    dur = 0.6
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), dtype=np.float32)
    freq_sweep = np.sin(2 * np.pi * (200 + 2000 * t / dur) * t)
    envelope = np.sin(np.pi * t / dur)
    return (0.5 * freq_sweep * envelope).astype(np.float32)


def gen_suspense() -> np.ndarray:
    """Low drone for tense moments."""
    dur = 3.0
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), dtype=np.float32)
    drone = 0.4 * np.sin(2 * np.pi * 55 * t)
    wobble = 0.2 * np.sin(2 * np.pi * 58 * t)
    noise = 0.1 * np.random.randn(len(t)).astype(np.float32) * np.exp(-t / 2)
    return (drone + wobble + noise).astype(np.float32)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
SFX_GENERATORS = {
    "thunder":    gen_thunder,
    "rain":       gen_rain,
    "door":       gen_door,
    "footsteps":  gen_footsteps,
    "wind":       gen_wind,
    "applause":   gen_applause,
    "bell":       gen_bell,
    "heartbeat":  gen_heartbeat,
    "silence":    gen_silence,
    "whoosh":     gen_whoosh,
    "suspense":   gen_suspense,
}


def generate_all_sfx() -> None:
    """Generate all SFX WAV files into static/sfx/."""
    os.makedirs(SFX_DIR, exist_ok=True)
    print("[SvaanVox] Generating SFX library…")
    for name, gen_fn in SFX_GENERATORS.items():
        audio = gen_fn()
        _save(name, audio)
    print(f"[SvaanVox] {len(SFX_GENERATORS)} SFX files ready ✓")


if __name__ == "__main__":
    generate_all_sfx()
