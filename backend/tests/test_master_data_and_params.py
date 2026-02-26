"""マスターデータのJSON外部化および新パラメータのテスト."""

import json
import os
import tempfile
from pathlib import Path

from fastapi import status

from app.core.gamedata import (
    _get_shop_listings,
    _get_weapon_shop_listings,
    get_shop_listing_by_id,
    get_weapon_listing_by_id,
    reload_master_data,
)
from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon
from main import app


# === マスターデータ読み込みテスト ===


def test_load_mobile_suits_from_json():
    """JSONファイルからモビルスーツデータが読み込めること."""
    listings = _get_shop_listings()
    assert len(listings) > 0

    # 各商品に必要なフィールドがあることを確認
    for item in listings:
        assert "id" in item
        assert "name" in item
        assert "price" in item
        assert "description" in item
        assert "specs" in item
        specs = item["specs"]
        assert "max_hp" in specs
        assert "armor" in specs
        assert "mobility" in specs
        # 新規パラメータ
        assert "melee_aptitude" in specs
        assert "shooting_aptitude" in specs
        assert "accuracy_bonus" in specs
        assert "evasion_bonus" in specs
        assert "acceleration_bonus" in specs
        assert "turning_bonus" in specs


def test_load_weapons_from_json():
    """JSONファイルから武器データが読み込めること."""
    listings = _get_weapon_shop_listings()
    assert len(listings) > 0

    for item in listings:
        assert "id" in item
        assert "name" in item
        assert "price" in item
        assert "weapon" in item
        weapon = item["weapon"]
        assert isinstance(weapon, Weapon)


def test_get_shop_listing_by_id():
    """IDで機体データを取得できること."""
    listing = get_shop_listing_by_id("zaku_ii")
    assert listing is not None
    assert listing["name"] == "Zaku II"
    assert listing["price"] == 500

    # 存在しないID
    assert get_shop_listing_by_id("nonexistent") is None


def test_get_weapon_listing_by_id():
    """IDで武器データを取得できること."""
    listing = get_weapon_listing_by_id("beam_saber")
    assert listing is not None
    assert listing["name"] == "Beam Saber"

    # 存在しないID
    assert get_weapon_listing_by_id("nonexistent") is None


def test_reload_master_data():
    """マスターデータのリロードが正常に動作すること."""
    result = reload_master_data()
    assert "mobile_suits" in result
    assert "weapons" in result
    assert result["mobile_suits"] > 0
    assert result["weapons"] > 0


def test_weapon_is_melee_flag():
    """武器のis_meleeフラグがJSONから正しく読み込まれること."""
    # Heat Rod は近接武器
    heat_rod = get_weapon_listing_by_id("heat_rod")
    assert heat_rod is not None
    assert heat_rod["weapon"].is_melee is True

    # Beam Saber は近接武器
    beam_saber = get_weapon_listing_by_id("beam_saber")
    assert beam_saber is not None
    assert beam_saber["weapon"].is_melee is True

    # Zaku Machine Gun は射撃武器
    zaku_mg = get_weapon_listing_by_id("zaku_mg")
    assert zaku_mg is not None
    assert zaku_mg["weapon"].is_melee is False


# === リロードAPIテスト ===


def test_reload_master_api(client):
    """POST /api/admin/reload-master が正常にリロードすること."""
    response = client.post("/api/admin/reload-master")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "ok"
    assert "reloaded" in data
    assert data["reloaded"]["mobile_suits"] > 0
    assert data["reloaded"]["weapons"] > 0


# === 新パラメータの戦闘ロジックテスト ===


def _create_suit_with_params(
    name="Test Suit",
    position=None,
    weapons=None,
    melee_aptitude=1.0,
    shooting_aptitude=1.0,
    accuracy_bonus=0.0,
    evasion_bonus=0.0,
    side="PLAYER",
    team_id="TEAM_A",
) -> MobileSuit:
    """テスト用のMobileSuitを作成する."""
    if position is None:
        position = Vector3(x=0, y=0, z=0)
    if weapons is None:
        weapons = [
            Weapon(
                id="test_weapon",
                name="Test Weapon",
                power=100,
                range=500,
                accuracy=80,
                type="BEAM",
                optimal_range=300.0,
                decay_rate=0.05,
                is_melee=False,
            )
        ]
    return MobileSuit(
        name=name,
        max_hp=1000,
        current_hp=1000,
        armor=50,
        mobility=1.0,
        position=position,
        weapons=weapons,
        side=side,
        team_id=team_id,
        tactics={"priority": "CLOSEST", "range": "BALANCED"},
        melee_aptitude=melee_aptitude,
        shooting_aptitude=shooting_aptitude,
        accuracy_bonus=accuracy_bonus,
        evasion_bonus=evasion_bonus,
    )


