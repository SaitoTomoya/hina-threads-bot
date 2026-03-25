"""
リサーチャーエージェント
- X（旧Twitter）のトレンド投稿を収集
- YouTubeの転職系動画タイトル・概要を収集
- リサーチ結果をdata/research/に保存
"""

import anthropic
import json
import os
import re
import requests
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
RESEARCH_DIR = BASE_DIR / "data" / "research"

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def search_web(query: str) -> str:
    """DuckDuckGoでウェブ検索（無料・APIキー不要）"""
    url = "https://html.duckduckgo.com/html/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    params = {"q": query, "kl": "jp-jp"}
    try:
        resp = requests.post(url, data=params, headers=headers, timeout=10)
        resp.raise_for_status()
        # 結果からテキストを抽出（簡易版）
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text)
        return text[:3000]
    except Exception as e:
        return f"検索エラー: {e}"


def analyze_trends(raw_data: str, topic: str) -> dict:
    """収集データをClaudeで分析してトレンドを抽出"""
    prompt = f"""以下の検索結果から、Threadsで転職系アフィリエイト投稿を作るためのネタを抽出してください。

【トピック】{topic}

【検索結果】
{raw_data[:2000]}

【出力形式（JSON）】
{{
  "trending_topics": ["トレンドトピック1", "トレンドトピック2", ...],
  "hot_angles": ["バズりそうな切り口1", "切り口2", ...],
  "key_facts": ["使えるデータ・数字1", "データ2", ...],
  "post_ideas": ["投稿アイデア1", "投稿アイデア2", "投稿アイデア3"]
}}

JSONのみ出力してください。"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    # JSONを抽出
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {"trending_topics": [], "hot_angles": [], "key_facts": [], "post_ideas": []}


def run_research() -> str:
    """リサーチを実行してdata/research/に保存"""
    topics = [
        "転職 2025 トレンド AI リストラ",
        "転職エージェント おすすめ 女性 2025",
        "フルリモート 転職 求人 増加",
        "30代 転職 成功 体験談",
        "doda ビズリーチ 比較 口コミ 2025",
    ]

    all_results = []
    print("リサーチ開始...")

    for topic in topics:
        print(f"検索中: {topic}")
        raw = search_web(topic)
        analysis = analyze_trends(raw, topic)
        all_results.append({
            "topic": topic,
            "analysis": analysis,
            "searched_at": datetime.now().isoformat(),
        })

    # 結果を保存
    filename = f"research_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_file = RESEARCH_DIR / filename
    output_file.write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding="utf-8")

    # 投稿アイデアをまとめて返す
    all_ideas = []
    for r in all_results:
        all_ideas.extend(r["analysis"].get("post_ideas", []))
        all_ideas.extend(r["analysis"].get("hot_angles", []))

    summary = "\n".join(f"- {idea}" for idea in all_ideas[:20])
    print(f"✅ リサーチ完了: {filename}")
    return summary


if __name__ == "__main__":
    result = run_research()
    print("\n=== リサーチ結果サマリー ===")
    print(result)
