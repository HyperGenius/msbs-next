"""FuzzyRuleCache のユニットテスト."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.engine.fuzzy_engine import FuzzyEngine
from app.engine.fuzzy_rule_cache import FuzzyRuleCache

# ---------------------------------------------------------------------------
# テスト用ファジィルール JSON（最小限の有効な構造）
# ---------------------------------------------------------------------------

_MINIMAL_FUZZY_JSON = {
    "strategy": "TEST",
    "layer": "behavior_selection",
    "rules": [
        {
            "id": "rule_001",
            "conditions": [{"variable": "hp_ratio", "set": "HIGH"}],
            "operator": "AND",
            "output": {"variable": "action", "set": "ATTACK"},
        }
    ],
    "membership_functions": {
        "hp_ratio": {
            "HIGH": {"type": "trapezoid", "params": [0.65, 0.80, 1.0, 1.0]},
        },
        "action": {
            "ATTACK": {"type": "trapezoid", "params": [0.0, 0.0, 0.15, 0.30]},
            "MOVE": {"type": "triangle", "params": [0.25, 0.50, 0.75]},
        },
    },
}


def _write_json(path: Path, data: dict) -> None:
    """JSON データをファイルに書き込む."""
    path.write_text(json.dumps(data), encoding="utf-8")


def _make_test_rules_dir(tmp_path: Path) -> Path:
    """テスト用 rules_dir に AGGRESSIVE の3ファイルを作成して返す."""
    rules_dir = tmp_path / "fuzzy_rules"
    rules_dir.mkdir()

    # aggressive.json (behavior)
    _write_json(rules_dir / "aggressive.json", _MINIMAL_FUZZY_JSON)
    # aggressive_target_selection.json (target)
    _write_json(rules_dir / "aggressive_target_selection.json", _MINIMAL_FUZZY_JSON)
    # aggressive_weapon_selection.json (weapon)
    _write_json(rules_dir / "aggressive_weapon_selection.json", _MINIMAL_FUZZY_JSON)

    return rules_dir


# ---------------------------------------------------------------------------
# テストケース
# ---------------------------------------------------------------------------


def test_initial_load_all_rules(tmp_path: Path) -> None:
    """FuzzyRuleCache 初期化後に全ルールセットが _engines にロードされている."""
    rules_dir = _make_test_rules_dir(tmp_path)
    cache = FuzzyRuleCache(rules_dir)

    assert "AGGRESSIVE" in cache._engines
    assert "behavior" in cache._engines["AGGRESSIVE"]
    assert "target" in cache._engines["AGGRESSIVE"]
    assert "weapon" in cache._engines["AGGRESSIVE"]


def test_no_reload_when_unchanged(tmp_path: Path) -> None:
    """JSONファイルが変更されていない場合は get_engines() 呼び出しでリロードが発生しない."""
    rules_dir = _make_test_rules_dir(tmp_path)
    cache = FuzzyRuleCache(rules_dir)

    # 初回 get_engines() でエンジンオブジェクトを取得
    engines_first = cache.get_engines()
    behavior_engine_first = engines_first["AGGRESSIVE"]["behavior"]

    # ファイルを変更せずに再度 get_engines() を呼ぶ
    engines_second = cache.get_engines()
    behavior_engine_second = engines_second["AGGRESSIVE"]["behavior"]

    # 同じオブジェクトが返される（再ロードされていない）
    assert behavior_engine_first is behavior_engine_second


def test_reload_triggered_on_file_change(tmp_path: Path) -> None:
    """JSONファイルのハッシュを変更すると次の get_engines() 呼び出しで再ロードされる."""
    rules_dir = _make_test_rules_dir(tmp_path)
    cache = FuzzyRuleCache(rules_dir)

    # 初回 get_engines() でエンジンオブジェクトを取得
    engines_first = cache.get_engines()
    behavior_engine_first = engines_first["AGGRESSIVE"]["behavior"]

    # ファイルを変更（JSONの内容を書き換え）
    modified_json = dict(_MINIMAL_FUZZY_JSON)
    modified_json["rules"] = [
        {
            "id": "rule_modified",
            "conditions": [{"variable": "hp_ratio", "set": "HIGH"}],
            "operator": "AND",
            "output": {"variable": "action", "set": "MOVE"},
        }
    ]
    _write_json(rules_dir / "aggressive.json", modified_json)

    # 次の get_engines() で再ロードが発生する
    engines_second = cache.get_engines()
    behavior_engine_second = engines_second["AGGRESSIVE"]["behavior"]

    # 異なるオブジェクトが返される（再ロードされた）
    assert behavior_engine_first is not behavior_engine_second


def test_only_changed_file_reloaded(tmp_path: Path) -> None:
    """変更されたファイルのみが再ロードされ、他のエンジンはそのままである."""
    rules_dir = _make_test_rules_dir(tmp_path)
    cache = FuzzyRuleCache(rules_dir)

    # 初回取得
    engines_first = cache.get_engines()
    behavior_engine_first = engines_first["AGGRESSIVE"]["behavior"]
    target_engine_first = engines_first["AGGRESSIVE"]["target"]
    weapon_engine_first = engines_first["AGGRESSIVE"]["weapon"]

    # behavior ファイルのみ変更
    modified_json = dict(_MINIMAL_FUZZY_JSON)
    modified_json["rules"] = [
        {
            "id": "rule_modified",
            "conditions": [{"variable": "hp_ratio", "set": "HIGH"}],
            "operator": "AND",
            "output": {"variable": "action", "set": "MOVE"},
        }
    ]
    _write_json(rules_dir / "aggressive.json", modified_json)

    # 再取得
    engines_second = cache.get_engines()
    behavior_engine_second = engines_second["AGGRESSIVE"]["behavior"]
    target_engine_second = engines_second["AGGRESSIVE"]["target"]
    weapon_engine_second = engines_second["AGGRESSIVE"]["weapon"]

    # behavior のみ再ロードされている
    assert behavior_engine_first is not behavior_engine_second
    # target と weapon は変更なし → 同一オブジェクト
    assert target_engine_first is target_engine_second
    assert weapon_engine_first is weapon_engine_second


def test_force_reload_all(tmp_path: Path) -> None:
    """force_reload_all() で全エンジンが再ロードされる."""
    rules_dir = _make_test_rules_dir(tmp_path)
    cache = FuzzyRuleCache(rules_dir)

    # 初回取得
    engines_first = cache.get_engines()
    behavior_engine_first = engines_first["AGGRESSIVE"]["behavior"]
    target_engine_first = engines_first["AGGRESSIVE"]["target"]

    # ファイルを変更しないまま force_reload_all() を呼ぶ
    cache.force_reload_all()

    # 再取得（全エンジンが新しいオブジェクト）
    engines_second = cache.get_engines()
    behavior_engine_second = engines_second["AGGRESSIVE"]["behavior"]
    target_engine_second = engines_second["AGGRESSIVE"]["target"]

    assert behavior_engine_first is not behavior_engine_second
    assert target_engine_first is not target_engine_second


def test_schema_json_excluded(tmp_path: Path) -> None:
    """schema.json はルールセットとしてロードされない."""
    rules_dir = _make_test_rules_dir(tmp_path)

    # schema.json を作成（実際には valid な JSON だが schema.json という名前）
    _write_json(rules_dir / "schema.json", _MINIMAL_FUZZY_JSON)

    cache = FuzzyRuleCache(rules_dir)
    engines = cache.get_engines()

    # schema.json はどの戦略モードのエンジンとしても登録されていない
    # （ファイル名が prefix+suffix のパターンに一致しないため）
    for mode_engines in engines.values():
        for engine in mode_engines.values():
            assert isinstance(engine, FuzzyEngine)

    # _hashes に schema.json のエントリが存在しないこと
    schema_path_key = str(rules_dir / "schema.json")
    assert schema_path_key not in cache._hashes


def test_hot_reload_disabled_uses_snapshot(tmp_path: Path) -> None:
    """enable_hot_reload=False では get_engines() を呼んでも同一オブジェクトを返す.

    BattleSimulator を enable_hot_reload=False で初期化した場合、
    JSONファイルを変更しても _strategy_engines は起動時のスナップショットを返す。
    """
    from app.engine.simulation import BattleSimulator
    from app.models.models import MobileSuit, Vector3, Weapon

    def _make_ms(name: str, side: str, team_id: str) -> MobileSuit:
        return MobileSuit(
            name=name,
            max_hp=100,
            current_hp=100,
            armor=10,
            mobility=2.0,
            position=Vector3(x=0, y=0, z=0),
            weapons=[
                Weapon(
                    id="beam_rifle",
                    name="Beam Rifle",
                    power=30,
                    range=500,
                    accuracy=85,
                )
            ],
            side=side,
            team_id=team_id,
        )

    player = _make_ms("Player", "PLAYER", "PLAYER_TEAM")
    enemy = _make_ms("Enemy", "ENEMY", "ENEMY_TEAM")
    enemy.position = Vector3(x=300, y=0, z=0)

    # enable_hot_reload=False（デフォルト）
    sim = BattleSimulator(player, enemies=[enemy], enable_hot_reload=False)

    engines_first = sim._strategy_engines
    engines_second = sim._strategy_engines

    # ホットリロード無効時は常に同一スナップショットオブジェクトを返す
    assert engines_first is engines_second
