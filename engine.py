"""
SvaanVox Engine v2 — Bark AI wrapper for cinematic audiobook generation.
========================================================================

Handles model preloading, intelligent text splitting (respecting Bark's
token limit), sequential segment generation with emotion-aware audio cues,
SFX insertion, per-part BGM mixing, and final WAV export via scipy.

Key design principle: Bark ONLY receives the `bark_text` field from the
parser, which contains clean spoken dialogue + injected audio cues.
Character names, stage directions, and other metadata are fully stripped.
"""

import os
import re
import uuid
import datetime
import numpy as np
from scipy.io.wavfile import write as write_wav, read as read_wav

# ---------------------------------------------------------------------------
# PyTorch compatibility patch (works around weights_only restriction)
# ---------------------------------------------------------------------------
try:
    import torch
    _original_load = torch.load
    def _safe_load(*args, **kwargs):
        kwargs['weights_only'] = False
        return _original_load(*args, **kwargs)
    torch.load = _safe_load
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Bark imports
# ---------------------------------------------------------------------------
try:
    from bark import generate_audio, preload_models, SAMPLE_RATE
    BARK_AVAILABLE = True
except ImportError:
    BARK_AVAILABLE = False
    SAMPLE_RATE = 24_000

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_SEGMENT_CHARS = 220          # Bark's safe token limit (~14s of audio)
OUTPUT_DIR  = os.path.join(os.path.dirname(__file__), "static", "outputs")
SFX_DIR     = os.path.join(os.path.dirname(__file__), "static", "sfx")
UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "static", "uploads")

# Silence gap durations (seconds)
GAP_BETWEEN_SEGMENTS = 0.3
GAP_BETWEEN_PARTS    = 1.0
BGM_VOLUME_DB        = -12       # background music volume reduction


# ---------------------------------------------------------------------------
# Model initialisation
# ---------------------------------------------------------------------------

def init_models() -> None:
    """Pre-download and cache Bark model weights (call once at startup)."""
    if BARK_AVAILABLE:
        preload_models()
        print("[SvaanVox] Bark models loaded ✓")
    else:
        print("[SvaanVox] ⚠  Bark not installed – running in DEMO mode.")


# ---------------------------------------------------------------------------
# Text splitting — respects Bark's ~220 char limit
# ---------------------------------------------------------------------------

