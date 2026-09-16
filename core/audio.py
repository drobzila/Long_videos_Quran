"""Audio downloading and duration handling."""

import concurrent.futures as cf
import os
from typing import Tuple

import requests
from mutagen.mp3 import MP3

from .config import AUDIO_DIR, BISMILLAH_AUDIO_URL, Ayah


def download_one(ayah: Ayah):
    if not os.path.exists(ayah.audio_path):
        response = requests.get(ayah.audio_url, stream=True, timeout=30)
        response.raise_for_status()
        with open(ayah.audio_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    file.write(chunk)
    ayah.duration = MP3(ayah.audio_path).info.length
    return ayah


def download_all_parallel(ayahs, max_workers=8):
    os.makedirs(AUDIO_DIR, exist_ok=True)
    with cf.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(download_one, ayah) for ayah in ayahs]
        for future in cf.as_completed(futures):
            future.result()


def download_bismillah() -> Tuple[str, float]:
    """تحميل بسملة المنشاوي لاستخدامها قبل صوت الآية الأولى، دون قص أو حذف."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    path = os.path.join(AUDIO_DIR, "bismillah_ar_minshawi.mp3")
    if not os.path.exists(path):
        response = requests.get(BISMILLAH_AUDIO_URL, stream=True, timeout=30)
        response.raise_for_status()
        with open(path, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 64):
                if chunk:
                    file.write(chunk)
    return path, MP3(path).info.length


def prepare_audio(ayahs, surah_number: int):
    download_all_parallel(ayahs)

    bismillah_path = None
    bismillah_duration = 0.0
    if surah_number not in (1, 9):
        bismillah_path, bismillah_duration = download_bismillah()
        ayahs[0].duration += bismillah_duration

    return bismillah_path, bismillah_duration


def build_audio_concat_list(ayahs, bismillah_path: str | None) -> str:
    concat_list = os.path.join(AUDIO_DIR, "files.txt")
    with open(concat_list, "w", encoding="utf-8") as file:
        if bismillah_path:
            file.write(f"file '{os.path.abspath(bismillah_path)}'\n")
        for ayah in ayahs:
            file.write(f"file '{os.path.abspath(ayah.audio_path)}'\n")
    return concat_list
