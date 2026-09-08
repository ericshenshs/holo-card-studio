#!/usr/bin/env python3
"""[cc] Export a card project as a macOS .app inside a .dmg — double-click to view.
Uses the card's subject.png as the app icon. Three.js loads from CDN, no node_modules needed.

Usage: python3 export_dmg.py <project_dir> [--output <path.dmg>]
"""

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

INFO_PLIST = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" \
"http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>{name}</string>
  <key>CFBundleDisplayName</key>
  <string>{display}</string>
  <key>CFBundleIdentifier</key>
  <string>com.holo.{slug}</string>
  <key>CFBundleExecutable</key>
  <string>start</string>
  <key>CFBundleVersion</key>
  <string>1.0</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>LSMinimumSystemVersion</key>
  <string>10.15</string>
</dict>
</plist>
"""

LAUNCHER = """\
#!/bin/bash
# [cc] Auto-start local server and open card in browser
DIR="$(cd "$(dirname "$0")/../Resources/web" && pwd)"
cd "$DIR" || exit 1
PORT=$(python3 -c "import socket; s=socket.socket(); s.bind(('',0)); print(s.getsockname()[1]); s.close()")
python3 -m http.server "$PORT" --bind 127.0.0.1 &
SERVER_PID=$!
cleanup() { kill "$SERVER_PID" 2>/dev/null; wait "$SERVER_PID" 2>/dev/null; }
trap cleanup EXIT INT TERM
sleep 0.5
open "http://127.0.0.1:${PORT}"
wait "$SERVER_PID"
"""

# [cc] CDN import map replaces local node_modules — keeps the package small
CDN_IMPORTMAP = '{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/"}}'


def make_icns(source_png: Path, output: Path):
    """[cc] Convert a PNG to macOS .icns using sips + iconutil."""
    iconset = output.parent / "tmp.iconset"
    iconset.mkdir(exist_ok=True)
    sizes = [
        (16, "icon_16x16.png"), (32, "icon_16x16@2x.png"),
        (32, "icon_32x32.png"), (64, "icon_32x32@2x.png"),
        (128, "icon_128x128.png"), (256, "icon_128x128@2x.png"),
        (256, "icon_256x256.png"), (512, "icon_256x256@2x.png"),
        (512, "icon_512x512.png"), (1024, "icon_512x512@2x.png"),
    ]
    for sz, name in sizes:
        subprocess.run(
            ["sips", "-z", str(sz), str(sz), str(source_png),
             "--out", str(iconset / name)],
            capture_output=True,
        )
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(output)],
                   check=True, capture_output=True)
    shutil.rmtree(iconset)


def main():
    parser = argparse.ArgumentParser(description="Export card as macOS .dmg")
    parser.add_argument("project_dir", help="Path to the card project directory")
    parser.add_argument("--output", "-o", help="Output .dmg path (default: ~/Desktop/<slug>.dmg)")
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    web_dir = project / "web"
    config = json.loads((project / "card-config.json").read_text())
    slug = project.name
    title = config.get("title", slug)
    subtitle = config.get("subtitle", "")
    app_name = f"{title}"
    if subtitle:
        app_name = f"{title} — {subtitle}"

    output = Path(args.output) if args.output else Path.home() / "Desktop" / f"{slug}.dmg"

    if not web_dir.exists():
        print(f"ERROR: {web_dir} does not exist. Run the pipeline first.")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        # [cc] Build .app structure
        app_dir = tmp / f"{app_name}.app"
        macos_dir = app_dir / "Contents" / "MacOS"
        res_dir = app_dir / "Contents" / "Resources"
        web_dst = res_dir / "web"
        macos_dir.mkdir(parents=True)
        res_dir.mkdir(parents=True)

        # [cc] Info.plist
        (app_dir / "Contents" / "Info.plist").write_text(
            INFO_PLIST.format(name=app_name, display=title, slug=slug)
        )

        # [cc] Launcher script
        launcher = macos_dir / "start"
        launcher.write_text(LAUNCHER)
        launcher.chmod(0o755)

        # [cc] Copy web files (skip node_modules)
        web_dst.mkdir()
        assets_dst = web_dst / "assets"
        assets_dst.mkdir()
        for f in ["app.js", "style.css", "card-config.json", "server.mjs"]:
            src = web_dir / f
            if src.exists():
                shutil.copy2(src, web_dst / f)
        for f in (web_dir / "assets").iterdir():
            shutil.copy2(f, assets_dst / f.name)

        # [cc] Rewrite index.html to use CDN import map
        html = (web_dir / "index.html").read_text()
        html = html.replace(
            '{"imports":{"three":"./node_modules/three/build/three.module.js","three/addons/":"./node_modules/three/examples/jsm/"}}',
            CDN_IMPORTMAP,
        )
        (web_dst / "index.html").write_text(html)

        # [cc] Generate .icns from subject.png
        subject = project / "assets" / "subject.png"
        if subject.exists():
            icns = res_dir / "AppIcon.icns"
            print(f"Creating app icon from {subject.name}...")
            make_icns(subject, icns)

        # [cc] Build DMG
        dmg_staging = tmp / "dmg"
        dmg_staging.mkdir()
        shutil.copytree(app_dir, dmg_staging / app_dir.name, symlinks=True)

        print(f"Creating DMG...")
        output.unlink(missing_ok=True)
        subprocess.run(
            ["hdiutil", "create", "-volname", title,
             "-srcfolder", str(dmg_staging), "-ov", "-format", "UDZO",
             str(output)],
            check=True, capture_output=True,
        )

        size_mb = output.stat().st_size / 1024 / 1024
        print(f"Done: {output} ({size_mb:.1f} MB)")
        print(f"Send via AirDrop, iMessage, Google Drive, or WeChat.")
        return 0


if __name__ == "__main__":
    exit(main())
