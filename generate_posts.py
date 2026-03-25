"""
Claude APIを使ってHinaの投稿文を生成するスクリプト
"""

import anthropic
import json
import os
from datetime import datetime

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

HINA_PROFILE = """
あなたはThreadsで転職アフィリエイトを発信するキャラクター「Hina」です。

【キャラ設定】
- 29歳・元営業事務5年 → WEBマーケ職にフルリモートで転職成功
- 年収+100万円・残業ほぼゼロを実現
- AIツール導入で仕事が減りそうな不安を感じていたのがきっかけ
- 読者：25〜35歳の会社員女性、転職に不安・興味がある層

【口調】
- 友達感覚・等身大・共感ファースト
- 「私もそうだった」「〇〇な人いませんか？」系
- 絵文字は1〜2個まで

【投稿ルール】
- 文字数：200〜400文字
- 構成：悩み提示 → 共感 → 解決策/体験談 → 行動誘導
- ハッシュタグ：最後に1つだけ
- アフィリエイト誘導は「プロフのリンクから」と自然に入れる
- 必ず文末に「#PR」を入れる（アフィリエイト開示）
- 投稿の70%は共感・体験談、30%はサービス紹介
"""

THEMES = [
    "AIに仕事を奪われる不安と転職の決意",
    "転職して年収が上がった体験談",
    "転職活動中に使ってよかったサービス",
    "フルリモートの働き方と転職の関係",
    "30代でも転職は遅くないという話",
    "転職エージェントを使った感想",
    "職場環境が悪い時の判断基準",
    "転職活動で後悔したこと・よかったこと",
    "出社強制になって転職を考え始めた話",
    "転職前後の生活の変化",
]


def generate_post(theme: str) -> str:
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[
            {
                "role": "user",
                "content": f"{HINA_PROFILE}\n\n以下のテーマで投稿文を1つ作成してください。\nテーマ：{theme}\n\n投稿文のみ出力してください。",
            }
        ],
    )
    return message.content[0].text


def generate_and_save_posts(count: int = 10):
    posts_file = "posts.json"

    # 既存の投稿を読み込む
    if os.path.exists(posts_file):
        with open(posts_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"posts": [], "posted": []}

    print(f"{count}件の投稿を生成します...")

    for i, theme in enumerate(THEMES[:count]):
        print(f"生成中 ({i+1}/{count}): {theme}")
        text = generate_post(theme)
        data["posts"].append(
            {
                "id": f"{datetime.now().strftime('%Y%m%d')}_{i+1:02d}",
                "theme": theme,
                "text": text,
                "created_at": datetime.now().isoformat(),
            }
        )

    with open(posts_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ {count}件の投稿を posts.json に保存しました")


if __name__ == "__main__":
    generate_and_save_posts(10)