def split_text(text: str, max_chars: int = MAX_SEGMENT_CHARS) -> list[str]:
    """Split *text* into ≤ max_chars segments on sentence boundaries.

    Bark can only process ~14 seconds of audio per call, which roughly
    corresponds to ~220 characters.  This function splits on sentence
    endings (. ! ?) first, then on commas if a sentence is still too long.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    segments: list[str] = []
    current = ""

    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_chars:
            current = f"{current} {sent}".strip() if current else sent
        else:
            if current:
                segments.append(current)
            if len(sent) > max_chars:
                segments.extend(_split_long_sentence(sent, max_chars))
                current = ""
            else:
                current = sent

    if current:
        segments.append(current)
    return segments


def _split_long_sentence(sentence: str, max_chars: int) -> list[str]:
    """Break an over-long sentence on commas, then hard-chop if needed."""
    parts = sentence.split(",")
    segments: list[str] = []
    current = ""
    for part in parts:
        part = part.strip()
        if len(current) + len(part) + 2 <= max_chars:
            current = f"{current}, {part}".strip(", ") if current else part
        else:
            if current:
                segments.append(current)
            current = part
    if current:
        segments.append(current)

    # Hard chop anything still over the limit
    final: list[str] = []
    for seg in segments:
        while len(seg) > max_chars:
            final.append(seg[:max_chars])
            seg = seg[max_chars:]
        if seg:
            final.append(seg)
    return final


# ---------------------------------------------------------------------------
# Audio helpers
# ---------------------------------------------------------------------------

def _silence(duration_s: float) -> np.ndarray:
    """Generate silence of the given duration."""
    return np.zeros(int(SAMPLE_RATE * duration_s), dtype=np.float32)


def _load_wav(path: str) -> np.ndarray:
    """Load a WAV file and return it as float32 mono at SAMPLE_RATE."""
    sr, data = read_wav(path)
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    if data.ndim > 1:
        data = data.mean(axis=1)
    if sr != SAMPLE_RATE:
        indices = np.linspace(0, len(data) - 1, int(len(data) * SAMPLE_RATE / sr))
        data = np.interp(indices, np.arange(len(data)), data).astype(np.float32)
    return data


def _mix_bgm(voice_audio: np.ndarray, bgm_audio: np.ndarray,
             volume_db: float = BGM_VOLUME_DB) -> np.ndarray:
    """Mix background music under voice audio with fade in/out."""
    target_len = len(voice_audio)
    volume_scale = 10 ** (volume_db / 20)

    if len(bgm_audio) == 0:
        return voice_audio
    loops_needed = (target_len // len(bgm_audio)) + 1
    bgm_looped = np.tile(bgm_audio, loops_needed)[:target_len]
    bgm_looped *= volume_scale

    fade_in  = min(int(SAMPLE_RATE * 1.0), target_len // 4)
    fade_out = min(int(SAMPLE_RATE * 2.0), target_len // 4)
    bgm_looped[:fade_in] *= np.linspace(0, 1, fade_in)
    bgm_looped[-fade_out:] *= np.linspace(1, 0, fade_out)

    return voice_audio + bgm_looped


def _bark_generate(text: str, voice_preset: str, seg_idx: int = 0) -> np.ndarray:
    """Generate speech for a SANITISED text segment via Bark AI.

    IMPORTANT: This function receives ONLY the bark_text (clean dialogue
    + emotion cues).  Character names and stage directions have already
    been stripped by the parser.
    """
    if BARK_AVAILABLE:
        return generate_audio(text, history_prompt=voice_preset)
    else:
        # DEMO mode — generate a variable-pitch sine wave so each
        # character sounds distinct (not production quality!)
        duration = max(1.0, len(text) / 40)
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration), dtype=np.float32)
        freq = 300 + (hash(voice_preset) % 400) + (seg_idx * 30)
        return (0.4 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _load_sfx(sfx_name: str) -> np.ndarray:
    """Load an SFX file from static/sfx/.

    Falls back to a generic short beep if the file doesn't exist.
    """
    # Try exact match first, then try common variants
    for candidate in [sfx_name, sfx_name.split()[0], sfx_name.replace(" ", "_")]:
        sfx_path = os.path.join(SFX_DIR, f"{candidate}.wav")
        if os.path.exists(sfx_path):
            return _load_wav(sfx_path)

    # Fallback: generic short beep
    t = np.linspace(0, 0.5, int(SAMPLE_RATE * 0.5), dtype=np.float32)
    return (0.3 * np.sin(2 * np.pi * 600 * t)).astype(np.float32)


# ---------------------------------------------------------------------------
# Simple TTS generation (single voice)
# ---------------------------------------------------------------------------

def generate_speech(
    text: str,
    voice_preset: str = "v2/en_speaker_6",
    mode: str = "standard",
) -> dict:
    """Generate a WAV file from text using a single voice preset."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    segments = split_text(text)
    audio_parts: list[np.ndarray] = []

    for i, segment in enumerate(segments):
        print(f"[SvaanVox] Generating segment {i + 1}/{len(segments)} …")
        audio_parts.append(_bark_generate(segment, voice_preset, i))

    full_audio = np.concatenate(audio_parts)
    return _save_wav(full_audio, mode, voice_preset)


# ---------------------------------------------------------------------------
# Audiobook generation (multi-part, multi-voice, SFX, BGM)
# ---------------------------------------------------------------------------

