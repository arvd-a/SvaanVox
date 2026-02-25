"""
SvaanVox Script Parser v2 — Cinematic Screenplay Format
========================================================

Parses DOCX files written in the cinematic format:

    CHARACTER NAME  (emotion, stage direction) : "Spoken Dialogue"
    [SFX — description]
    Plain narration text

Extracts structured segments for the Bark AI engine, completely
stripping stage directions and character metadata so the TTS model
only ever receives clean, speakable text.
"""

import re
from docx import Document


# ---------------------------------------------------------------------------
# Voice Dictionary — assign specific Bark presets to known characters
# ---------------------------------------------------------------------------
# Add or modify entries here to match your screenplay's cast.

VOICE_DICT: dict[str, str] = {
    "SANJAY":    "v2/en_speaker_2",
    "ATHARV":    "v2/en_speaker_5",
    "DEVAJ":     "v2/en_speaker_8",
    "AARADHYA":  "v2/en_speaker_0",
    "AADHYAN":   "v2/en_speaker_3",
    "NARRATOR":  "v2/en_speaker_9",
}

# Fallback voice for any character not listed above
DEFAULT_VOICE = "v2/en_speaker_7"
NARRATOR_VOICE = VOICE_DICT.get("NARRATOR", "v2/en_speaker_9")


# ---------------------------------------------------------------------------
# Emotion → Bark Audio Cue Translation
# ---------------------------------------------------------------------------
# If the (emotion/stage-direction) block contains any of these keywords,
# the corresponding Bark text cue is *prepended* to the spoken dialogue.
# This guides Bark to generate the audio with the right emotional colour.

EMOTION_CUE_MAP: dict[str, str] = {
    # ---- Laughter & amusement ----
    "laugh":     "[laughs]",
    "chuckle":   "[laughs]",
    "amused":    "[laughs]",
    "giggle":    "[laughs]",
    # ---- Sighing ----
    "sigh":      "[sighs]",
    "exhale":    "[sighs]",
    "resigned":  "[sighs]",
    # ---- Crying & sadness ----
    "cry":       "[crying]",
    "sob":       "[crying]",
    "tear":      "[crying]",
    "weep":      "[crying]",
    # ---- Anger & shouting ----
    "angry":     "...",       # Bark uses "..." for tense pauses
    "shout":     "...",
    "yell":      "...",
    "furious":   "...",
    # ---- Whispering ----
    "whisper":   "[whispers]",
    "quiet":     "[whispers]",
    "hushed":    "[whispers]",
    # ---- Gasping / surprise ----
    "gasp":      "[gasps]",
    "shock":     "[gasps]",
    "surprise":  "[gasps]",
    # ---- Hesitation ----
    "hesitant":  "...",
    "nervous":   "...",
    "stammer":   "...",
    "stutter":   "...",
    # ---- Excitement / eagerness ----
    "eager":     "♪",         # Bark uses ♪ for an uplifting cadence
    "excited":   "♪",
}


# ---------------------------------------------------------------------------
# Regex patterns for the cinematic screenplay format
# ---------------------------------------------------------------------------

# Main dialogue pattern:
#   CHARACTER NAME  (emotion, stage direction) : "Spoken Dialogue"
# Also handles:
#   CHARACTER NAME : "Dialogue"          (no emotion block)
#   CHARACTER NAME  (tags) : Dialogue    (no quotes)
RE_DIALOGUE = re.compile(
    r"""
    ^                                     # start of line
    ([A-Z][A-Z\s/]+?)                     # 1: CHARACTER NAME (all-caps, may include / for split chars)
    \s*                                   # optional whitespace
    (?:\(([^)]*)\))?                       # 2: optional (emotion, stage direction) in parens
    \s*                                   # optional whitespace
    :\s*                                  # colon separator
    ["\u201c]?                             # optional opening quote
    (.+?)                                 # 3: the spoken dialogue text
    ["\u201d]?\s*$                         # optional closing quote + end of line
    """,
    re.VERBOSE,
)

