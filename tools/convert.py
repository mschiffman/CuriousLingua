#!/usr/bin/env python3
"""
Convert PNG images to JPG the way Squoosh does.

Squoosh (squoosh.app) saves JPGs with MozJPEG using these defaults:
    quality 75, progressive, optimized Huffman coding, 4:2:0 chroma
    subsampling, YCbCr colour, no smoothing, quantization table 3
    (the "ImageMagick" table by N. Robidoux), trellis quantization,
    and no metadata.

If pyvips is installed, this script uses its built-in MozJPEG with those same
settings, so files match Squoosh's. (Below quality 70, libvips caps a few
quantization values at 255, so files there come out a touch larger.)

Without pyvips it falls back to Pillow, which has every setting except trellis
quantization: same quality, files roughly 10-15% larger.

Usage:
    python png_to_jpg.py                          # every PNG in this script's folder
    python png_to_jpg.py image.png                # one file
    python png_to_jpg.py images/                  # every PNG in a folder
    python png_to_jpg.py images/ -r               # include subfolders
    python png_to_jpg.py images/ -o jpg_out/      # write to another folder
    python png_to_jpg.py images/ -q 80            # same as Squoosh's quality slider
    python png_to_jpg.py images/ --max-side 1600  # shrink so the longest side is 1600 px
    python png_to_jpg.py images/ --scale 0.8      # shrink to 80%

Requires:  pip install pillow "pyvips[binary]"
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageColor

try:
    import pyvips  # "pyvips[binary]" includes libvips built with MozJPEG
except (ImportError, OSError):
    pyvips = None

# MozJPEG quantization table 3 (ImageMagick table by N. Robidoux).
# Squoosh uses it for both the brightness and the colour channels.
ROBIDOUX_TABLE = [
    16,  16,  16,  18,  25,  37,  56,  85,
    16,  17,  20,  27,  34,  40,  53,  75,
    16,  20,  24,  31,  43,  62,  91, 135,
    18,  27,  31,  40,  53,  74, 106, 156,
    25,  34,  43,  53,  69,  94, 131, 189,
    37,  40,  62,  74,  94, 124, 169, 238,
    56,  53,  91, 106, 131, 169, 226, 311,
    85,  75, 135, 156, 189, 238, 311, 418,
]


def squoosh_qtable(quality: int) -> list[int]:
    """Scale the base table for a 1-100 quality value, exactly as MozJPEG does."""
    scale = 5000 // quality if quality < 50 else 200 - quality * 2
    return [min(32767, max(1, (v * scale + 50) // 100)) for v in ROBIDOUX_TABLE]


def to_rgb(img: Image.Image, background: tuple[int, int, int]) -> Image.Image:
    """JPG has no transparency, so place transparent images on a solid background."""
    has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
    if not has_alpha:
        return img.convert("RGB")
    img = img.convert("RGBA")
    flat = Image.new("RGB", img.size, background)
    flat.paste(img, mask=img.getchannel("A"))
    return flat


def new_size(width: int, height: int, scale: float | None, max_side: int | None) -> tuple[int, int]:
    factor = scale or 1.0
    if max_side:
        factor = min(factor, max_side / max(width, height))
    factor = min(factor, 1.0)  # never enlarge
    return max(1, round(width * factor)), max(1, round(height * factor))


def convert_mozjpeg(src: Path, dest: Path, args: argparse.Namespace) -> None:
    """Encode with libvips' MozJPEG, using Squoosh's default settings."""
    img = pyvips.Image.new_from_file(str(src), access="sequential")
    if img.interpretation != "srgb":  # grayscale or 16-bit PNGs -> 8-bit RGB
        img = img.colourspace("srgb")
    if img.hasalpha():  # JPG has no transparency
        img = img.flatten(background=list(args.background))

    w, h = new_size(img.width, img.height, args.scale, args.max_side)
    if (w, h) != (img.width, img.height):
        img = img.resize(w / img.width, vscale=h / img.height)  # Lanczos3, Squoosh's default

    img.jpegsave(
        str(dest),
        Q=args.quality,
        quant_table=3,             # Squoosh's ImageMagick table
        optimize_coding=True,      # optimized Huffman tables
        interlace=True,            # progressive
        optimize_scans=True,
        trellis_quant=True,
        overshoot_deringing=True,
        subsample_mode="on",       # always 4:2:0; libvips' "auto" switches to 4:4:4 at Q 90+
        keep=pyvips.enums.ForeignKeep.ICC,  # keep colours right if the PNG has a colour profile
    )


def convert_pillow(src: Path, dest: Path, args: argparse.Namespace) -> None:
    """Encode with Pillow, using every Squoosh setting except trellis quantization."""
    with Image.open(src) as img:
        icc = img.info.get("icc_profile")
        rgb = to_rgb(img, args.background)

    size = new_size(rgb.width, rgb.height, args.scale, args.max_side)
    if size != rgb.size:
        rgb = rgb.resize(size, Image.Resampling.LANCZOS)  # Squoosh's default resize method

    table = squoosh_qtable(args.quality)
    rgb.save(
        dest,
        "JPEG",
        qtables=[table, table],  # already scaled for quality; don't also pass quality=
        subsampling=2,           # 4:2:0, what Squoosh's "auto subsample" picks
        progressive=True,
        optimize=True,           # optimized Huffman tables
        icc_profile=icc,         # keep colours right if the PNG has a colour profile
    )


def convert(src: Path, dest: Path, args: argparse.Namespace) -> tuple[int, int]:
    """Convert one PNG to JPG. Returns (old_size, new_size) in bytes."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if pyvips:
        convert_mozjpeg(src, dest, args)
    else:
        convert_pillow(src, dest, args)
    return src.stat().st_size, dest.stat().st_size


