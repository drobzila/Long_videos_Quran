import os
import pickle
from datetime import datetime, timezone

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


API_SERVICE_NAME = "youtube"
API_VERSION = "v3"


def load_creds():
    token_file = os.environ.get("YT_TOKEN_FILE", "token.pkl")
    with open(token_file, "rb") as f:
        return pickle.load(f)


def get_surah_name(surah_number: int) -> str:
    import requests

    url = f"https://api.alquran.cloud/v1/surah/{surah_number}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    return response.json()["data"]["name"]


def upload_video(file_path: str, surah_number: int, publish_at: str):
    if not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)

    dt = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("PUBLISH_AT must include a timezone")
    dt = dt.astimezone(timezone.utc)
    if dt <= datetime.now(timezone.utc):
        raise ValueError("PUBLISH_AT must be in the future")

    surah_name = get_surah_name(surah_number)
    title = f"{surah_name} | القرآن الكريم | نسمات القرآن"
    description = (
        f"تلاوة سورة {surah_name} بصوت الشيخ محمد صديق المنشاوي.\n\n"
        "القرآن الكريم — نسمات القرآن\n\n"
        "#القرآن #تلاوة #المنشاوي #سورة"
    )

    credentials = load_creds()
    youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

    publish_rfc3339 = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    status = {
        "privacyStatus": "private",
        "publishAt": publish_rfc3339,
        "selfDeclaredMadeForKids": False,
    }

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "categoryId": "22",
        },
        "status": status,
    }

    response = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(file_path, mimetype="video/mp4", resumable=True),
    ).execute()

    video_id = response["id"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    print(f"[OK] YouTube video: {video_url}")
    print(f"[OK] Scheduled UTC: {publish_rfc3339}")

    with open("youtube_url.txt", "w", encoding="utf-8") as f:
        f.write(video_url)

    return video_id, video_url


if __name__ == "__main__":
    upload_video(
        os.environ.get("VIDEO_FILE", "surah.mp4"),
        int(os.environ["SURAH"]),
        os.environ["PUBLISH_AT"],
    )