# SFX pattern: [SFX — description] or [SFX: description] or just [description]
RE_SFX = re.compile(
    r"""
    ^\[                                   # opening bracket
    (?:SFX\s*[:\u2014\-—]\s*)?            # optional "SFX —" or "SFX:" prefix
    (.+?)                                 # 1: the SFX description
    \]\s*$                                # closing bracket
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Part / Chapter / Scene headers
RE_PART_HEADER = re.compile(
    r'^(?:PART|CHAPTER|SCENE|ACT|BOOK)\s+\w+', re.IGNORECASE
)

# Horizontal separators (---, ***, ###)
RE_SEPARATOR = re.compile(r'^[-*#]{3,}$')


# ---------------------------------------------------------------------------
# DOCX text extraction
# ---------------------------------------------------------------------------

def parse_docx(file_path: str) -> str:
    """Extract all text from a .docx file, preserving line structure."""
    doc = Document(file_path)
    lines = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def parse_script(text: str) -> dict:
    """Parse a cinematic screenplay into structured parts with segments.

    Returns:
        {
          "parts": [
            {
              "name": "Chapter 1",
              "segments": [
                {
                  "type":      "dialogue" | "sfx" | "narrator",
                  "character": "ATHARV" | None,
                  "text":      "Clean spoken text for Bark",
                  "emotion":   "hesitant, eager" | None,
                  "voice":     "v2/en_speaker_5",
                  "bark_text": "... Dr. Sanjay?"
                },
                ...
              ]
            }
          ]
        }
    """
    lines = text.strip().split("\n")
    parts: list[dict] = []
    current_part_name = "Introduction"
    current_segments: list[dict] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # ── Part / Chapter / Scene boundary ──────────────────────
        if RE_PART_HEADER.match(line) or RE_SEPARATOR.match(line):
            if current_segments:
                parts.append({"name": current_part_name, "segments": current_segments})
                current_segments = []
            current_part_name = line if RE_PART_HEADER.match(line) else f"Part {len(parts) + 2}"
            continue

        # ── SFX block: [SFX — thunder] or [door slam] ───────────
        sfx_match = RE_SFX.match(line)
        if sfx_match:
            sfx_desc = sfx_match.group(1).strip().lower()
            current_segments.append({
                "type":      "sfx",
                "character": None,
                "text":      sfx_desc,
                "emotion":   None,
                "voice":     None,
                "bark_text": None,
            })
            continue

        # ── Character dialogue ───────────────────────────────────
        dial_match = RE_DIALOGUE.match(line)
        if dial_match:
            raw_name   = dial_match.group(1).strip()
            raw_tags   = dial_match.group(2) or ""      # emotion/stage block
            raw_text   = dial_match.group(3).strip()

            # Handle split characters like SANJAY/AADHYAN → take first name
            char_name = raw_name.split("/")[0].strip()

            # Look up voice from the voice dictionary
            voice = VOICE_DICT.get(char_name.upper(), DEFAULT_VOICE)

            # Clean emotion tags string
            emotion_str = raw_tags.strip() if raw_tags else None

            # Translate emotions to Bark audio cues
            bark_text = _inject_emotion_cues(raw_text, raw_tags)

            current_segments.append({
                "type":      "dialogue",
                "character": char_name,
                "text":      raw_text,       # original clean dialogue
                "emotion":   emotion_str,
                "voice":     voice,
                "bark_text": bark_text,       # emotion-injected text for Bark
            })
            continue

        # ── Narration (everything else) ──────────────────────────
        current_segments.append({
            "type":      "narrator",
            "character": None,
            "text":      line,
            "emotion":   None,
            "voice":     NARRATOR_VOICE,
            "bark_text": line,               # narration goes to Bark as-is
        })

    # Don't forget the last part
    if current_segments:
        parts.append({"name": current_part_name, "segments": current_segments})

    return {"parts": parts}


# ---------------------------------------------------------------------------
# Emotion → Bark cue injection (internal helper)
# ---------------------------------------------------------------------------

def _inject_emotion_cues(dialogue: str, emotion_block: str) -> str:
    """Scan the emotion/stage-direction block for keywords and prepend
    the corresponding Bark audio cues to the dialogue string.

    Example:
        dialogue     = "Dr. Sanjay?"
        emotion_block = "hesitant, respectful — eager"
        → returns:  "... Dr. Sanjay?"

    Multiple matching cues are prepended in order, deduplicated.
    """
    if not emotion_block:
        return dialogue

    # Normalise the block: lowercase, replace separators with spaces
    block_lower = emotion_block.lower().replace("—", " ").replace("-", " ").replace(",", " ")

    # Collect unique cues to prepend
    cues_to_prepend: list[str] = []
    seen_cues: set[str] = set()

    for keyword, cue in EMOTION_CUE_MAP.items():
        if keyword in block_lower and cue not in seen_cues:
            cues_to_prepend.append(cue)
            seen_cues.add(cue)

    if not cues_to_prepend:
        return dialogue

    # Build the final string: cues + space + dialogue
    cue_prefix = " ".join(cues_to_prepend)
    return f"{cue_prefix} {dialogue}"


# ---------------------------------------------------------------------------
# Quick self-test (run with: python script_parser.py)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_script = """
CHAPTER 1 — The Signal

[SFX — thunder rumbling in the distance]

The lab was dark. Only the blue glow of the monitors kept the room alive.

ATHARV  (hesitant, respectful — eager) : "Dr. Sanjay?"

SANJAY  (calm, measured) : "Come in, Atharv. I've been expecting you."

[SFX — door creaking open]

SANJAY/AADHYAN  (laughing, amused) : "You should see your face right now."

DEVAJ  (whispering, nervous) : "Something doesn't feel right."

AARADHYA  (sigh, resigned) : "We've been through this before."
    """

    result = parse_script(test_script)
    print("=" * 60)
    for part in result["parts"]:
        print(f"\n📖 {part['name']}")
        for seg in part["segments"]:
            if seg["type"] == "sfx":
                print(f"   🔊 [SFX] {seg['text']}")
            elif seg["type"] == "dialogue":
                print(f"   🎤 {seg['character']} ({seg['emotion']}) → voice: {seg['voice']}")
                print(f"      Original:  \"{seg['text']}\"")
                print(f"      Bark gets: \"{seg['bark_text']}\"")
            else:
                print(f"   📜 [NARRATOR] {seg['text']}")
