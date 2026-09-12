#!/usr/bin/env python3
"""Extract the gnome from the source photo into companion assets.

The source photo is the mascot reference. This script lifts the gnome off its
dark studio background and produces the PNGs the desk companion displays.

No second guessing pass: one flood-fill from the border with a tolerance
derived from the measured dark background, one hole fill, one trim, one
export at the sizes the companion needs.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageFilter

# Background corner samples measured from the source photo (see commit log).
# Dark blue-black studio background.
BG_REF = (10, 14, 20)
BG_TOLERANCE = 28


def _border_pixels(img: Image.Image) -> list[tuple[int, int]]:
    w, h = img.size
    coords: list[tuple[int, int]] = []
    for x in range(w):
        coords.append((x, 0))
        coords.append((x, h - 1))
    for y in range(h):
        coords.append((0, y))
        coords.append((w - 1, y))
    return coords


def extract(src: Path, out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    img = Image.open(src).convert("RGB")
    w, h = img.size
    px = img.load()

    def is_bg(c: tuple[int, int, int]) -> bool:
        return (
            abs(c[0] - BG_REF[0]) <= BG_TOLERANCE
            and abs(c[1] - BG_REF[1]) <= BG_TOLERANCE
            and abs(c[2] - BG_REF[2]) <= BG_TOLERANCE
        )

    # Flood fill from the border: everything reachable that matches the dark
    # background is background; the gnome is the island.
    visited = bytearray(w * h)
    stack = [c for c in _border_pixels(img) if is_bg(px[c])]
    while stack:
        x, y = stack.pop()
        i = y * w + x
        if visited[i]:
            continue
        visited[i] = 1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not visited[ny * w + nx]:
                if is_bg(px[nx, ny]):
                    stack.append((nx, ny))
    # Anything the flood did not reach is the gnome (or a background island
    # trapped inside it — that is fine, it stays part of the mascot).
    mask = Image.new("1", (w, h), 1)
    mpx = mask.load()
    for y in range(h):
        for yx in range(w):
            if visited[y * w + yx]:
                mpx[yx, y] = 0

    cut = img.convert("RGBA")
    cut.putalpha(mask)

    # Trim to the gnome plus a small margin.
    bbox = mask.getbbox()
    if bbox:
        margin = 24
        l = max(0, bbox[0] - margin)
        t = max(0, bbox[1] - margin)
        r = min(w, bbox[2] + margin)
        b = min(h, bbox[3] + margin)
        cut = cut.crop((l, t, r, b))

    # Soft edge: 1px feather so it does not look cut out with scissors.
    alpha = cut.getchannel("A").filter(ImageFilter.GaussianBlur(0.6))
    cut.putalpha(alpha)

    written: dict[str, Path] = {}
    resample = getattr(Image, "Resampling", Image).LANCZOS
    for name, size in (("gnome@128", 128), ("gnome@256", 256), ("gnome@512", 512)):
        out = out_dir / f"{name}.png"
        s = cut.resize((size, int(size * cut.height / cut.width)), resample)
        s.save(out)
        written[name] = out
    return written


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else []
    src = Path(
        "/Users/christian.grau/Library/Application Support/Hermes/composer-images/"
        "059DDA96-54B8-4C6F-AC7B-AD176920F606_8cd3e7.png"
    )
    out_dir = Path(argv[1]) if len(argv) > 1 else Path("companion/assets")
    if not src.is_file():
        print(f"source photo missing: {src}", file=sys.stderr)
        return 1
    written = extract(src, out_dir)
    for name, path in written.items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())