"""واجهة تشغيل مولد فيديوهات القرآن الطويلة."""

import argparse
import os
import random
import sys


def parse_args():
    parser = argparse.ArgumentParser(description="مولد فيديوهات القرآن")
    parser.add_argument("--surah", type=int, required=True)
    parser.add_argument("--reciter", default="ar.husary")
    parser.add_argument("--svg", default="assets/Tile-Derivative-8.svg")
    parser.add_argument("--out", default="quran_output.mp4")
    parser.add_argument("--gpu", choices=["none", "nvidia", "qsv"], default="none")
    parser.add_argument("--end-image", default=None, help="مسار صورة النهاية الاختيارية")
    parser.add_argument("--end-duration", type=float, default=None, help="مدة صورة النهاية بالثواني")
    parser.add_argument("--format", choices=["landscape", "shorts"], default="landscape",
                        help="landscape للفيديو الطويل أو shorts لفيديو عمودي قصير")
    parser.add_argument("--min-duration", type=float, default=4.0,
                        help="أقل مدة لمقطع shorts بالثواني")
    parser.add_argument("--max-duration", type=float, default=20.0,
                        help="أقصى مدة لمقطع shorts بالثواني")
    parser.add_argument("--seed", type=int, default=None,
                        help="بذرة اختيار المقطع لتكرار النتيجة")
    return parser.parse_args()


def build(surah_number: int, reciter: str, svg_path: str, out_path: str,
          gpu_accel: str = "none", end_image: str | None = None,
          end_duration: float = 5.0, video_format: str = "landscape",
          min_duration: float = 4.0, max_duration: float = 20.0,
          seed: int | None = None):
    # Set output geometry before importing core modules, whose config is read at import time.
    if end_duration is None:
        end_duration = 0.0 if video_format == "shorts" else 5.0
    if video_format == "shorts":
        if min_duration <= 0 or max_duration < min_duration:
            raise ValueError("يجب أن تكون حدود المدة موجبة، والحد الأقصى أكبر من الأدنى")
        os.environ["VIDEO_WIDTH"] = "1080"
        os.environ["VIDEO_HEIGHT"] = "1920"

    from core.audio import prepare_audio
    from core.config import AUDIO_DIR
    from core.quran_api import build_ayahs, fetch_surah_data
    from core.video import build_video

    print(f"[*] جلب بيانات سورة رقم {surah_number}...")
    data = fetch_surah_data(surah_number, reciter)
    surah_name = data["name"]

    ayahs = build_ayahs(data)
    for ayah in ayahs:
        ayah.audio_path = os.path.join(AUDIO_DIR, f"ayah_{ayah.number_in_surah}.mp3")

    print("[*] تحميل الصوتيات بالتوازي...")
    bismillah_path, _ = prepare_audio(ayahs, surah_number)

    if video_format == "shorts":
        rng = random.Random(seed)
        candidates = []
        for start in range(len(ayahs)):
            duration = 0.0
            for end in range(start, len(ayahs)):
                duration += ayahs[end].duration
                if duration > max_duration:
                    break
                if duration >= min_duration:
                    candidates.append((start, end + 1, duration))
        if not candidates:
            raise ValueError(
                f"لم يُعثر على مقطع كامل بين {min_duration:g} و{max_duration:g} ثانية"
            )
        # Keep each complete ayah and its original audio; favor clips near 12 seconds.
        best_distance = min(abs(item[2] - 12.0) for item in candidates)
        near_best = [item for item in candidates if abs(abs(item[2] - 12.0) - best_distance) < 2.0]
        start, end, clip_duration = rng.choice(near_best)
        ayahs = ayahs[start:end]
        if start > 0:
            bismillah_path = None
        print(
            f"[*] مقطع قصير: الآيات {ayahs[0].number_in_surah}-"
            f"{ayahs[-1].number_in_surah} ({clip_duration:.1f} ثانية)"
        )

    build_video(
        ayahs=ayahs,
        surah_name=surah_name,
        bismillah_path=bismillah_path,
        svg_path=svg_path,
        out_path=out_path,
        gpu_accel=gpu_accel,
        end_image=end_image,
        end_duration=end_duration,
    )
    print(f"[OK] تم إنشاء الفيديو: {out_path}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    build(args.surah, args.reciter, args.svg, args.out, args.gpu,
          args.end_image, args.end_duration, args.format, args.min_duration,
          args.max_duration, args.seed)


if __name__ == "__main__":
    main()
