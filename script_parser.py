"""
SvaanVox Script Parser — Intelligent audiobook script analysis.

Parses DOCX files, divides text into Parts/Chapters, classifies lines
(title, dialogue, narration, SFX), detects character gender & emotion,
and auto-assigns Bark voice presets.
"""

import re
from docx import Document


# ---------------------------------------------------------------------------
# Gender detection — common name lists (expandable)
# ---------------------------------------------------------------------------
FEMALE_NAMES = {
    "alice", "anna", "bella", "cara", "clara", "diana", "elena", "emma",
    "eva", "fiona", "grace", "hannah", "isla", "jane", "julia", "kate",
    "laura", "lily", "luna", "maria", "mary", "maya", "mia", "nora",
    "olivia", "rose", "sara", "sarah", "sophia", "victoria", "queen",
    "princess", "mother", "mom", "grandmother", "grandma", "sister",
    "aunt", "wife", "girl", "woman", "lady", "maiden", "duchess",
    "empress", "goddess", "priestess", "heroine", "witch", "she",
}

MALE_NAMES = {
    "adam", "alex", "arthur", "ben", "blake", "charles", "daniel", "david",
    "derek", "edward", "felix", "george", "henry", "jack", "james", "john",
    "leo", "mark", "max", "michael", "oliver", "peter", "robert", "sam",
    "thomas", "william", "king", "prince", "father", "dad", "grandfather",
    "grandpa", "brother", "uncle", "husband", "boy", "man", "lord", "duke",
    "emperor", "god", "priest", "hero", "knight", "wizard", "he",
}

# ---------------------------------------------------------------------------
# Emotion keywords
# ---------------------------------------------------------------------------
EMOTION_MAP = {
    "angry":    ["angry", "furious", "rage", "yelled", "screamed", "shouted", "roared", "slammed", "fury"],
    "sad":      ["sad", "cried", "wept", "tears", "sobbed", "mourned", "grief", "sorrow", "whispered sadly"],
    "happy":    ["happy", "laughed", "smiled", "joyful", "cheerful", "grinned", "excited", "delighted"],
    "scared":   ["scared", "trembled", "afraid", "terrified", "fear", "horror", "gasped", "shivered"],
    "excited":  ["excited", "thrilled", "eagerly", "enthusiastic", "can't wait", "amazing"],
    "calm":     ["calm", "quietly", "softly", "gently", "peacefully", "serene", "whispered"],
}

# ---------------------------------------------------------------------------
# Voice assignment matrix
# ---------------------------------------------------------------------------
VOICE_MATRIX = {
    # (gender, emotion) -> bark preset
    ("female", "calm"):     "v2/en_speaker_0",   # Aria
    ("female", "happy"):    "v2/en_speaker_2",   # Clara
    ("female", "excited"):  "v2/en_speaker_4",   # Elena
    ("female", "sad"):      "v2/en_speaker_8",   # Isla
    ("female", "angry"):    "v2/en_speaker_4",   # Elena (bright/intense)
    ("female", "scared"):   "v2/en_speaker_8",   # Isla (soft/shaky)
    ("female", "neutral"):  "v2/en_speaker_6",   # Grace
    ("male", "calm"):       "v2/en_speaker_7",   # Henry (narrator)
    ("male", "happy"):      "v2/en_speaker_5",   # Felix
    ("male", "excited"):    "v2/en_speaker_9",   # Jack
    ("male", "sad"):        "v2/en_speaker_1",   # Blake (deep)
    ("male", "angry"):      "v2/en_speaker_3",   # Derek (strong)
    ("male", "scared"):     "v2/en_speaker_5",   # Felix
    ("male", "neutral"):    "v2/en_speaker_7",   # Henry
    ("neutral", "neutral"): "v2/en_speaker_7",   # Henry (narrator default)
}

# Character → voice cache (consistent voice per character across script)
_character_voice_cache: dict[str, str] = {}
_character_counter = 0


# ---------------------------------------------------------------------------
# DOCX parsing
# ---------------------------------------------------------------------------

def parse_docx(file_path: str) -> str:
    """Extract all text from a .docx file."""
    doc = Document(file_path)
    lines = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Script parsing — main intelligence
# ---------------------------------------------------------------------------

# Patterns
RE_PART_HEADER = re.compile(
    r'^(?:PART|CHAPTER|SCENE|ACT|BOOK)\s+\w+', re.IGNORECASE
)
RE_SEPARATOR = re.compile(r'^-{3,}$|^\*{3,}$|^#{3,}$')
RE_TITLE = re.compile(r'^TITLE\s*:\s*(.+)$', re.IGNORECASE)
RE_SFX = re.compile(r'^\[(.+?)\]$')
RE_DIALOGUE = re.compile(
    r'^([A-Z][A-Za-z\s]{1,30}?)\s*:\s*["\u201c]?(.+?)["\u201d]?\s*$'
)
RE_DIALOGUE_SAID = re.compile(
    r'^["\u201c](.+?)["\u201d]\s*(?:said|whispered|shouted|yelled|cried|exclaimed|replied|asked|muttered|screamed)\s+([A-Z][A-Za-z\s]+?)\.?\s*$',
    re.IGNORECASE,
)


