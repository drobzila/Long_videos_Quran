"""
quran_final_v3.py
-----------------
مولد فيديوهات القرآن الطويلة.

الإعدادات الافتراضية:
  - المقرئ: الحصري (ar.abdulsamad)
  - الخط: Amiri / Amiri-Bold
  - لا يتم حذف أو قص أي صمت من التسجيلات.

المتطلبات:
    pip install requests mutagen pillow arabic_reshaper python-bidi
    resvg في PATH أو عبر RESVG_BIN
    ffmpeg في PATH
"""

import argparse
import concurrent.futures as cf
import functools
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Tuple

import requests
from mutagen.mp3 import MP3
from PIL import Image, ImageDraw, ImageFilter, ImageFont, features

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    HAS_SHAPING = True
except ImportError:
    HAS_SHAPING = False

HAS_RAQM = bool(features.check("raqm"))

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

BISMILLAH = "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"
# Al Quran Cloud identifies global ayah 1 (Al-Fatihah 1:1) as Bismillah.
# Use the same Minshawi Murattal edition as the selected reciter.
BISMILLAH_AUDIO_URL = (
    "https://www.everyayah.com/data/Minshawy_Murattal_128kbps/001001.mp3"
)
AUDIO_DIR = "audio_temp"
FADE_DURATION_SEC = 0.4
QURAN_FONT = os.environ.get("QURAN_FONT", "")


@dataclass
class Ayah:
    number_in_surah: int
    text: str
    audio_url: str
    audio_path: str = ""
    duration: float = 0.0


def fetch_surah_data(surah_number: int, reciter: str) -> dict:
    url = f"https://api.alquran.cloud/v1/surah/{surah_number}/{reciter}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()["data"]


def download_one(ayah: Ayah):
    if not os.path.exists(ayah.audio_path):
        r = requests.get(ayah.audio_url, stream=True, timeout=30)
        r.raise_for_status()
        with open(ayah.audio_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)
    ayah.duration = MP3(ayah.audio_path).info.length
    return ayah


def download_all_parallel(ayahs, max_workers=8):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    with cf.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(download_one, a) for a in ayahs]
        for fut in cf.as_completed(futures):
            fut.result()


def download_bismillah() -> Tuple[str, float]:
    os.makedirs(AUDIO_DIR, exist_ok=True)
    path = os.path.join(AUDIO_DIR, "bismillah_ar_minshawi.mp3")
    if not os.path.exists(path):
        r = requests.get(BISMILLAH_AUDIO_URL, stream=True, timeout=30)
        r.raise_for_status()
        with open(path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)
    return path, MP3(path).info.length


def load_colored_motif(svg_path: str, color=PATTERN_COLOR, size=1024) -> Image.Image:
    if shutil.which(RESVG_BIN) is None:
        raise RuntimeError(f"لم يتم العثور على {RESVG_BIN} في PATH.")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_png = os.path.join(tmp, "motif.png")
        result = subprocess.run(
            [RESVG_BIN, svg_path, tmp_png, "-w", str(size), "-h", str(size)],
            capture_output=True, text=True,
        )
        if result.returncode != 0 or not os.path.exists(tmp_png):
            raise RuntimeError(f"resvg فشل: {result.stderr}")
        raw = Image.open(tmp_png).convert("RGBA")

    alpha = raw.split()[3]
    colored = Image.new("RGBA", raw.size, color + (0,))
    colored.putalpha(alpha)
    return colored


def shape_arabic(text: str) -> str:
    if not HAS_SHAPING:
        return text
    reshaped = arabic_reshaper.reshape(text)
    return reshaped if HAS_RAQM else get_display(reshaped)


def text_layout_kwargs() -> dict:
    return {"direction": "rtl"} if HAS_RAQM else {}


BISMILLAH_PREFIXES = (
    BISMILLAH,
    "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
    "بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ",
    "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ",
    "بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ",
)


def display_ayah_text(text: str, surah_number: int, number_in_surah: int) -> str:
    """تجنب عرض البسملة مرتين؛ لا نلمس الصوت أو مدته."""
    text = text.strip()
    if surah_number in (1, 9) or number_in_surah != 1:
        return text

    for prefix in BISMILLAH_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix):].lstrip(" \u0610\u0611\u0612\u0613\u0614\u0615\u0616\u0617\u0618\u0619\u061a\u061b\u061c\u061d\u061e\u061f\u0640")

    return text


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


def build_base_cached_background(w, h) -> Image.Image:
    img = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))

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


