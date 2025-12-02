#!/usr/bin/env python3
"""
Generate PWA icons from SVG or create placeholder icons.
This script creates icon-192.png and icon-512.png for the PWA manifest.
"""
import base64
from pathlib import Path

# Simple 192x192 PNG placeholder (blue square with "HQ" text)
# This is a minimal valid PNG
ICON_192_PNG = base64.b64decode("""
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
""")

# Simple 512x512 PNG placeholder
ICON_512_PNG = base64.b64decode("""
iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==
""")

def create_icon_png(size, output_path):
    """Create a simple PNG icon placeholder."""
    # For now, create a minimal valid PNG
    # In production, you'd want to use PIL/Pillow to create proper icons
    # This is a 1x1 transparent PNG that will be scaled by the browser
    minimal_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    
    # Write placeholder - browsers will handle scaling
    output_path.write_bytes(minimal_png)
    print(f"Created placeholder icon: {output_path} ({size}x{size})")

def main():
    """Generate icon files."""
    public_dir = Path(__file__).parent.parent / "public"
    public_dir.mkdir(exist_ok=True)
    
    # Create icon files
    create_icon_png(192, public_dir / "icon-192.png")
    create_icon_png(512, public_dir / "icon-512.png")
    
    print("Icons generated successfully!")
    print("Note: These are placeholder icons. For production, use proper icon generation tools.")

if __name__ == "__main__":
    main()

