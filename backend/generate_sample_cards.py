"""
Script para gerar cartas de exemplo usando PIL.
Executa: python generate_sample_cards.py
"""
from PIL import Image, ImageDraw, ImageFont
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_cards")
os.makedirs(OUTPUT_DIR, exist_ok=True)

CARDS = [
    ("A", "♠", (0, 0, 0)),
    ("K", "♥", (200, 30, 30)),
    ("Q", "♦", (200, 30, 30)),
    ("J", "♣", (0, 0, 0)),
    ("10", "♠", (0, 0, 0)),
    ("7", "♥", (200, 30, 30)),
    ("3", "♣", (0, 0, 0)),
    ("5", "♦", (200, 30, 30)),
]


def draw_card(rank: str, suit: str, color: tuple) -> Image.Image:
    w, h = 200, 300
    img = Image.new("RGB", (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Borda arredondada simulada
    draw.rectangle([4, 4, w - 5, h - 5], outline=(180, 180, 180), width=3)

    try:
        font_large = ImageFont.truetype("arial.ttf", 60)
        font_small = ImageFont.truetype("arial.ttf", 28)
    except OSError:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Canto superior esquerdo
    draw.text((12, 8), rank, fill=color, font=font_small)
    draw.text((12, 38), suit, fill=color, font=font_small)

    # Centro
    draw.text((w // 2 - 25, h // 2 - 40), rank, fill=color, font=font_large)
    draw.text((w // 2 - 18, h // 2 + 10), suit, fill=color, font=font_large)

    # Canto inferior direito (invertido)
    draw.text((w - 35, h - 40), rank, fill=color, font=font_small)
    draw.text((w - 35, h - 70), suit, fill=color, font=font_small)

    return img


for rank, suit, color in CARDS:
    img = draw_card(rank, suit, color)
    safe_suit = suit.replace("♠", "spades").replace("♥", "hearts").replace("♦", "diamonds").replace("♣", "clubs")
    path = os.path.join(OUTPUT_DIR, f"{rank}_{safe_suit}.jpg")
    img.save(path, "JPEG", quality=95)
    print(f"Gerado: {path}")

print(f"\n{len(CARDS)} cartas geradas em '{OUTPUT_DIR}'")
