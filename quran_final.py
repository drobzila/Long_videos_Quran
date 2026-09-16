"""واجهة تشغيل مولد فيديوهات القرآن الطويلة.

تم تقسيم منطق المشروع إلى وحدات داخل مجلد core لتسهيل الصيانة والتطوير.

المتطلبات:
    pip install requests mutagen pillow arabic_reshaper python-bidi
    resvg في PATH أو عبر RESVG_BIN
    ffmpeg في PATH
"""

import argparse
import os

from core.audio import prepare_audio
from core.config import AUDIO_DIR
from core.quran_api import build_ayahs, fetch_surah_data
from core.video import build_video


def parse_args():
    parser = argparse.ArgumentParser(description="مولد فيديوهات القرآن الطويلة")
    parser.add_argument("--surah", type=int, required=True)
    parser.add_argument("--reciter", default="ar.husary")
    parser.add_argument("--svg", default="assets/Tile-Derivative-8.svg")
    parser.add_argument("--out", default="quran_output.mp4")
    parser.add_argument("--gpu", choices=["none", "nvidia", "qsv"], default="none")
    return parser.parse_args()


def build(surah_number: int, reciter: str, svg_path: str, out_path: str, gpu_accel: str = "none"):
    print(f"[*] جلب بيانات سورة رقم {surah_number}...")
    data = fetch_surah_data(surah_number, reciter)
    surah_name = data["name"]

    ayahs = build_ayahs(data)
    for ayah in ayahs:
        ayah.audio_path = os.path.join(
            AUDIO_DIR, f"ayah_{ayah.number_in_surah}.mp3"
        )

    print("[*] تحميل الصوتيات بالتوازي...")
    bismillah_path, _ = prepare_audio(ayahs, surah_number)

    build_video(
        ayahs=ayahs,
        surah_name=surah_name,
        bismillah_path=bismillah_path,
        svg_path=svg_path,
        out_path=out_path,
        gpu_accel=gpu_accel,
    )

    print(f"[OK] تم إنشاء الفيديو: {out_path}")


def main():
    args = parse_args()
    build(args.surah, args.reciter, args.svg, args.out, args.gpu)


if __name__ == "__main__":
    main()