def build(
    surah_number: int,
    reciter: str,
    svg_path: str,
    out_path: str,
    gpu_accel: str = "none",
):
    print(f"[*] جلب بيانات سورة رقم {surah_number}...")
    data = fetch_surah_data(surah_number, reciter)
    surah_name = data["name"]

    ayahs = [
        Ayah(
            number_in_surah=a["numberInSurah"],
            text=a["text"],
            audio_url=a["audio"],
            audio_path=os.path.join(AUDIO_DIR, f"ayah_{a['numberInSurah']}.mp3"),
        )
        for a in data["ayahs"]
    ]

    print("[*] تحميل الصوتيات بالتوازي...")
    download_all_parallel(ayahs)

    bismillah_path = None
    bismillah_duration = 0.0
    if surah_number not in (1, 9):
        print("[*] تحميل تلاوة البسملة...")
        bismillah_path, bismillah_duration = download_bismillah()

    concat_list = os.path.join(AUDIO_DIR, "files.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        if bismillah_path:
            f.write(f"file '{os.path.abspath(bismillah_path)}'\n")
        for a in ayahs:
            f.write(f"file '{os.path.abspath(a.audio_path)}'\n")

    full_audio = os.path.join(AUDIO_DIR, "full_audio.m4a")
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c:a", "aac", full_audio,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    vcodec = "libx264"
    if gpu_accel == "nvidia":
        vcodec = "h264_nvenc"
    elif gpu_accel == "qsv":
        vcodec = "h264_qsv"

    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-",
        "-i", full_audio,
        "-c:v", vcodec, "-pix_fmt", "yuv420p", "-preset", "fast",
        "-c:a", "aac", "-shortest",
        out_path,
    ]

    print(f"[*] بدء الترميز باستخدام ({vcodec})...")
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    tasks = []
    global_frame_counter = 0

    # عرض البسملة ومزامنة الفيديو معها قبل الآية الأولى.
    if bismillah_path:
        bismillah_frames = int(bismillah_duration * FPS)
        fade_frames = max(1, int(FADE_DURATION_SEC * FPS))
        for f in range(bismillah_frames):
            global_t = global_frame_counter / FPS
            frames_to_end = bismillah_frames - f
            opacity_in = min(1.0, f / fade_frames)
            opacity_out = min(1.0, max(0.0, frames_to_end / fade_frames))
            opacity = min(opacity_in, opacity_out)
            tasks.append(
                (
                    global_frame_counter,
                    global_t,
                    BISMILLAH,
                    f"📖 سورة {surah_name}",
                    opacity,
                )
            )
            global_frame_counter += 1

    for idx, ayah in enumerate(ayahs):
        info_text = f"📖 سورة {surah_name} - آية {ayah.number_in_surah}"
        text = display_ayah_text(ayah.text, surah_number, ayah.number_in_surah)
        total_ayah_frames = int(ayah.duration * FPS)
        fade_frames = max(1, int(FADE_DURATION_SEC * FPS))

        for f in range(total_ayah_frames):
            global_t = global_frame_counter / FPS
            frames_from_start = f
            frames_to_end = total_ayah_frames - f
            opacity_in = min(1.0, max(0.0, frames_from_start / fade_frames))
            opacity_out = min(1.0, max(0.0, frames_to_end / fade_frames))
            opacity = min(opacity_in, opacity_out)

            tasks.append(
                (global_frame_counter, global_t, text, info_text, opacity)
            )
            global_frame_counter += 1

    num_workers = min(os.cpu_count() or 4, 8)
    chunk_size = 60

    print(f"[*] المعالجة جارية بـ {num_workers} process حقيقية...")
    try:
        with cf.ProcessPoolExecutor(
            max_workers=num_workers,
            initializer=_worker_init,
            initargs=(svg_path,),
        ) as pool:
            for start in range(0, len(tasks), chunk_size):
                chunk = tasks[start : start + chunk_size]
                for _, frame_bytes in pool.map(render_frame_task, chunk):
                    process.stdin.write(frame_bytes)
    finally:
        process.stdin.close()
        process.wait()

    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg فشل برمز خروج {process.returncode}")

    print(f"[OK] تم إنشاء الفيديو: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="مولد فيديوهات القرآن الطويلة")
    parser.add_argument("--surah", type=int, required=True)
    parser.add_argument("--reciter", default="ar.husary")
    parser.add_argument("--svg", default="assets/Tile-Derivative-8.svg")
    parser.add_argument("--out", default="quran_output.mp4")
    parser.add_argument("--gpu", choices=["none", "nvidia", "qsv"], default="none")
    args = parser.parse_args()
    build(args.surah, args.reciter, args.svg, args.out, args.gpu)


if __name__ == "__main__":
    main()
