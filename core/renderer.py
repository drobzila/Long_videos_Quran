"""Per-frame Quran video rendering."""

import concurrent.futures as cf
from typing import Tuple

from PIL import Image, ImageDraw

from .arabic import load_font, shape_arabic, text_layout_kwargs
from .background import build_base_cached_background, load_colored_motif
from .config import (
    BRAND_COLOR,
    BRAND_NAME,
    BRAND_SECONDARY,
    CENTER_OPACITY,
    CENTER_SIZE,
    FADE_DURATION_SEC,
    FPS,
    FULL_ROTATIONS_PER_SEC,
    HEIGHT,
    INFO_COLOR,
    TEXT_COLOR,
    WIDTH,
)

_W_MOTIF = None
_W_BASE_BG = None


def _worker_init(svg_path: str):
    global _W_MOTIF, _W_BASE_BG
    _W_MOTIF = load_colored_motif(svg_path)
    _W_BASE_BG = build_base_cached_background(WIDTH, HEIGHT)


def render_frame_task(task_args: Tuple) -> Tuple[int, bytes]:
    frame_idx, global_t, main_text, info_text, text_opacity = task_args
    motif, base_bg = _W_MOTIF, _W_BASE_BG

    angle = 360 * FULL_ROTATIONS_PER_SEC * global_t
    tile = motif.resize((CENTER_SIZE, CENTER_SIZE), Image.LANCZOS).rotate(
        angle, expand=True, resample=Image.BICUBIC
    )
    r, g, b, a = tile.split()
    a = a.point(lambda p: int(p * CENTER_OPACITY))
    tile = Image.merge("RGBA", (r, g, b, a))

    frame = base_bg.copy()
    x = (WIDTH - tile.width) // 2
    y = (HEIGHT - tile.height) // 2
    frame.alpha_composite(tile, (x, y))

    # هوية القناة: ثابتة وهادئة حتى لا تنافس الآية.
    branding = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(branding)
    layout = text_layout_kwargs()

    title = shape_arabic("القرآن الكريم")
    title_font = load_font(34)
    tb = bdraw.textbbox((0, 0), title, font=title_font, **layout)
    tw = tb[2] - tb[0]
    bdraw.text(
        ((WIDTH - tw) / 2, 48),
        title,
        font=title_font,
        fill=BRAND_COLOR + (235,),
        **layout,
    )

    channel = shape_arabic(BRAND_NAME)
    channel_font = load_font(27)
    cb = bdraw.textbbox((0, 0), channel, font=channel_font, **layout)
    cw = cb[2] - cb[0]
    bdraw.text(
        ((WIDTH - cw) / 2, HEIGHT - 76),
        channel,
        font=channel_font,
        fill=BRAND_SECONDARY + (225,),
        **layout,
    )
    frame.alpha_composite(branding)

    if text_opacity > 0.001:
        text_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)
        layout = text_layout_kwargs()

        box_w = WIDTH * 0.72
        shaped_main = shape_arabic(f"« {main_text} »")
        font_size = 54
        font_main = load_font(font_size)
        bbox = draw.textbbox((0, 0), shaped_main, font=font_main, **layout)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        max_w = box_w - 100

        while tw > max_w and font_size > 20:
            font_size -= 2
            font_main = load_font(font_size)
            bbox = draw.textbbox((0, 0), shaped_main, font=font_main, **layout)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

        alpha_val = int(255 * text_opacity)
        cx, cy = WIDTH / 2, HEIGHT / 2 - 25
        draw.text(
            (cx - tw / 2, cy - th / 2),
            shaped_main,
            font=font_main,
            fill=TEXT_COLOR + (alpha_val,),
            **layout,
        )

        shaped_info = shape_arabic(info_text)
        font_info = load_font(24)
        ibbox = draw.textbbox((0, 0), shaped_info, font=font_info, **layout)
        iw = ibbox[2] - ibbox[0]
        draw.text(
            (cx - iw / 2, cy + th / 2 + 28),
            shaped_info,
            font=font_info,
            fill=INFO_COLOR + (alpha_val,),
            **layout,
        )

        frame.alpha_composite(text_layer)

    return frame_idx, frame.convert("RGB").tobytes()


def build_frame_tasks(ayahs, surah_name: str):
    tasks = []
    global_frame_counter = 0

    # نعرض نص كل آية كما هو، بما فيه البسملة في بداية الآية الأولى.
    # صوت البسملة المنفصل يسبق صوت الآية الأولى، بينما العرض المرئي يبقى مرة واحدة فقط.
    for ayah in ayahs:
        info_text = f"📖 سورة {surah_name} - آية {ayah.number_in_surah}"
        text = ayah.text.strip()
        total_ayah_frames = int(ayah.duration * FPS)
        fade_frames = max(1, int(FADE_DURATION_SEC * FPS))

        for frame_in_ayah in range(total_ayah_frames):
            global_t = global_frame_counter / FPS
            frames_from_start = frame_in_ayah
            frames_to_end = total_ayah_frames - frame_in_ayah
            opacity_in = min(1.0, max(0.0, frames_from_start / fade_frames))
            opacity_out = min(1.0, max(0.0, frames_to_end / fade_frames))
            opacity = min(opacity_in, opacity_out)

            tasks.append(
                (global_frame_counter, global_t, text, info_text, opacity)
            )
            global_frame_counter += 1

    return tasks


def render_tasks_to_process(process, tasks, svg_path: str, num_workers: int | None = None):
    workers = num_workers or min(cf.os.cpu_count() if hasattr(cf, "os") else 4, 8)
    if workers < 1:
        workers = 1

    chunk_size = 60
    print(f"[*] المعالجة جارية بـ {workers} process حقيقية...")
    with cf.ProcessPoolExecutor(
        max_workers=workers,
        initializer=_worker_init,
        initargs=(svg_path,),
    ) as pool:
        for start in range(0, len(tasks), chunk_size):
            chunk = tasks[start : start + chunk_size]
            for _, frame_bytes in pool.map(render_frame_task, chunk):
                process.stdin.write(frame_bytes)
