"""Generate placeholder PNG icons for the ContextOS browser extension.

Usage:
    python generate_icons.py

Produces: icons/icon16.png, icons/icon48.png, icons/icon128.png

Each is a solid indigo square (#4f46e5) sized appropriately.
"""

import struct
import zlib
from pathlib import Path


def create_png(size: int) -> bytes:
    """Create a minimal valid PNG of a solid-colored square."""

    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))

    raw = b""
    for _ in range(size):
        raw += b"\x00"  # filter byte
        raw += b"\x4f\x46\xe5" * size  # RGB pixel

    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")

    return sig + ihdr + idat + iend


def main():
    out = Path(__file__).parent / "icons"
    out.mkdir(exist_ok=True)

    for size in (16, 48, 128):
        path = out / f"icon{size}.png"
        path.write_bytes(create_png(size))
        print(f"Created {path} ({size}x{size})")


if __name__ == "__main__":
    main()
