#!/usr/bin/env python3
"""[cc] Generate the 4 card layers (subject, background, lineart, text) using OpenAI's
DALL-E image generation API. Uses OPENAI_API_KEY from environment.

Usage: python3 generate_images.py <project_dir> [--subject-prompt "..."] [--bg-prompt "..."]
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

# [cc] Use the temp venv's openai if system doesn't have it
VENV_SITE = Path("/tmp/openai-env/lib").glob("python*/site-packages")
for p in VENV_SITE:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from openai import OpenAI


def generate_image(client, prompt, size="1024x1536", style="vivid", quality="high"):
    """[cc] Generate an image using DALL-E and return raw PNG bytes."""
    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        n=1,
        size=size,
        quality=quality,
    )
    # [cc] gpt-image-1 returns base64 by default
    b64 = response.data[0].b64_json
    return base64.b64decode(b64)


def main():
    parser = argparse.ArgumentParser(description="Generate card layer images")
    parser.add_argument("project_dir", help="Path to the card project directory")
    parser.add_argument("--subject-prompt", help="Override subject prompt")
    parser.add_argument("--bg-prompt", help="Override background prompt")
    parser.add_argument("--lineart-prompt", help="Override lineart prompt")
    parser.add_argument("--skip-text", action="store_true",
                        help="Skip text layer (use generate_typography.py instead)")
    args = parser.parse_args()

    project = Path(args.project_dir)
    assets = project / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    # [cc] Read card config for context
    config_path = project / "card-config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
    else:
        print("ERROR: card-config.json not found in project directory")
        sys.exit(1)

    title = config.get("title", "")
    subtitle = config.get("subtitle", "")
    description = config.get("description", "")
    technique = config.get("technique", "")

    client = OpenAI()

    # [cc] --- Layer 1: Subject (transparent RGBA) ---
    subject_prompt = args.subject_prompt or (
        f"A super cute character illustration for a collectible card. "
        f"{description} "
        f"The character should be centered on a COMPLETELY TRANSPARENT background "
        f"(no background at all, pure alpha transparency). "
        f"Bold readable contours, vibrant colors, adorable proportions. "
        f"Portrait orientation, full body visible with clear silhouette. "
        f"No text, no border, no frame, no background scenery."
    )
    print(f"Generating subject layer...")
    subject_data = generate_image(client, subject_prompt)
    (assets / "subject.png").write_bytes(subject_data)
    print(f"  Saved subject.png ({len(subject_data)} bytes)")

    # [cc] --- Layer 2: Background (full opaque canvas) ---
    bg_prompt = args.bg_prompt or (
        f"A beautiful atmospheric background for a collectible card. "
        f"Theme: {description} "
        f"Full opaque canvas, dreamy and magical atmosphere. "
        f"Leave the center relatively quiet for the main subject overlay. "
        f"Rich colors at edges, subtle magical particles and lighting effects. "
        f"No characters, no text, no border. Portrait orientation 1024x1536."
    )
    print(f"Generating background layer...")
    bg_data = generate_image(client, bg_prompt)
    (assets / "background.png").write_bytes(bg_data)
    print(f"  Saved background.png ({len(bg_data)} bytes)")

    # [cc] --- Layer 3: Line art (black contours on white) ---
    lineart_prompt = args.lineart_prompt or (
        f"A clean line art drawing matching this character: {description} "
        f"ONLY simplified single black contour strokes on a pure white background. "
        f"Same pose and placement as the original character. "
        f"No hatching, no filled areas, no shading, no color. "
        f"Just clean black outlines on white. Portrait orientation."
    )
    print(f"Generating lineart layer...")
    lineart_data = generate_image(client, lineart_prompt)
    (assets / "lineart.png").write_bytes(lineart_data)
    print(f"  Saved lineart.png ({len(lineart_data)} bytes)")

    print("\nAll image layers generated successfully!")
    print(f"Assets directory: {assets}")
    print("Next: run generate_typography.py for text layer, then run_pipeline.py")


if __name__ == "__main__":
    main()
