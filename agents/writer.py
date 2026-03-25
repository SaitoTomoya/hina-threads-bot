"""
ライターエージェント
- 投稿文を生成（15パターン）
- 品質スコア採点（10項目、7.0以上のみ通過）
- 類似度チェック（過去100件と0.85以上は棄却）
- パターンローテーション（直近3件と同じパターンは使用禁止）
"""

import anthropic
import json
import os
import re
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
KNOWLEDGE_DIR = BASE_DIR / "knowledge"
PATTERNS_FILE = BASE_DIR / "patterns" / "post_patterns.json"
QUEUE_DIR = BASE_DIR / "data" / "queue"
POSTED_DIR = BASE_DIR / "data" / "posted"

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def load_knowledge() -> str:
    files = ["profile.md", "target.md", "strategy.md", "ng_words.md", "domain.md"]
    knowledge = ""
    for f in files:
        path = KNOWLEDGE_DIR / f
        if path.exists():
            knowledge += f"\n\n=== {f} ===\n" + path.read_text(encoding="utf-8")
    return knowledge


def load_patterns() -> list:
    with open(PATTERNS_FILE, encoding="utf-8") as f:
        return json.load(f)["patterns"]


def get_recent_pattern_ids(count: int = 3) -> list:
    """直近N件のパターンIDを取得"""
    queue_files = sorted(QUEUE_DIR.glob("*.json"), reverse=True)[:count]
    posted_files = sorted(POSTED_DIR.glob("*.json"), reverse=True)[:count]
    all_files = sorted(queue_files + posted_files, reverse=True)[:count]

    pattern_ids = []
    for f in all_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        if "pattern_id" in data:
            pattern_ids.append(data["pattern_id"])
    return pattern_ids


def get_past_posts(count: int = 100) -> list:
    """過去の投稿テキストを取得（類似度チェック用）"""
    texts = []
    all_files = list(QUEUE_DIR.glob("*.json")) + list(POSTED_DIR.glob("*.json"))
    for f in sorted(all_files, reverse=True)[:count]:
        data = json.loads(f.read_text(encoding="utf-8"))
        if "text" in data:
            texts.append(data["text"])
    return texts


def simple_similarity(text1: str, text2: str) -> float:
    """シンプルな類似度計算（単語の重複率）"""
    words1 = set(text1.replace("\n", " ").split())
    words2 = set(text2.replace("\n", " ").split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


def score_post(text: str, knowledge: str) -> float:
    """投稿の品質スコアを採点（0〜10点）"""
    prompt = f"""以下の投稿文を10項目で採点してください。各項目0〜1点で採点し、合計点（0〜10点）を返してください。

【採点項目】
1. フックの強さ（1行目で読み続けたくなるか）
2. 共感性（ターゲット読者が「わかる」と感じるか）
3. 有益性（読んで何か得るものがあるか）
4. 具体性（抽象的でなく具体的か）
5. テンポ感（読みやすいリズムか）
6. Hinaらしさ（キャラ設定に合っているか）
7. 自然な誘導（アフィリエイト誘導が不自然でないか）
8. 口調の適切さ（NGワードを使っていないか）
9. 文字数（200〜400文字の適切な長さか）
10. 拡散性（シェアしたくなるか）

【キャラ設定・NGワード情報】
{knowledge[:2000]}

【採点する投稿文】
{text}

【出力形式】
スコア: X.X
理由: （1行で簡潔に）"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    result = response.content[0].text
    match = re.search(r"スコア:\s*(\d+\.?\d*)", result)
    if match:
        return float(match.group(1))
    return 0.0


def generate_post(pattern: dict, knowledge: str, research_data: str = "") -> str:
    """投稿文を生成"""
    prompt = f"""あなたはThreadsで転職アフィリエイトを発信するキャラクター「Hina」です。

【キャラ・戦略情報】
{knowledge}

【今回使用するパターン】
パターン名: {pattern['name']}
構成: {pattern['structure']}
例文（参考のみ、そのままコピーしないこと）:
{pattern['example']}

{f"【リサーチデータ（参考）】{chr(10)}{research_data}" if research_data else ""}

【指示】
上記パターンを使って、転職ジャンルの投稿文を1つ作成してください。
- 文字数：200〜400文字
- 絵文字：最大2個
- ハッシュタグ：最後に1〜2個
- アフィリエイト案件を紹介する場合は末尾に「#PR」を追加
- 例文をそのままコピーしないこと

投稿文のみ出力してください。"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def generate_batch(count: int = 5, research_data: str = "") -> list:
    """投稿をバッチ生成して品質チェックを通過したものをキューに追加"""
    knowledge = load_knowledge()
    patterns = load_patterns()
    recent_pattern_ids = get_recent_pattern_ids(3)
    past_posts = get_past_posts(100)

    # 直近3件と同じパターンを除外
    available_patterns = [p for p in patterns if p["id"] not in recent_pattern_ids]
    if not available_patterns:
        available_patterns = patterns

    approved = []
    attempts = 0
    max_attempts = count * 3

    while len(approved) < count and attempts < max_attempts:
        attempts += 1
        pattern = available_patterns[attempts % len(available_patterns)]

        print(f"生成中 (パターン: {pattern['name']})...")
        text = generate_post(pattern, knowledge, research_data)

        # 類似度チェック
        too_similar = False
        for past in past_posts:
            if simple_similarity(text, past) >= 0.85:
                print(f"  → 類似度が高すぎるため棄却")
                too_similar = True
                break

        if too_similar:
            continue

        # 品質スコアチェック
        score = score_post(text, knowledge)
        print(f"  → 品質スコア: {score:.1f}")

        if score >= 7.0:
            post_data = {
                "id": f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(approved)+1:02d}",
                "pattern_id": pattern["id"],
                "pattern_name": pattern["name"],
                "text": text,
                "score": score,
                "status": "queued",
                "created_at": datetime.now().isoformat(),
            }
            # キューに保存
            queue_file = QUEUE_DIR / f"{post_data['id']}.json"
            queue_file.write_text(json.dumps(post_data, ensure_ascii=False, indent=2), encoding="utf-8")
            approved.append(post_data)
            print(f"  → キューに追加 ✅")
        else:
            print(f"  → スコア不足のため棄却")

    print(f"\n✅ {len(approved)}件の投稿をキューに追加しました")
    return approved


if __name__ == "__main__":
    results = generate_batch(count=5)
    for r in results:
        print(f"\n--- {r['pattern_name']} (スコア: {r['score']}) ---")
        print(r["text"])
