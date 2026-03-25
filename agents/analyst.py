"""
アナリストエージェント
- メトリクスデータを分析
- 伸びたパターン・テーマを特定
- 次のライター・リサーチャーへのフィードバックを生成
"""

import anthropic
import json
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
METRICS_DIR = BASE_DIR / "data" / "metrics"
POSTED_DIR = BASE_DIR / "data" / "posted"
RESEARCH_DIR = BASE_DIR / "data" / "research"

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def load_performance_data() -> list:
    """投稿データとメトリクスを結合"""
    results = []
    for metrics_file in METRICS_DIR.glob("*_metrics.json"):
        metrics_data = json.loads(metrics_file.read_text(encoding="utf-8"))
        post_id = metrics_data.get("post_id", "")

        # 対応する投稿データを取得
        post_file = POSTED_DIR / f"{post_id}.json"
        if not post_file.exists():
            continue

        post_data = json.loads(post_file.read_text(encoding="utf-8"))

        # 24時間後のメトリクスを優先
        checkpoint = (
            metrics_data["checkpoints"].get("24")
            or metrics_data["checkpoints"].get("6")
            or metrics_data["checkpoints"].get("1")
            or {}
        )

        results.append({
            "id": post_id,
            "pattern_name": post_data.get("pattern_name", "不明"),
            "text": post_data.get("text", ""),
            "score": post_data.get("score", 0),
            "metrics": checkpoint.get("metrics", {}),
            "posted_at": post_data.get("posted_at", ""),
        })

    return results


def analyze(performance_data: list) -> str:
    """パフォーマンスデータを分析してフィードバックを生成"""
    if not performance_data:
        return "分析データがまだありません。"

    data_summary = json.dumps(performance_data[:20], ensure_ascii=False, indent=2)

    prompt = f"""以下のThreads投稿パフォーマンスデータを分析して、改善提案を出してください。

【パフォーマンスデータ】
{data_summary}

【分析してほしい項目】
1. 最もviews/likesが多かったパターン・テーマ
2. 低パフォーマンスだったパターン・テーマ
3. 今後強化すべきコンテンツの方向性
4. 避けるべきコンテンツの特徴
5. 次のリサーチで調べるべきトピック

箇条書きで簡潔にまとめてください。"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )

    feedback = response.content[0].text.strip()

    # フィードバックを保存
    feedback_file = RESEARCH_DIR / f"feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    feedback_file.write_text(feedback, encoding="utf-8")

    return feedback


def run_analysis():
    data = load_performance_data()
    print(f"分析対象: {len(data)}件の投稿")
    feedback = analyze(data)
    print("\n=== 分析結果 ===")
    print(feedback)
    return feedback


if __name__ == "__main__":
    run_analysis()
