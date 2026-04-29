# backend/app/engine/fuzzy_rule_cache.py
"""ファジィルール JSON のキャッシュ管理クラス.

ファイルハッシュを使って JSON の変更を検出し、変更があった場合のみ
FuzzyEngine を再構築するホットリロード機能を提供する。
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.engine.fuzzy_engine import FuzzyEngine, _file_hash

logger = logging.getLogger(__name__)

# 戦略モードとJSONファイルのレイヤーマッピング（simulation.py と共通）
_STRATEGY_FILE_PREFIXES: dict[str, str] = {
    "AGGRESSIVE": "aggressive",
    "DEFENSIVE": "defensive",
    "SNIPER": "sniper",
    "ASSAULT": "assault",
    "RETREAT": "retreat",
}
_LAYER_SUFFIXES: dict[str, str] = {
    "behavior": "",
    "target": "_target_selection",
    "weapon": "_weapon_selection",
}
_LAYER_DEFAULTS: dict[str, dict[str, float]] = {
    "behavior": {"action": 0.0},
    "target": {"target_priority": 0.0},
    "weapon": {"weapon_score": 0.0},
}


class FuzzyRuleCache:
    """ファジィルール JSON のキャッシュ管理クラス.

    ファイルハッシュを使ってJSONの変更を検出し、変更があった場合のみ
    FuzzyEngine を再構築する。

    Usage:
        cache = FuzzyRuleCache(Path("backend/data/fuzzy_rules"))
        engines = cache.get_engines()  # 変更があったファイルのみ再ロード
        cache.force_reload_all()       # 全エンジンを強制再ロード
    """

    def __init__(self, rules_dir: Path) -> None:
        """初期化.

        Args:
            rules_dir: ファジィルール JSON ファイルが格納されているディレクトリ
        """
        self._rules_dir = rules_dir
        self._engines: dict[str, dict[str, FuzzyEngine]] = {}
        self._hashes: dict[str, str] = {}  # ファイルパス文字列 → SHA-256 ハッシュ値

        # 初期ロード
        self._load_all()

    def get_engines(self) -> dict[str, dict[str, FuzzyEngine]]:
        """変更があったファイルのみ再ロードしてエンジン辞書を返す.

        Returns:
            {"MODE": {"behavior": FuzzyEngine, "target": FuzzyEngine, "weapon": FuzzyEngine}}
        """
        self._scan_and_reload_changed()
        return self._engines

    def _scan_and_reload_changed(self) -> list[str]:
        """変更されたファイルを検出し再ロードする.

        Returns:
            変更されたファイルに対応する "MODE:layer" キーのリスト
        """
        changed_keys: list[str] = []

        for mode, prefix in _STRATEGY_FILE_PREFIXES.items():
            for layer, suffix in _LAYER_SUFFIXES.items():
                json_path = self._rules_dir / f"{prefix}{suffix}.json"
                if not json_path.exists():
                    continue

                path_key = str(json_path)
                current_hash = _file_hash(json_path)

                if self._hashes.get(path_key) == current_hash:
                    continue

                # ハッシュが変わった（または初回ロード）→ 再ロード
                engine = FuzzyEngine.from_json(
                    json_path, default_output=_LAYER_DEFAULTS[layer]
                )
                if mode not in self._engines:
                    self._engines[mode] = {}
                self._engines[mode][layer] = engine
                self._hashes[path_key] = current_hash

                logger.info(
                    "[HotReload] %s が変更されました → %s:%s を再ロードしました",
                    json_path.name,
                    mode,
                    layer,
                )
                print(
                    f"[HotReload] {json_path.name} が変更されました → {mode}:{layer} を再ロードしました"
                )
                changed_keys.append(f"{mode}:{layer}")

        return changed_keys

    def _load_all(self) -> None:
        """全ルールセットを初期ロードする（内部用）."""
        for mode, prefix in _STRATEGY_FILE_PREFIXES.items():
            mode_engines: dict[str, FuzzyEngine] = {}
            for layer, suffix in _LAYER_SUFFIXES.items():
                json_path = self._rules_dir / f"{prefix}{suffix}.json"
                if not json_path.exists():
                    continue

                path_key = str(json_path)
                engine = FuzzyEngine.from_json(
                    json_path, default_output=_LAYER_DEFAULTS[layer]
                )
                mode_engines[layer] = engine
                self._hashes[path_key] = _file_hash(json_path)

            if mode_engines:
                self._engines[mode] = mode_engines

    def force_reload_all(self) -> None:
        """全ルールセットを強制再ロードする.

        ハッシュキャッシュをリセットして全JSONを再ロードする。
        """
        self._hashes.clear()
        self._engines.clear()
        self._load_all()
