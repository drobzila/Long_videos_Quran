"""Quran API access."""

import requests

from .config import Ayah


def fetch_surah_data(surah_number: int, reciter: str) -> dict:
    url = f"https://api.alquran.cloud/v1/surah/{surah_number}/{reciter}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()["data"]


def build_ayahs(data: dict) -> list[Ayah]:
    return [
        Ayah(
            number_in_surah=ayah["numberInSurah"],
            text=ayah["text"],
            audio_url=ayah["audio"],
        )
        for ayah in data["ayahs"]
    ]
