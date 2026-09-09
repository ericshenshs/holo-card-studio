#!/usr/bin/env python3
"""[cc] Generate the 4 card layers (subject, background, lineart, text) using OpenAI's
DALL-E image generation API. Uses OPENAI_API_KEY from environment.

Usage: python3 generate_images.py <project_dir> [--subject-prompt "..."] [--bg-prompt "..."]
"""

import argparse
import base64
import json
import os
import random
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
    parser.add_argument("--art-style", default="ffta",
                        help="Art style preset (default: ffta). Options: ffta, cute, realistic")
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

    # [cc] FFTA random element pools — picked at random per card to make each unique.
    # Foreground is either a character class or a weapon, chosen 50/50, then a random
    # pick within that category. Background is a random FFTA/FFTA2 scene/location.
    # These are combined with the card's own topic to form the final prompt.

    # [cc] Character classes from FFTA, FFTA2, and FFT series
    FFTA_CLASSES = [
        "Soldier with iron armor and a broadsword",
        "Black Mage in a pointed hat channeling fire magic",
        "White Mage in flowing robes with a healing staff",
        "Archer in a leather jerkin with a longbow",
        "Thief in dark clothing with twin daggers",
        "Paladin in gleaming silver-gold armor with a knight sword",
        "Ninja in dark wrappings throwing shuriken",
        "Blue Mage in a blue coat studying monster abilities",
        "Summoner in ornate robes calling forth an Esper",
        "Assassin in a hooded cloak with a concealed blade",
        "Dragoon in spiked armor leaping with a lance",
        "Illusionist in a star-patterned robe weaving illusions",
        "Sniper in a long coat taking aim with a greatbow",
        "Mog Knight — a Moogle in tiny plate armor with a blade",
        "Juggler — a Moogle tossing daggers and rings in the air",
        "Sage in ancient robes channeling both black and white magic",
        "Templar in heavy crusader armor with a sacred blade",
        "Fencer in elegant dueling attire with a rapier",
        "Elementalist channeling wind and thunder through a staff",
        "Gladiator in arena armor wielding a massive greatsword",
        "Hunter in a ranger cloak with a hunting bow and a Moogle companion",
        "Morpher shapeshifting into a captured monster",
        "Time Mage in a clock-patterned robe bending time and space",
        "Beastmaster commanding a pack of magical creatures",
        "Cannoneer in a bandolier with a hand cannon",
        "Heritor in royal attire wielding a legendary blade",
        "Geomancer barefoot on crystal ground, channeling earth magic",
    ]

    # [cc] Weapons from FFTA/FFTA2 — each with a visual description
    FFTA_WEAPONS = [
        "a Mythril Sword — a gleaming silver longsword with rune engravings",
        "a Sequence — a golden rapier with an ornate swept hilt",
        "a Estreledge — a dark greatsword crackling with lightning",
        "a Masamune — an elegant katana with a crimson tassel",
        "a Sage Staff — a gnarled wooden staff topped with a glowing crystal orb",
        "a Perseus Bow — a sleek silver bow radiating holy light",
        "a Zwill Crossblade — twin curved daggers connected by a chain",
        "a Javelin — a barbed throwing spear with red feather tassels",
        "a Lotus Mace — a heavy flanged mace with a blooming lotus motif",
        "a Save the Queen — a holy knight sword wreathed in golden aura",
        "an Artemis Bow — a green-tinted elven longbow with vine carvings",
        "a Nirvana Staff — a crystal staff emanating rainbow-colored healing light",
        "a Cinquedea — a wide-bladed short sword with five fullers",
        "a Dragon Whisker — a long spear made from a dragon's fang",
        "a Tonberry Knife — a small eerie lantern-shaped knife glowing green",
        "a Excalibur — a legendary golden sword radiating brilliant white light",
        "a Murasame — a blue-tempered katana dripping with water energy",
        "a Chaos Rifle — a steampunk hand cannon with arcane sigils",
    ]

    # [cc] Background scenes/locations from FFTA, FFTA2, and FFT series
    FFTA_SCENES = [
        "Lutche Highlands — rolling green hills with scattered stone ruins under a warm golden sky",
        "Cyril town square — a cozy medieval marketplace with cobblestone streets and timber-frame shops",
        "Jagd Dorsa — a lawless volcanic wasteland with red crags and black smoke plumes",
        "Materiwood — a dense enchanted forest with glowing mushrooms and dappled green light",
        "Cadoan city — a grand desert city with sandstone towers and fluttering banners",
        "Roda Volcano — a fiery volcanic crater with rivers of lava and obsidian pillars",
        "Nubswood — a misty twilight grove with enormous ancient trees draped in moss",
        "Bervenia Palace — a grand throne room with stained glass windows and marble floors",
        "Aisenfield — a vast golden wheat field stretching to distant blue mountains",
        "Koringwood — a dark autumnal forest with orange-red canopy and scattered leaves",
        "Salikawood — a crystalline forest where trees are made of translucent blue crystal",
        "Goug Machine City — a steampunk workshop filled with gears, pipes, and sparking machinery",
        "Zellea Falls — a majestic waterfall cascading into a turquoise pool surrounded by ferns",
        "Camoa town — a bustling port town with colorful awnings and ships in the harbor",
        "Graszton — a rainy gothic town with dark spires and lantern-lit cobblestone alleys",
        "The Aldanna Range — snow-capped mountain peaks above the clouds at sunrise",
        "Orbonne Monastery library — an ancient candlelit library with towering bookshelves",
        "Lezaford's Cottage — a wizard's cozy hilltop cottage with potion bottles and star charts",
        "Zedlei Forest — a bright springtime forest with cherry blossoms falling like snow",
        "Giza Plains — a wide savannah with tall grass swaying under a dramatic sunset sky",
    ]

    # [cc] Non-FFTA style presets (kept simple — no random element picks)
    OTHER_STYLES = {
        "cute": {
            "subject": (
                "A super cute character illustration for a collectible card. "
                "Bold readable contours, vibrant colors, adorable proportions. "
            ),
            "bg": (
                "A beautiful atmospheric background for a collectible card. "
                "Full opaque canvas, dreamy and magical atmosphere. "
            ),
            "lineart": (
                "A clean line art drawing. "
                "Simplified single contour strokes. "
            ),
        },
        "realistic": {
            "subject": (
                "A realistic detailed character illustration for a premium collectible card. "
                "Photorealistic rendering with dramatic lighting, rich textures, and fine detail. "
            ),
            "bg": (
                "A photorealistic atmospheric background for a premium collectible card. "
                "Cinematic lighting, volumetric fog, rich environmental detail. "
            ),
            "lineart": (
                "A detailed technical line drawing with fine cross-hatching and precise contours. "
            ),
        },
    }

    print(f"Art style: {args.art_style}")

    # [cc] For FFTA style, randomly pick a foreground element (character or weapon)
    # and a background scene, then build a prompt where the card's topic is primary
    # and the FFTA element is the visual vehicle adapted to fit the topic's context
    # (time of day, mood, setting, activity). The result must make sense as a whole —
    # e.g. a "morning gym workout" card should show dawn lighting and energetic posing,
    # regardless of which FFTA class or weapon was randomly drawn.
    if args.art_style == "ffta":
        # [cc] 50/50 chance: character class or weapon as foreground subject
        if random.random() < 0.5:
            fg_pick = random.choice(FFTA_CLASSES)
            fg_type = "character"
        else:
            fg_pick = random.choice(FFTA_WEAPONS)
            fg_type = "weapon"

        bg_pick = random.choice(FFTA_SCENES)

        print(f"  FFTA foreground ({fg_type}): {fg_pick}")
        print(f"  FFTA background: {bg_pick}")

        ffta_base = (
            "In the art style of Final Fantasy Tactics Advance (FFTA / Square Enix GBA tactical RPG): "
            "soft cel-shaded with warm saturated colors, slightly chibi proportions if character, "
            "clean defined outlines, gentle shading with no harsh shadows. "
            "Rich color harmony (warm golds, deep blues, soft greens). "
            "Painterly yet crisp, like an FFTA ability card illustration. "
        )

        # [cc] The card topic is the primary context — the FFTA element must adapt to it.
        # We tell the model the card's meaning first, then ask it to express that meaning
        # through the randomly chosen FFTA figure, adapting pose/mood/lighting to match.
        if fg_type == "character":
            subject_style = (
                f"{ffta_base}"
                f"This card's meaning: \"{description}\". "
                f"Express this meaning through an FFTA {fg_pick}. "
                f"Adapt the character's pose, expression, lighting, and time-of-day atmosphere "
                f"to match the card's concept. For example, if the card is about morning energy, "
                f"show dawn light and a dynamic ready-to-go stance; if about nighttime discipline, "
                f"show moonlit determination. The character IS the card's concept made visible. "
            )
        else:
            subject_style = (
                f"{ffta_base}"
                f"This card's meaning: \"{description}\". "
                f"Express this meaning through {fg_pick}, displayed as the card's centerpiece. "
                f"Adapt the weapon's glow, aura, surrounding particles, and lighting "
                f"to match the card's concept and time of day. The weapon embodies the card's energy — "
                f"it should feel like the concept given physical form. "
            )

        bg_style = (
            "In the art style of Final Fantasy Tactics Advance (FFTA) environment art. "
            f"This card's meaning: \"{description}\". "
            f"Use this FFTA location as a starting point: {bg_pick}. "
            f"But adapt the lighting, time of day, weather, and mood to match the card's concept. "
            f"If the card is about morning, paint dawn light; if about night, paint moonlight and lanterns; "
            f"if about energy, use warm vibrant tones; if about calm focus, use cool serene tones. "
            "The scene must feel coherent with the card's theme — the FFTA location provides "
            "the architectural and environmental structure, the card's topic provides the atmosphere. "
            "Warm painterly rendering with soft atmospheric perspective, storybook quality. "
        )

        lineart_style = (
            "In the style of a Final Fantasy Tactics Advance character outline sheet: "
            "clean, confident ink strokes with slight warmth, soft rounded contours. "
            f"The figure is: {fg_pick}, posed to convey \"{description}\". "
        )
    else:
        style = OTHER_STYLES.get(args.art_style, OTHER_STYLES["cute"])
        subject_style = f"{style['subject']}Subject: {description}. "
        bg_style = f"{style['bg']}Theme: {description}. "
        lineart_style = f"{style['lineart']}Matching this character: {description}. "

    # [cc] --- Layer 1: Subject (transparent RGBA) ---
    subject_prompt = args.subject_prompt or (
        f"{subject_style}"
        f"The figure should be centered on a COMPLETELY TRANSPARENT background "
        f"(no background at all, pure alpha transparency). "
        f"Portrait orientation, full body visible with clear silhouette. "
        f"No text, no border, no frame, no background scenery."
    )
    print(f"Generating subject layer...")
    subject_data = generate_image(client, subject_prompt)
    (assets / "subject.png").write_bytes(subject_data)
    print(f"  Saved subject.png ({len(subject_data)} bytes)")

    # [cc] --- Layer 2: Background (full opaque canvas) ---
    bg_prompt = args.bg_prompt or (
        f"{bg_style}"
        f"Full opaque canvas. "
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
        f"{lineart_style}"
        f"ONLY black contour strokes on a pure white background. "
        f"Same pose and placement as the original figure. "
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
