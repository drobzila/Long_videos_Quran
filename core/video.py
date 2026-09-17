"""FFmpeg video assembly, encoding, and Pillow end card."""

import os
import subprocess
import tempfile

from .audio import build_audio_concat_list
from .config import AUDIO_DIR, FPS, HEIGHT, WIDTH
from .end_card import create_end_card
from .renderer import build_frame_tasks, render_tasks_to_process


def build_full_audio(ayahs, bismillah_path: str | None) -> str:
    concat_list = build_audio_concat_list(ayahs, bismillah_path)
    full_audio = os.path.join(AUDIO_DIR, "full_audio.m4a")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c:a", "aac", full_audio],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return full_audio


def select_video_codec(gpu_accel: str) -> str:
    if gpu_accel == "nvidia":
        return "h264_nvenc"
    if gpu_accel == "qsv":
        return "h264_qsv"
    return "libx264"


def encode_video(tasks, svg_path: str, full_audio: str, out_path: str, gpu_accel: str = "none"):
    vcodec = select_video_codec(gpu_accel)
    cmd = [
        "ffmpeg", "-y", "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}", "-pix_fmt", "rgb24", "-r", str(FPS),
        "-i", "-", "-i", full_audio, "-c:v", vcodec, "-pix_fmt", "yuv420p",
        "-preset", "fast", "-c:a", "aac", "-shortest", out_path,
    ]
    print(f"[*] بدء الترميز باستخدام ({vcodec})...")
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        render_tasks_to_process(process, tasks, svg_path)
    finally:
        process.stdin.close()
        process.wait()
    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg فشل برمز خروج {process.returncode}")


def append_end_card(main_video: str, out_path: str, image_path: str | None, duration: float, gpu_accel: str):
    if duration <= 0:
        os.replace(main_video, out_path)
        return

    vcodec = select_video_codec(gpu_accel)
    with tempfile.TemporaryDirectory() as tmp:
        image_file = os.path.join(tmp, "end_card.png")
        create_end_card(image_path).save(image_file)
        end_video = os.path.join(tmp, "end_card.mp4")
        concat_file = os.path.join(tmp, "concat.txt")

        subprocess.run([
            "ffmpeg", "-y", "-loop", "1", "-i", image_file,
            "-t", str(duration), "-r", str(FPS), "-s", f"{WIDTH}x{HEIGHT}",
            "-c:v", vcodec, "-pix_fmt", "yuv420p", "-an", end_video,
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        with open(concat_file, "w", encoding="utf-8") as f:
            f.write(f"file '{os.path.abspath(main_video)}'\n")
            f.write(f"file '{os.path.abspath(end_video)}'\n")

        subprocess.run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
            "-c", "copy", out_path,
        ], check=True)


def build_video(ayahs, surah_name: str, bismillah_path: str | None, svg_path: str,
                out_path: str, gpu_accel: str = "none", end_image: str | None = None,
                end_duration: float = 5.0):
    full_audio = build_full_audio(ayahs, bismillah_path)
    tasks = build_frame_tasks(ayahs, surah_name)

    with tempfile.TemporaryDirectory() as tmp:
        main_video = os.path.join(tmp, "main_video.mp4")
        encode_video(tasks, svg_path, full_audio, main_video, gpu_accel)
        append_end_card(main_video, out_path, end_image, end_duration, gpu_accel)
