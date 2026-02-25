# 🐺 SvaanVox — AI Text-to-Audio Engine

> Transform scripts into stunning multi-character audiobooks with intelligent voice switching, sound effects, and background music — powered by [Bark AI](https://github.com/suno-ai/bark).

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-Backend-black?logo=flask)
![Bark AI](https://img.shields.io/badge/Bark_AI-TTS-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ Features

- **🎙️ 10 Distinct AI Voices** — Male & female presets with emotion-aware selection (calm, happy, sad, angry)
- **📖 Audiobook Mode** — Upload `.docx` scripts and auto-detect characters, chapters, dialogue, and narration
- **🎵 Background Music (BGM)** — Upload `.wav` BGM per chapter with automatic looping, fade-in/out, and volume ducking
- **⚡ Sound Effects (SFX)** — Built-in synthesized SFX library (thunder, rain, footsteps, heartbeat, etc.)
- **🧠 Smart Script Parser** — Detects character gender via name heuristics, scans emotions via keywords, and auto-assigns voices
- **🖥️ Premium Dark Mode UI** — 3-pane dashboard inspired by modern audio production tools
- **🚀 GPU Accelerated** — Full NVIDIA CUDA support for real-time generation

---

## 🖼️ Screenshots

| Home | Audiobook Timeline |
|------|-------------------|
| Dark mode landing page with quick actions | Part-by-part script preview with color-coded segments |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- NVIDIA GPU with CUDA support (recommended) or CPU (slower)
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/arvd-a/SvaanVox.git
cd SvaanVox

# Create a virtual environment (recommended)
uv venv --python 3.12 .venv

# Activate it
# Windows:
.\.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install PyTorch with GPU support (NVIDIA CUDA 12.4)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# Install dependencies
pip install -r requirements.txt

# Install compatible transformers version
pip install transformers==4.47.0

# Generate the SFX library
python generate_sfx.py
```

### Run

```bash
python app.py
```

Open your browser at **http://localhost:8080**

> **Windows shortcut:** Double-click `start.bat` to launch with GPU acceleration.

---

## 📁 Project Structure

```
SvaanVox/
├── app.py              # Flask server (routes, API)
├── engine.py           # Bark AI engine (TTS, chunking, BGM mixing)
├── script_parser.py    # DOCX parser (character detection, emotion, voices)
├── generate_sfx.py     # One-time SFX WAV generator
├── start.bat           # Windows GPU launch script
├── requirements.txt    # Python dependencies
├── templates/
│   └── index.html      # Frontend UI (Tailwind CSS dark mode)
└── static/
    ├── app.js          # Frontend JavaScript logic
    ├── logo.png        # SvaanVox logo
    ├── sfx/            # Generated sound effects
    ├── outputs/        # Generated audio files
    └── uploads/        # Uploaded scripts & BGM
```

---

## 🎧 How It Works

### Standard TTS
1. Type or paste any text
2. Select a voice preset
3. Click **Generate** → get a `.wav` file instantly

### Audiobook Mode
1. Upload a `.docx` script file
2. SvaanVox auto-detects **Parts/Chapters**, **Characters**, **Dialogue**, **SFX cues**, and **Narration**
3. Each character is assigned a voice based on detected **gender** and **emotion**
4. Optionally upload `.wav` BGM files per chapter
5. Toggle sound effects on/off
6. Click **Generate Audiobook** → full multi-voice audiobook with BGM and SFX

### Script Format

SvaanVox understands scripts formatted like this:

```
CHAPTER 1 — The Beginning

[thunder]

The rain poured heavily over the old mansion.

Elena: "I can't believe we're actually here."

Derek: "Stay close. This place isn't safe."

[footsteps]

They moved cautiously through the dark hallway.
```

---

## 🎤 Voice Presets

| Voice | Gender | Emotion |
|-------|--------|---------|
| Aria | Female | Calm |
| Clara | Female | Warm |
| Elena | Female | Bright |
| Isla | Female | Soft |
| Grace | Female | Neutral |
| Blake | Male | Deep |
| Derek | Male | Strong |
| Felix | Male | Friendly |
| Henry | Male | Narrator |
| Jack | Male | Energetic |

---

## ⚡ Performance

| Environment | Speed per Sentence |
|-------------|-------------------|
| CPU only | ~3-5 minutes |
| NVIDIA RTX 4060 | ~10-15 seconds |
| NVIDIA A100 / Cloud GPU | ~2-3 seconds |

---

## 🛠️ Tech Stack

- **Backend:** Flask, Python
- **AI Engine:** [Bark by Suno AI](https://github.com/suno-ai/bark)
- **Audio:** NumPy, SciPy
- **Document Parsing:** python-docx
- **Frontend:** HTML5, Tailwind CSS, Vanilla JavaScript
- **GPU:** PyTorch with CUDA

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## 🙏 Acknowledgements

- [Suno AI — Bark](https://github.com/suno-ai/bark) for the incredible open-source text-to-audio model
- [Tailwind CSS](https://tailwindcss.com/) for the utility-first CSS framework

---

<p align="center">
  <b>SvaanVox</b> — Where scripts come alive. 🐺
</p>
