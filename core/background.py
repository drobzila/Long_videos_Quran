"""Background and motif rendering helpers."""

import os
import shutil
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFilter

from .config import (
    BG_BOTTOM,
    BG_TOP,
    BOX_BORDER,
    BOX_BORDER_WIDTH,
    BOX_FILL,
    BOX_RADIUS,
    BRAND_COLOR,
    PATTERN_COLOR,
    RESVG_BIN,
)


def load_colored_motif(svg_path: str, color=PATTERN_COLOR, size=1024) -> Image.Image:
    if shutil.which(RESVG_BIN) is None:
        raise RuntimeError(f"لم يتم العثور على {RESVG_BIN} في PATH.")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_png = os.path.join(tmp, "motif.png")
        result = subprocess.run(
            [RESVG_BIN, svg_path, tmp_png, "-w", str(size), "-h", str(size)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not os.path.exists(tmp_png):
            raise RuntimeError(f"resvg فشل: {result.stderr}")
        raw = Image.open(tmp_png).convert("RGBA")

    alpha = raw.split()[3]
    colored = Image.new("RGBA", raw.size, color + (0,))
    colored.putalpha(alpha)
    return colored


def build_base_cached_background(w, h) -> Image.Image:
    img = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        t = y / h
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

    # لمسات هادئة جدًا أعلى وأسفل الشاشة للحفاظ على البساطة مع هوية واضحة.
    draw.line([(220, 92), (1700, 92)], fill=BRAND_COLOR + (45,), width=2)
    draw.line([(220, h - 92), (1700, h - 92)], fill=BRAND_COLOR + (30,), width=2)

    box_w, box_h = w * 0.72, h * 0.30
    x0 = (w - box_w) / 2
    y0 = (h - box_h) / 2
    box_rect = (x0, y0, x0 + box_w, y0 + box_h)

    shadow_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow_layer)
    sdraw.rounded_rectangle(
        (x0, y0 + 14, x0 + box_w, y0 + box_h + 14),
        radius=BOX_RADIUS,
        fill=(20, 60, 25, 90),
    )
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(22))
    img.alpha_composite(shadow_layer)

    box_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(box_layer)
    bdraw.rounded_rectangle(
        box_rect,
        radius=BOX_RADIUS,
        fill=BOX_FILL,
        outline=BOX_BORDER,
        width=BOX_BORDER_WIDTH,
    )
    img.alpha_composite(box_layer)
    return img