def parse_script(text: str) -> dict:
    """Parse a script into structured parts with classified segments.

    Returns: { "parts": [ { "name": str, "segments": [...] } ] }
    """
    global _character_voice_cache, _character_counter
    _character_voice_cache = {}
    _character_counter = 0

    lines = text.strip().split("\n")
    parts: list[dict] = []
    current_part_name = "Introduction"
    current_segments: list[dict] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # --- Part / Chapter separator ---
        if RE_PART_HEADER.match(line) or RE_SEPARATOR.match(line):
            # Save the current part
            if current_segments:
                parts.append({"name": current_part_name, "segments": current_segments})
                current_segments = []
            if RE_PART_HEADER.match(line):
                current_part_name = line
            else:
                current_part_name = f"Part {len(parts) + 2}"
            continue

        # --- Title ---
        title_match = RE_TITLE.match(line)
        if title_match:
            current_segments.append({
                "type": "title",
                "character": None,
                "text": title_match.group(1).strip(),
                "emotion": None,
                "voice": "v2/en_speaker_7",
            })
            continue

        # --- SFX ---
        sfx_match = RE_SFX.match(line)
        if sfx_match:
            current_segments.append({
                "type": "sfx",
                "character": None,
                "text": sfx_match.group(1).strip().lower(),
                "emotion": None,
                "voice": None,
            })
            continue

        # --- Dialogue (NAME: "text") ---
        dial_match = RE_DIALOGUE.match(line)
        if dial_match:
            char_name = dial_match.group(1).strip()
            dial_text = dial_match.group(2).strip()
            emotion = detect_emotion(dial_text)
            gender = detect_gender(char_name)
            voice = assign_voice(char_name, gender, emotion)
            current_segments.append({
                "type": "dialogue",
                "character": char_name,
                "text": dial_text,
                "emotion": emotion,
                "voice": voice,
            })
            continue

        # --- Dialogue ("text" said Character) ---
        said_match = RE_DIALOGUE_SAID.match(line)
        if said_match:
            dial_text = said_match.group(1).strip()
            char_name = said_match.group(2).strip()
            emotion = detect_emotion(dial_text)
            gender = detect_gender(char_name)
            voice = assign_voice(char_name, gender, emotion)
            current_segments.append({
                "type": "dialogue",
                "character": char_name,
                "text": dial_text,
                "emotion": emotion,
                "voice": voice,
            })
            continue

        # --- All-caps line at the top → treat as title ---
        if line.isupper() and len(line) > 3 and len(current_segments) == 0:
            current_segments.append({
                "type": "title",
                "character": None,
                "text": line.title(),
                "emotion": None,
                "voice": "v2/en_speaker_7",
            })
            continue

        # --- Narration (default) ---
        emotion = detect_emotion(line)
        current_segments.append({
            "type": "narrator",
            "character": None,
            "text": line,
            "emotion": emotion,
            "voice": "v2/en_speaker_7",
        })

    # Don't forget the last part
    if current_segments:
        parts.append({"name": current_part_name, "segments": current_segments})

    return {"parts": parts}


# ---------------------------------------------------------------------------
# Gender & emotion detection
# ---------------------------------------------------------------------------

def detect_gender(character_name: str) -> str:
    """Heuristic gender detection from character name."""
    name_lower = character_name.lower().split()[0] if character_name else ""
    if name_lower in FEMALE_NAMES:
        return "female"
    if name_lower in MALE_NAMES:
        return "male"
    # Check if name ends with common female suffixes
    if name_lower.endswith(("a", "ie", "ina", "elle", "ette")):
        return "female"
    return "neutral"


def detect_emotion(text: str) -> str:
    """Keyword-based emotion detection from text."""
    text_lower = text.lower()
    best_emotion = "neutral"
    best_count = 0
    for emotion, keywords in EMOTION_MAP.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count > best_count:
            best_count = count
            best_emotion = emotion
    return best_emotion


def assign_voice(character_name: str, gender: str, emotion: str) -> str:
    """Assign a consistent Bark voice preset to a character.

    Same character always gets the same base voice (for consistency),
    but emotion can modulate it.
    """
    global _character_counter

    # Check cache for a previously assigned base voice
    char_key = character_name.lower().strip()
    if char_key in _character_voice_cache:
        return _character_voice_cache[char_key]

    # Look up in the matrix
    voice = VOICE_MATRIX.get(
        (gender, emotion),
        VOICE_MATRIX.get((gender, "neutral"), "v2/en_speaker_7"),
    )

    # Cache it
    _character_voice_cache[char_key] = voice
    _character_counter += 1

    return voice
