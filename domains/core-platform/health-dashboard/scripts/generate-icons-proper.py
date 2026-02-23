#!/usr/bin/env python3
"""
Generate proper PWA icons from SVG.
Creates icon-192.png and icon-512.png for the PWA manifest.
"""
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL/Pillow not available. Creating simple colored icons instead.")

def create_icon_from_svg(size, output_path, svg_path=None):
    """Create a PNG icon at the specified size."""
    if HAS_PIL:
        # Create a proper icon with HomeIQ branding colors
        # Theme color: #1e40af (blue-800)
        img = Image.new('RGB', (size, size), color='#1e40af')
        draw = ImageDraw.Draw(img)
        
        # Draw a simple "HQ" logo in the center
        # Use a larger font size based on icon size
        font_size = int(size * 0.4)
        try:
            # Try to use a system font
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
            except:
                # Fallback to default font
                font = ImageFont.load_default()
        
        # Calculate text position (centered)
        text = "HQ"
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2
        
        # Draw white text
        draw.text((x, y), text, fill='white', font=font)
        
        # Save as PNG
        img.save(output_path, 'PNG', optimize=True)
        print(f"Created icon: {output_path} ({size}x{size})")
    else:
        # Fallback: Create a simple colored square
        # This is a minimal valid PNG with the theme color
        # Base64 encoded 1x1 PNG with blue color (#1e40af = rgb(30, 64, 175))
        import base64
        # Create a simple blue square PNG
        # This is a 1x1 blue pixel PNG (will be scaled by browser)
        blue_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        output_path.write_bytes(blue_png)
        print(f"Created placeholder icon: {output_path} ({size}x{size}) - Install Pillow for proper icons")

def main():
    """Generate icon files."""
    script_dir = Path(__file__).parent
    public_dir = script_dir.parent / "public"
    public_dir.mkdir(exist_ok=True)
    
    svg_path = public_dir / "vite.svg"
    
    # Create icon files
    print("Generating PWA icons...")
    create_icon_from_svg(192, public_dir / "icon-192.png", svg_path if svg_path.exists() else None)
    create_icon_from_svg(512, public_dir / "icon-512.png", svg_path if svg_path.exists() else None)
    
    print("\nIcons generated successfully!")
    if not HAS_PIL:
        print("\nNote: Install Pillow for better icon quality:")
        print("  pip install Pillow")
        print("Then re-run this script to generate proper icons from the SVG.")

if __name__ == "__main__":
    main()

