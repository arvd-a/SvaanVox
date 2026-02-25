"""
SvaanVox — Flask application server.

Serves the frontend, exposes the /generate and /upload-* APIs,
and manages the audio library. Bark models are preloaded at startup.
"""

import os
import json
import datetime
from flask import Flask, render_template, request, jsonify

from engine import init_models, generate_speech, generate_audiobook, OUTPUT_DIR, UPLOADS_DIR
from script_parser import parse_docx, parse_script

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB upload limit

# Bark voice presets available in the UI
VOICE_PRESETS = [
    {"id": "v2/en_speaker_0",  "name": "Aria (Female, Calm)"},
    {"id": "v2/en_speaker_1",  "name": "Blake (Male, Deep)"},
    {"id": "v2/en_speaker_2",  "name": "Clara (Female, Warm)"},
    {"id": "v2/en_speaker_3",  "name": "Derek (Male, Strong)"},
    {"id": "v2/en_speaker_4",  "name": "Elena (Female, Bright)"},
    {"id": "v2/en_speaker_5",  "name": "Felix (Male, Friendly)"},
    {"id": "v2/en_speaker_6",  "name": "Grace (Female, Neutral)"},
    {"id": "v2/en_speaker_7",  "name": "Henry (Male, Narrator)"},
    {"id": "v2/en_speaker_8",  "name": "Isla (Female, Soft)"},
    {"id": "v2/en_speaker_9",  "name": "Jack (Male, Energetic)"},
]

# Available SFX names
SFX_NAMES = [
    "thunder", "rain", "door", "footsteps", "wind",
    "applause", "bell", "heartbeat", "silence", "whoosh", "suspense",
]


# ---------------------------------------------------------------------------
# Routes — Pages
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", voices=VOICE_PRESETS, sfx_names=SFX_NAMES)


# ---------------------------------------------------------------------------
# Routes — Simple TTS
# ---------------------------------------------------------------------------

@app.route("/generate", methods=["POST"])
def generate():
    """Generate audio from text (simple TTS or audiobook).

    Simple TTS:   { "text", "voice_preset", "mode": "standard" }
    Audiobook:    { "parts": [...], "bgm_map": {...}, "enable_sfx": bool, "mode": "audiobook" }
    """
    data = request.get_json(force=True)
    mode = data.get("mode", "standard")

    try:
        if mode == "audiobook" and "parts" in data:
            parts = data["parts"]
            bgm_map = data.get("bgm_map", {})
            enable_sfx = data.get("enable_sfx", True)
            result = generate_audiobook(parts, bgm_map=bgm_map, enable_sfx=enable_sfx)
        else:
            text = data.get("text", "").strip()
            voice_preset = data.get("voice_preset", "v2/en_speaker_6")
            if not text:
                return jsonify({"error": "Text is required."}), 400
            result = generate_speech(text, voice_preset=voice_preset, mode=mode)

        return jsonify(result)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Routes — DOCX Script Upload
# ---------------------------------------------------------------------------

@app.route("/upload-script", methods=["POST"])
def upload_script():
    """Upload a .docx file, parse it, return structured parts + segments."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    if not file.filename.lower().endswith(".docx"):
        return jsonify({"error": "Only .docx files are supported."}), 400

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    filepath = os.path.join(UPLOADS_DIR, file.filename)
    file.save(filepath)

    try:
        raw_text = parse_docx(filepath)
        parsed = parse_script(raw_text)
        parsed["raw_text"] = raw_text
        return jsonify(parsed)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Routes — BGM Music Upload
# ---------------------------------------------------------------------------

@app.route("/upload-music", methods=["POST"])
def upload_music():
    """Upload a .wav background music file for a specific part."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".wav",):
        return jsonify({"error": "Only .wav files are supported."}), 400

    os.makedirs(UPLOADS_DIR, exist_ok=True)
    # Save with a unique name to avoid collisions
    import uuid
    safe_name = f"bgm_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOADS_DIR, safe_name)
    file.save(filepath)

    return jsonify({
        "filename": safe_name,
        "path": filepath,
        "url": f"/static/uploads/{safe_name}",
    })


# ---------------------------------------------------------------------------
# Routes — Library
# ---------------------------------------------------------------------------

@app.route("/library")
def library():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = []
    for fname in sorted(os.listdir(OUTPUT_DIR), reverse=True):
        if fname.endswith(".wav"):
            fpath = os.path.join(OUTPUT_DIR, fname)
            stat = os.stat(fpath)
            files.append({
                "filename": fname,
                "url": f"/static/outputs/{fname}",
                "size_kb": round(stat.st_size / 1024, 1),
                "created": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    return jsonify(files)


@app.route("/library/<filename>", methods=["DELETE"])
def delete_file(filename):
    filepath = os.path.join(OUTPUT_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({"deleted": filename})
    return jsonify({"error": "File not found."}), 404


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 50)
    print("  SvaanVox — Text-to-Audio Engine v2")
    print("  Powered by Bark AI")
    print("=" * 50)
    init_models()
    app.run(host="0.0.0.0", port=8080, debug=False)