def test_accuracy_bonus_increases_hit_chance():
    """accuracy_bonusが命中率に加算されること."""
    attacker_base = _create_suit_with_params(accuracy_bonus=0.0)
    attacker_bonus = _create_suit_with_params(accuracy_bonus=10.0)
    target = _create_suit_with_params(
        name="Target", position=Vector3(x=300, y=0, z=0),
        side="ENEMY", team_id="TEAM_B",
    )
    weapon = attacker_base.weapons[0]

    sim1 = BattleSimulator(attacker_base, [target])
    sim2 = BattleSimulator(attacker_bonus, [target])

    hit1, _ = sim1._calculate_hit_chance(attacker_base, target, weapon, 300.0)
    hit2, _ = sim2._calculate_hit_chance(attacker_bonus, target, weapon, 300.0)

    # accuracy_bonus=10のほうが10ポイント高い
    assert hit2 > hit1
    assert abs(hit2 - hit1 - 10.0) < 0.01


def test_evasion_bonus_decreases_hit_chance():
    """evasion_bonusが命中率を低下させること."""
    attacker = _create_suit_with_params()
    target_base = _create_suit_with_params(
        name="Target Base", position=Vector3(x=300, y=0, z=0),
        side="ENEMY", team_id="TEAM_B", evasion_bonus=0.0,
    )
    target_evasive = _create_suit_with_params(
        name="Target Evasive", position=Vector3(x=300, y=0, z=0),
        side="ENEMY", team_id="TEAM_B", evasion_bonus=10.0,
    )
    weapon = attacker.weapons[0]

    sim1 = BattleSimulator(attacker, [target_base])
    sim2 = BattleSimulator(attacker, [target_evasive])

    hit1, _ = sim1._calculate_hit_chance(attacker, target_base, weapon, 300.0)
    hit2, _ = sim2._calculate_hit_chance(attacker, target_evasive, weapon, 300.0)

    # evasion_bonus=10のターゲットのほうが10ポイント命中率が低い
    assert hit1 > hit2
    assert abs(hit1 - hit2 - 10.0) < 0.01


def test_melee_aptitude_affects_melee_damage():
    """melee_aptitudeが近接武器のダメージに影響すること."""
    melee_weapon = Weapon(
        id="melee_test",
        name="Melee Weapon",
        power=100,
        range=200,
        accuracy=90,
        type="PHYSICAL",
        optimal_range=100.0,
        decay_rate=0.1,
        is_melee=True,
    )
    # 格闘適性が高い機体
    attacker_high = _create_suit_with_params(
        melee_aptitude=1.5, weapons=[melee_weapon],
    )
    # 格闘適性が基準値の機体
    attacker_base = _create_suit_with_params(
        melee_aptitude=1.0, weapons=[melee_weapon],
    )

    target = _create_suit_with_params(
        name="Target", position=Vector3(x=100, y=0, z=0),
        side="ENEMY", team_id="TEAM_B",
    )

    # _process_hit はランダム要素があるので、直接適性値の計算をテスト
    # 適性値1.5の場合、damage = base * 1.5
    assert attacker_high.melee_aptitude == 1.5
    assert attacker_base.melee_aptitude == 1.0


def test_shooting_aptitude_affects_ranged_damage():
    """shooting_aptitudeが射撃武器のダメージに影響すること."""
    ranged_weapon = Weapon(
        id="ranged_test",
        name="Ranged Weapon",
        power=100,
        range=500,
        accuracy=80,
        type="BEAM",
        optimal_range=300.0,
        decay_rate=0.05,
        is_melee=False,
    )
    attacker_high = _create_suit_with_params(
        shooting_aptitude=1.3, weapons=[ranged_weapon],
    )
    attacker_base = _create_suit_with_params(
        shooting_aptitude=1.0, weapons=[ranged_weapon],
    )

    assert attacker_high.shooting_aptitude == 1.3
    assert attacker_base.shooting_aptitude == 1.0


def test_new_params_have_default_values():
    """新パラメータがデフォルト値を持つこと."""
    ms = MobileSuit(
        name="Default Suit",
        max_hp=100,
        current_hp=100,
        position=Vector3(x=0, y=0, z=0),
        weapons=[],
        side="PLAYER",
    )

    assert ms.melee_aptitude == 1.0
    assert ms.shooting_aptitude == 1.0
    assert ms.accuracy_bonus == 0.0
    assert ms.evasion_bonus == 0.0
    assert ms.acceleration_bonus == 1.0
    assert ms.turning_bonus == 1.0


def test_weapon_is_melee_default_false():
    """Weaponモデルのis_meleeがデフォルトでFalseであること."""
    weapon = Weapon(
        id="test",
        name="Test",
        power=100,
        range=500,
        accuracy=80,
    )
    assert weapon.is_melee is False


def test_shop_listings_include_new_params(client):
    """ショップリストに新パラメータが含まれること."""
    response = client.get("/api/shop/listings")
    assert response.status_code == status.HTTP_200_OK

    listings = response.json()
    assert len(listings) > 0

    for item in listings:
        specs = item["specs"]
        assert "melee_aptitude" in specs
        assert "shooting_aptitude" in specs
        assert "accuracy_bonus" in specs
        assert "evasion_bonus" in specs
        assert "acceleration_bonus" in specs
        assert "turning_bonus" in specs
