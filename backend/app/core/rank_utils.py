"""ステータスランク変換ユーティリティ.

閾値テーブルに基づいて数値をS〜Eのランク文字列に変換する。
閾値テーブルは backend/data/master/thresholds.json で定義する。
"""

import json
import os
from pathlib import Path

_DATA_DIR = Path(
    os.environ.get(
        "MASTER_DATA_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "data" / "master"),
    )
)

_THRESHOLDS: dict[str, list[dict]] | None = None


def _load_thresholds() -> dict[str, list[dict]]:
    """閾値テーブルをJSONファイルから読み込む."""
    global _THRESHOLDS
    if _THRESHOLDS is None:
        json_path = _DATA_DIR / "thresholds.json"
        with open(json_path, encoding="utf-8") as f:
            _THRESHOLDS = json.load(f)
    return _THRESHOLDS


def get_rank(stat_name: str, value: float) -> str:
    """指定したステータス値をランク文字列（S〜E）に変換する.

    Args:
        stat_name: ステータス名（例: "hp", "armor", "mobility"）
        value: 変換する数値

    Returns:
        str: ランク文字列 ("S", "A", "B", "C", "D", "E")。
             定義が見つからない場合は "C" を返す。
    """
    thresholds = _load_thresholds()
    table = thresholds.get(stat_name)
    if not table:
        return "C"

    for entry in table:
        if value >= entry["min"]:
            return entry["rank"]
    return "E"