def find_pngs(target: Path, recursive: bool) -> list[Path]:
    if target.is_file():
        return [target]
    pattern = "**/*" if recursive else "*"
    return sorted(p for p in target.glob(pattern) if p.is_file() and p.suffix.lower() == ".png")


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def change(old: int, new: int) -> str:
    saved = 100 * (1 - new / old) if old else 0
    return f"{saved:.0f}% smaller" if saved >= 0 else f"{-saved:.0f}% larger"


def quality_value(text: str) -> int:
    q = int(text)
    if not 1 <= q <= 100:
        raise argparse.ArgumentTypeError("quality must be 1-100")
    return q


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert PNG images to JPG with Squoosh's MozJPEG settings.")
    parser.add_argument("target", type=Path, nargs="?", default=Path(__file__).parent,
                        help="a PNG file or a folder of PNGs (default: this script's folder)")
    parser.add_argument("-o", "--out", type=Path, help="output folder (default: next to each PNG)")
    parser.add_argument("-r", "--recursive", action="store_true", help="include subfolders")
    parser.add_argument("-q", "--quality", type=quality_value, default=75, help="1-100 (Squoosh default: 75)")
    parser.add_argument("--max-side", type=int, help="shrink so the longest side is at most this many pixels")
    parser.add_argument("--scale", type=float, help="shrink by this factor, e.g. 0.8")
    parser.add_argument("--background", type=ImageColor.getrgb, default="white",
                        help="colour behind transparent areas, e.g. white, black, #f0f0f0 (default: white)")
    parser.add_argument("--overwrite", action="store_true", help="replace existing .jpg files")
    args = parser.parse_args()

    if not args.target.exists():
        sys.exit(f"Not found: {args.target}")

    pngs = find_pngs(args.target, args.recursive)
    if not pngs:
        sys.exit("No PNG files found.")

    if pyvips:
        print("Encoder: MozJPEG (pyvips), same as Squoosh\n")
    else:
        print('Encoder: Pillow (pip install "pyvips[binary]" for MozJPEG and smaller files)\n')

    base = args.target if args.target.is_dir() else args.target.parent
    total_old = total_new = 0

    for src in pngs:
        if args.out:
            dest = args.out / src.relative_to(base).with_suffix(".jpg")
        else:
            dest = src.with_suffix(".jpg")

        if dest.exists() and not args.overwrite:
            print(f"skip   {src.name} (already converted; use --overwrite)")
            continue

        try:
            old, new = convert(src, dest, args)
        except Exception as e:  # keep going if one file is broken
            print(f"ERROR  {src.name}: {e}")
            continue

        total_old += old
        total_new += new
        print(f"ok     {src.name}: {human(old)} -> {human(new)}  ({change(old, new)})")

    if total_old:
        print(f"\nTotal: {human(total_old)} -> {human(total_new)}  ({change(total_old, total_new)})")


if __name__ == "__main__":
    main()
