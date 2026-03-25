"""
オーケストレーター
全エージェントを統括して自動運用サイクルを回す

使い方:
  python orchestrator.py research   # リサーチ実行
  python orchestrator.py write      # 投稿文生成（5件）
  python orchestrator.py post       # 1件投稿
  python orchestrator.py fetch      # メトリクス取得
  python orchestrator.py analyze    # 分析実行
  python orchestrator.py all        # 全サイクル実行
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

# dataディレクトリの初期化
for d in ["data/research", "data/queue", "data/posted", "data/metrics"]:
    (BASE_DIR / d).mkdir(parents=True, exist_ok=True)


def run_research():
    from agents.researcher import run_research
    print("=== リサーチ開始 ===")
    return run_research()


def run_write(research_data: str = ""):
    from agents.writer import generate_batch
    print("=== 投稿文生成開始 ===")
    return generate_batch(count=5, research_data=research_data)


def run_post():
    from agents.poster import post_next
    print("=== 投稿実行 ===")
    return post_next()


def run_fetch():
    from agents.fetcher import fetch_all_pending
    print("=== メトリクス取得 ===")
    fetch_all_pending()


def run_analyze():
    from agents.analyst import run_analysis
    print("=== 分析実行 ===")
    return run_analysis()


def run_all():
    """全サイクル実行"""
    print("🤖 Hina自動運用サイクル開始\n")

    # 1. リサーチ
    research_data = run_research()
    print()

    # 2. 投稿文生成（リサーチ結果を活用）
    run_write(research_data)
    print()

    # 3. 1件投稿
    run_post()
    print()

    # 4. メトリクス取得
    run_fetch()
    print()

    # 5. 分析（投稿が10件以上あれば）
    posted_count = len(list((BASE_DIR / "data" / "posted").glob("*.json")))
    if posted_count >= 10:
        run_analyze()

    print("\n✅ サイクル完了")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "all"

    if command == "research":
        run_research()
    elif command == "write":
        run_write()
    elif command == "post":
        run_post()
    elif command == "fetch":
        run_fetch()
    elif command == "analyze":
        run_analyze()
    elif command == "all":
        run_all()
    else:
        print(__doc__)