def generate_audiobook(
    parts: list[dict],
    bgm_map: dict[str, str] | None = None,
    enable_sfx: bool = True,
) -> dict:
    """Generate a full audiobook WAV from parsed cinematic script parts.

    The generation loop processes the parser's output as follows:

    1. For each part (chapter/scene), iterate through segments.
    2. SFX segments → load from static/sfx/ and insert.
    3. Dialogue segments → use the `bark_text` field (which contains
       ONLY the emotion-cued spoken text, completely free of character
       names and stage directions) and the assigned `voice` preset.
    4. Narrator segments → same as dialogue but with the narrator voice.
    5. Each segment's audio is concatenated with short silence gaps.
    6. Per-part BGM is mixed underneath if provided.
    7. All parts are concatenated with longer gaps between them.

    Args:
        parts:      list of { name, segments: [{ type, bark_text, voice, ... }] }
        bgm_map:    { part_index_str: bgm_file_path } — optional per-part BGM
        enable_sfx: whether to insert SFX segments

    Returns:
        dict with filename, url, duration_s, created.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    all_parts_audio: list[np.ndarray] = []

    for part_idx, part in enumerate(parts):
        print(f"\n[SvaanVox] ══ Part {part_idx + 1}: {part.get('name', 'Untitled')} ══")
        part_audio_segments: list[np.ndarray] = []

        for seg_idx, seg in enumerate(part.get("segments", [])):
            seg_type = seg.get("type", "narrator")

            # ── SFX insertion ────────────────────────────────────
            if seg_type == "sfx":
                if enable_sfx:
                    sfx_name = seg.get("text", "").strip()
                    print(f"  🔊 [SFX] {sfx_name}")
                    part_audio_segments.append(_load_sfx(sfx_name))
                    part_audio_segments.append(_silence(0.2))
                continue

            # ── Dialogue / Narrator — the core TTS loop ──────────
            # CRITICAL: We use "bark_text" which is the sanitised,
            #           emotion-cued version of the dialogue.
            #           Character names and stage directions are GONE.
            bark_text = seg.get("bark_text", seg.get("text", "")).strip()
            voice     = seg.get("voice", "v2/en_speaker_7")
            character = seg.get("character", "NARRATOR")

            if not bark_text:
                continue

            # Log what we're generating
            if seg_type == "dialogue":
                print(f"  🎤 [{character}] → Bark receives: \"{bark_text[:70]}{'…' if len(bark_text) > 70 else ''}\"")
            else:
                print(f"  📜 [NARRATOR] {bark_text[:70]}{'…' if len(bark_text) > 70 else ''}")

            # Split into Bark-safe chunks and generate audio
            sub_segments = split_text(bark_text)
            for sub_i, sub_text in enumerate(sub_segments):
                audio = _bark_generate(sub_text, voice, seg_idx * 10 + sub_i)
                part_audio_segments.append(audio)

            # Small gap between segments
            part_audio_segments.append(_silence(GAP_BETWEEN_SEGMENTS))

        if not part_audio_segments:
            continue

        # Concatenate this part's audio
        part_audio = np.concatenate(part_audio_segments)

        # ── Mix BGM if provided ──────────────────────────────────
        bgm_map = bgm_map or {}
        bgm_path = bgm_map.get(str(part_idx), "")
        if bgm_path and os.path.exists(bgm_path):
            print(f"  🎵 [BGM] Mixing background music for Part {part_idx + 1}")
            bgm_audio = _load_wav(bgm_path)
            has_title = any(s.get("type") == "title" for s in part.get("segments", []))
            vol = BGM_VOLUME_DB + 4 if has_title else BGM_VOLUME_DB
            part_audio = _mix_bgm(part_audio, bgm_audio, volume_db=vol)

        all_parts_audio.append(part_audio)
        all_parts_audio.append(_silence(GAP_BETWEEN_PARTS))

    if not all_parts_audio:
        raise ValueError("No audio segments to process.")

    full_audio = np.concatenate(all_parts_audio)
    return _save_wav(full_audio, "audiobook", "multi-voice")


# ---------------------------------------------------------------------------
# Save helper
# ---------------------------------------------------------------------------

def _save_wav(audio: np.ndarray, mode: str, voice: str) -> dict:
    """Normalise, save as 16-bit WAV, and return metadata."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    short_id = uuid.uuid4().hex[:6]
    label = mode.replace(" ", "_")
    filename = f"svaanvox_{label}_{timestamp}_{short_id}.wav"
    filepath = os.path.join(OUTPUT_DIR, filename)

    # Normalise to prevent clipping
    peak = np.max(np.abs(audio)) + 1e-9
    audio_int16 = np.int16(audio / peak * 32767)
    write_wav(filepath, SAMPLE_RATE, audio_int16)

    duration_s = round(len(audio) / SAMPLE_RATE, 2)
    print(f"[SvaanVox] ✅ Saved {filename} ({duration_s}s)")

    return {
        "filename": filename,
        "url": f"/static/outputs/{filename}",
        "duration_s": duration_s,
        "created": datetime.datetime.now().isoformat(),
        "voice": voice,
        "mode": mode,
    }
