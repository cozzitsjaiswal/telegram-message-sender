"""Convert Furaya PNG logo to a proper multi-size .ico file."""
from PIL import Image
import sys, pathlib

src = pathlib.Path(r"C:\Users\NazaraX\.gemini\antigravity\brain\0fa2f188-f2a7-4299-bd39-dc6f66bd2b31\furaya_logo_1774343390770.png")
out = pathlib.Path(r"C:\Users\NazaraX\telegram-message-sender\furaya.ico")

img = Image.open(src).convert("RGBA")

# ICO needs these exact sizes for Windows
sizes = [(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)]
img.save(str(out), format="ICO", sizes=sizes)
print(f"ICO saved: {out}  ({out.stat().st_size//1024} KB)")
