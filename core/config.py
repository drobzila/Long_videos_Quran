"""Shared configuration and data models."""

import os
from dataclasses import dataclass

WIDTH, HEIGHT = 1920, 1080
FPS = 30
RESVG_BIN = os.environ.get("RESVG_BIN", "resvg")

BG_TOP = (242, 255, 247)
BG_BOTTOM = (255, 255, 255)
PATTERN_COLOR = (46, 125, 50)
CENTER_SIZE = 780
CENTER_OPACITY = 0.55
FULL_ROTATIONS_PER_SEC = 0.02

BOX_FILL = (255, 255, 255, 190)
BOX_BORDER = (27, 94, 32, 130)
BOX_BORDER_WIDTH = 2
BOX_RADIUS = 36
TEXT_COLOR = (27, 94, 32)
INFO_COLOR = (85, 85, 85)
BRAND_COLOR = (27, 94, 32)
BRAND_SECONDARY = (95, 105, 98)

BISMILLAH = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
BISMILLAH_AUDIO_URL = "https://www.everyayah.com/data/Minshawy_Murattal_128kbps/001001.mp3"
AUDIO_DIR = "audio_temp"
FADE_DURATION_SEC = 0.4
QURAN_FONT = os.environ.get("QURAN_FONT", "")

BRAND_TITLE = "القرآن الكريم"
BRAND_NAME = "نسمات القرآن"


@dataclass
class Ayah:
    number_in_surah: int
    text: str
    audio_url: str
    audio_path: str = ""
    duration: float = 0.0
