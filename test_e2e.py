"""End-to-end test: upload DOCX, parse, generate audiobook."""
import requests
import json

# Test 1: Upload DOCX
print("=== UPLOADING DOCX ===")
with open("test_script.docx", "rb") as f:
    r = requests.post("http://localhost:5000/upload-script", files={"file": f})
parsed = r.json()
if "error" in parsed:
    print("ERROR:", parsed["error"])
    exit(1)

num_parts = len(parsed.get("parts", []))
print(f"Parts detected: {num_parts}")
for p in parsed.get("parts", []):
    print(f"  {p['name']} ({len(p['segments'])} segments)")
    for s in p["segments"]:
        char = s.get("character") or "-"
        print(f"    [{s['type']:>8}] {char:>10} | {s['text'][:50]:50s} | voice={s.get('voice','n/a')}")

# Test 2: Generate audiobook
print("\n=== GENERATING AUDIOBOOK ===")
r2 = requests.post("http://localhost:5000/generate", json={
    "parts": parsed["parts"],
    "bgm_map": {},
    "enable_sfx": True,
    "mode": "audiobook",
})
result = r2.json()
print(json.dumps(result, indent=2))
