# backend/scripts/simulation/suppression_args.py
"""計測ツールの `--suppression` 引数を `SuppressionConfig` に変換する.

書き方:
    off                       制圧なし
    on                        既定の係数
    penalty=0.3,decay=0.5     既定の係数から一部を変える
    dirs=all                  後退・逃走中も減速する（既定は advance: 後退・逃走中は減速しない）

キー: per_shot（再使用待ち 1 秒あたりの量）, hit（命中の倍率）, max, decay, penalty, dirs
"""

from __future__ import annotations

from dataclasses import replace

from app.engine.suppression import SuppressionConfig

_FLOAT_KEYS = {
    "per_shot": "per_cooldown_sec",
    "hit": "hit_multiplier",
    "max": "max_value",
    "decay": "decay_rate",
    "penalty": "max_speed_penalty",
}
_DIRS = {"advance": True, "all": False}


def parse_suppression(value: str) -> SuppressionConfig | None:
    """`--suppression` の値を変換する. `off` は None を返す."""
    if value == "off":
        return None
    config = SuppressionConfig()
    if value == "on":
        return config
    for item in value.split(","):
        key, sep, raw = item.partition("=")
        key = key.strip()
        if not sep:
            raise ValueError(f"key=value の形ではない: {item!r}")
        if key == "dirs":
            if raw not in _DIRS:
                raise ValueError(f"dirs は {list(_DIRS)} のどれか: {raw!r}")
            config = replace(config, advance_only=_DIRS[raw])
        elif key in _FLOAT_KEYS:
            config = replace(config, **{_FLOAT_KEYS[key]: float(raw)})
        else:
            raise ValueError(f"不明なキー: {key!r}（候補: {[*_FLOAT_KEYS, 'dirs']}）")
    return config
