"""End-card image creation and loading using Pillow."""

import os
from PIL import Image, ImageDraw, ImageFont

from .config import BRAND_COLOR, BRAND_NAME, HEIGHT, WIDTH
from .arabic import load_font, shape_arabic, text_layout_kwargs


def create_end_card(image_path: str | None = None) -> Image.Image:
    """Load a user image or create a simple Pillow-generated end card."""
    if image_path and os.path.isfile(image_path):
        return Image.open(image_path).convert("RGB").resize((WIDTH, HEIGHT), Image.LANCZOS)

    image = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    layout = text_layout_kwargs()
    title = shape_arabic("جزاكم الله خيرًا")
    channel = shape_arabic(BRAND_NAME)

    title_font = load_font(78)
    channel_font = load_font(42)
    title_box = draw.textbbox((0, 0), title, font=title_font, **layout)
    channel_box = draw.textbbox((0, 0), channel, font=channel_font, **layout)

    title_w = title_box[2] - title_box[0]
    channel_w = channel_box[2] - channel_box[0]
    draw.text(((WIDTH - title_w) / 2, HEIGHT * 0.42), title, font=title_font, fill=(255, 255, 255), **layout)
    draw.text(((WIDTH - channel_w) / 2, HEIGHT * 0.56), channel, font=channel_font, fill=BRAND_COLOR, **layout)
    return image
