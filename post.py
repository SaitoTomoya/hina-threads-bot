"""
Threads APIに自動投稿するスクリプト
GitHub Actionsから毎日実行される
"""

import requests
import json
import os
import time
from datetime import datetime

THREADS_USER_ID = os.environ["THREADS_USER_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]
BASE_URL = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}"


def create_container(text: str) -> str:
    """Step1: 投稿コンテナを作成"""
    resp = requests.post(
        f"{BASE_URL}/threads",
        params={
            "media_type": "TEXT",
            "text": text,
            "access_token": THREADS_ACCESS_TOKEN,
        },
    )
    resp.raise_for_status()
    container_id = resp.json()["id"]
    print(f"コンテナ作成: {container_id}")
    return container_id


def publish_container(container_id: str) -> str:
    """Step2: コンテナを公開して投稿"""
    time.sleep(30)  # API推奨の待機時間
    resp = requests.post(
        f"{BASE_URL}/threads_publish",
        params={
            "creation_id": container_id,
            "access_token": THREADS_ACCESS_TOKEN,
        },
    )
    resp.raise_for_status()
    post_id = resp.json()["id"]
    print(f"投稿完了: {post_id}")
    return post_id


def get_next_post() -> dict | None:
    """posts.jsonから未投稿の投稿を1件取得"""
    if not os.path.exists("posts.json"):
        print("posts.jsonが見つかりません")
        return None

    with open("posts.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    posts = data.get("posts", [])
    posted_ids = set(data.get("posted", []))

    for post in posts:
        if post["id"] not in posted_ids:
            return post

    print("未投稿の投稿がありません")
    return None


def mark_as_posted(post_id: str, threads_post_id: str):
    """投稿済みとしてマーク"""
    with open("posts.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    data.setdefault("posted", []).append(post_id)

    # 投稿履歴に記録
    data.setdefault("history", []).append(
        {
            "post_id": post_id,
            "threads_post_id": threads_post_id,
            "posted_at": datetime.now().isoformat(),
        }
    )

    with open("posts.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    post = get_next_post()
    if not post:
        print("投稿する内容がありません。generate_posts.pyを実行してください。")
        return

    print(f"投稿テーマ: {post['theme']}")
    print(f"投稿文:\n{post['text']}\n")

    container_id = create_container(post["text"])
    threads_post_id = publish_container(container_id)
    mark_as_posted(post["id"], threads_post_id)

    print(f"✅ 投稿完了 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")


if __name__ == "__main__":
    main()
