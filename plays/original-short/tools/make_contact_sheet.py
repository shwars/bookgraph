"""Make a local QA contact sheet of all character sprites on a dark ground."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT = Path(__file__).resolve().parents[1]
manifest = json.loads((PROJECT / "assets" / "manifest.json").read_text(encoding="utf-8"))
items = [(key, value) for key, value in manifest["assets"].items() if value["kind"] == "character"]
columns = 10
cell_w, cell_h = 150, 220
rows = (len(items) + columns - 1) // columns
sheet = Image.new("RGBA", (columns * cell_w, rows * cell_h), "#2a2723")
draw = ImageDraw.Draw(sheet)
for index, (key, asset) in enumerate(items):
    image = Image.open(PROJECT / asset["file"]).convert("RGBA")
    left, top, right, bottom = asset["bounds"]
    image = image.crop((left, top, right, bottom))
    image.thumbnail((cell_w - 14, cell_h - 34), Image.LANCZOS)
    x = (index % columns) * cell_w + (cell_w - image.width) // 2
    y = (index // columns) * cell_h + 8
    sheet.alpha_composite(image, (x, y))
    draw.text(((index % columns) * cell_w + 4, (index // columns) * cell_h + cell_h - 18),
              key, fill="#f4e8d0")
sheet.save(PROJECT / "qa" / "contact-sheet.png")
print(PROJECT / "qa" / "contact-sheet.png")
