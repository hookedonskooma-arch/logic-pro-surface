#!/usr/bin/env python3
"""Describe an image via local Ollama vision model (moondream/llava)."""
import sys, json, base64, urllib.request

def describe(image_path, prompt, model="moondream"):
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    payload = {"model": model, "prompt": prompt, "images": [b64], "stream": False}
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        result = json.loads(r.read())
    return result.get("response", "NO RESPONSE")

if __name__ == "__main__":
    image_path = sys.argv[1]
    prompt = sys.argv[2] if len(sys.argv) > 2 else "Describe this image in detail."
    model = sys.argv[3] if len(sys.argv) > 3 else "moondream"
    print(describe(image_path, prompt, model))