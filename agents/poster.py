"""
ポスターエージェント
- data/queue/から未投稿の投稿を1件取得
- Threads APIに投稿
- 投稿済みをdata/posted/に移動
"""

import json
import os
import time
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
QUEUE_DIR = BASE_DIR / "data" / "queue"
POSTED_DIR = BASE_DIR / "data" / "posted"

THREADS_USER_ID = os.environ["THREADS_USER_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
BASE_URL = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}"


def get_next_post() -> dict | None:
    """キューから最も古い投稿を1件取得"""
    queue_files = sorted(QUEUE_DIR.glob("*.json"))
    if not queue_files:
        return None
    data = json.loads(queue_files[0].read_text(encoding="utf-8"))
    data["_file"] = str(queue_files[0])
    return data


def create_container(text: str) -> str:
    resp = requests.post(
        f"{BASE_URL}/threads",
        params={"media_type": "TEXT", "text": text, "access_token": THREADS_ACCESS_TOKEN},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def publish_container(container_id: str) -> str:
    time.sleep(30)
    resp = requests.post(
        f"{BASE_URL}/threads_publish",
        params={"creation_id": container_id, "access_token": THREADS_ACCESS_TOKEN},
    )
    resp.raise_for_status()
    return resp.json()["id"]


def post_next():
    post = get_next_post()
    if not post:
        print("キューに投稿がありません")
        return None

    print(f"投稿中: {post['text'][:50]}...")
    container_id = create_container(post["text"])
    threads_id = publish_container(container_id)

    # 投稿済みに移動
    post["threads_post_id"] = threads_id
    post["posted_at"] = datetime.now().isoformat()
    post["status"] = "posted"

    posted_file = POSTED_DIR / Path(post["_file"]).name
    posted_file.write_text(json.dumps({k: v for k, v in post.items() if k != "_file"}, ensure_ascii=False, indent=2), encoding="utf-8")
    Path(post["_file"]).unlink()

    print(f"✅ 投稿完了: {threads_id}")
    return threads_id


if __name__ == "__main__":
    post_next()
