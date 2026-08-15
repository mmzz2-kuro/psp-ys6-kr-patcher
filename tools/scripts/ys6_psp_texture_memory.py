#!/usr/bin/env python3
"""Render a raw PSP 32-bit swizzled texture memory dump as PNG."""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

try:
    from tools.scripts.ys6_mig_texture import unswizzle_8bpp
    from tools.scripts.ys6_menu_image_roundtrip import psp_dxt3_to_pc
except ModuleNotFoundError:
    from ys6_mig_texture import unswizzle_8bpp
    from ys6_menu_image_roundtrip import psp_dxt3_to_pc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=256)
    parser.add_argument("--height", type=int, default=256)
    parser.add_argument("--channel-order", choices=("rgba", "bgra"), default="rgba")
    parser.add_argument("--format", choices=("rgba32", "psp-dxt3"), default="rgba32")
    args = parser.parse_args()

    expected = args.width * args.height * (4 if args.format == "rgba32" else 1)
    stored = args.input.read_bytes()
    if len(stored) < expected:
        raise ValueError(f"input is too short: {len(stored)} < {expected}")
    if args.format == "psp-dxt3":
        image = Image.frombytes("RGBA", (args.width, args.height),
                                psp_dxt3_to_pc(stored[:expected]), "bcn", (2,))
    else:
        linear = unswizzle_8bpp(stored[:expected], args.width * 4, args.height)
        image = Image.frombytes("RGBA", (args.width, args.height), linear)
    if args.channel_order == "bgra":
        red, green, blue, alpha = image.split()
        image = Image.merge("RGBA", (blue, green, red, alpha))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
