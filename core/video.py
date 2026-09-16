"""FFmpeg video assembly and encoding."""

import os
import subprocess

from .audio import build_audio_concat_list
from .config import AUDIO_DIR, FPS, HEIGHT, WIDTH
from .renderer import build_frame_tasks, render_tasks_to_process


def build_full_audio(ayahs, bismillah_path: str | None) -> str:
    concat_list = build_audio_concat_list(ayahs, bismillah_path)
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

    try:
        render_tasks_to_process(process, tasks, svg_path)
    finally:
        process.stdin.close()
        process.wait()

    if process.returncode != 0:
        raise RuntimeError(f"ffmpeg فشل برمز خروج {process.returncode}")


def build_video(ayahs, surah_name: str, bismillah_path: str | None, svg_path: str, out_path: str, gpu_accel: str = "none"):
    full_audio = build_full_audio(ayahs, bismillah_path)
    tasks = build_frame_tasks(ayahs, surah_name)
    encode_video(tasks, svg_path, full_audio, out_path, gpu_accel)
