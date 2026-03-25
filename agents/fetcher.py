"""
フェッチャーエージェント
- 投稿後1時間・6時間・24時間のメトリクスを取得
- data/metrics/に保存
"""

import json
import os
import requests
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
POSTED_DIR = BASE_DIR / "data" / "posted"
METRICS_DIR = BASE_DIR / "data" / "metrics"

THREADS_USER_ID = os.environ["THREADS_USER_ID"]
THREADS_ACCESS_TOKEN = os.environ["THREADS_ACCESS_TOKEN"]


def get_post_metrics(threads_post_id: str) -> dict:
    """Threads APIからメトリクスを取得"""
    url = f"https://graph.threads.net/v1.0/{threads_post_id}/insights"
    params = {
        "metric": "views,likes,replies,reposts,quotes",
        "access_token": THREADS_ACCESS_TOKEN,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        metrics = {}
        for item in data:
            metrics[item["name"]] = item.get("values", [{}])[0].get("value", 0)
        return metrics
    except Exception as e:
        print(f"メトリクス取得エラー: {e}")
        return {}


def fetch_all_pending():
    """投稿後のメトリクス取得が必要なものを処理"""
    now = datetime.now()
    checkpoints = [1, 6, 24]  # 投稿後何時間後に取得するか

    for posted_file in POSTED_DIR.glob("*.json"):
        post = json.loads(posted_file.read_text(encoding="utf-8"))
        if "threads_post_id" not in post or "posted_at" not in post:
            continue

        posted_at = datetime.fromisoformat(post["posted_at"])
        hours_since = (now - posted_at).total_seconds() / 3600

        metrics_file = METRICS_DIR / f"{posted_file.stem}_metrics.json"
        if metrics_file.exists():
            existing = json.loads(metrics_file.read_text(encoding="utf-8"))
        else:
            existing = {"post_id": post["id"], "threads_post_id": post["threads_post_id"], "checkpoints": {}}

        for cp in checkpoints:
            if hours_since >= cp and str(cp) not in existing["checkpoints"]:
                print(f"メトリクス取得中: {post['id']} ({cp}時間後)")
                metrics = get_post_metrics(post["threads_post_id"])
                existing["checkpoints"][str(cp)] = {
                    "metrics": metrics,
                    "fetched_at": now.isoformat(),
                }
                metrics_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"  → {metrics}")


if __name__ == "__main__":
    fetch_all_pending()
