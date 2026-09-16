"""Arabic shaping, layout helpers, and font loading."""

import functools
import os

from PIL import ImageFont, features

from .config import QURAN_FONT

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_SHAPING = True
except ImportError:
    HAS_SHAPING = False

HAS_RAQM = bool(features.check("raqm"))


def shape_arabic(text: str) -> str:
    if not HAS_SHAPING:
        return text
    reshaped = arabic_reshaper.reshape(text)
    return reshaped if HAS_RAQM else get_display(reshaped)


def text_layout_kwargs() -> dict:
    return {"direction": "rtl"} if HAS_RAQM else {}


@functools.lru_cache(maxsize=None)
def load_font(size: int):
    candidates = [
        QURAN_FONT,
        "/usr/share/fonts/truetype/amiri/Amiri-Bold.ttf",
        "/usr/share/fonts/truetype/amiri/Amiri-Regular.ttf",
        "/usr/share/fonts/opentype/amiri/Amiri-Bold.ttf",
        "/usr/share/fonts/opentype/amiri/Amiri-Regular.ttf",
        "assets/Amiri-Bold.ttf",
        "assets/Amiri-Regular.ttf",
        "Amiri-Bold.ttf",
        "Amiri-Regular.ttf",
        "C:/Windows/Fonts/amiri-bold.ttf",
        "C:/Windows/Fonts/amiri-regular.ttf",
    ]

    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return ImageFont.truetype(candidate, size)

    raise RuntimeError(
        "لم يتم العثور على خط عربي Amiri. "
        "ثبّت fonts-hosny-amiri على Ubuntu أو حدّد QURAN_FONT."
    )
