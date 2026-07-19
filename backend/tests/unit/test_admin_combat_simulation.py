"""管理者用 1対1 攻撃シミュレーション API のユニットテスト（Issue #381）."""

import os

import pytest
from fastapi import status
from fastapi.testclient import TestClient

os.environ["ADMIN_API_KEY"] = "test_admin_key_12345"

from main import app

ADMIN_KEY = "test_admin_key_12345"
HEADERS = {"X-API-Key": ADMIN_KEY}

BEAM_RIFLE = {
    "id": "beam_rifle",
    "name": "Beam Rifle",
    "power": 150,
    "range": 500,
    "accuracy": 75,
    "type": "BEAM",
    "weapon_type": "RANGED",
    "optimal_range": 320.0,
    "decay_rate": 0.09,
    "is_melee": False,
}

HEAT_HAWK = {
    "id": "heat_hawk",
    "name": "Heat Hawk",
    "power": 130,
    "range": 50,
    "accuracy": 80,
    "type": "PHYSICAL",
    "weapon_type": "MELEE",
    "optimal_range": 0.0,
    "decay_rate": 0.05,
    "is_melee": True,
}


def _spec(armor=80, mobility=1.2, weapons=None, **overrides):
    base = {
        "max_hp": 1000,
        "armor": armor,
        "mobility": mobility,
        "sensor_range": 500.0,
        "beam_resistance": 0.0,
        "physical_resistance": 0.0,
        "melee_aptitude": 1.0,
        "shooting_aptitude": 1.0,
        "accuracy_bonus": 0.0,
        "evasion_bonus": 0.0,
        "acceleration_bonus": 1.0,
        "turning_bonus": 1.0,
        "weapons": weapons if weapons is not None else [BEAM_RIFLE],
    }
    base.update(overrides)
    return base


@pytest.fixture(name="client")
def client_fixture():
    """テスト用APIクライアント."""
    client = TestClient(app)
    yield client


# ===================== 認証テスト =====================


def test_simulate_requires_auth(client):
    """認証ヘッダーなしでは 401 または 422 が返ること."""
    response = client.post(
        "/api/admin/simulate-combat",
        json={
            "attacker_spec": _spec(),
            "attacker_weapon_id": "beam_rifle",
            "defender_spec": _spec(),
        },
    )
    assert response.status_code in (status.HTTP_401_UNAUTHORIZED, 422)


def test_simulate_wrong_key(client):
    """不正なAPIキーで 401 が返ること."""
    response = client.post(
        "/api/admin/simulate-combat",
        headers={"X-API-Key": "wrong_key"},
        json={
            "attacker_spec": _spec(),
            "attacker_weapon_id": "beam_rifle",
            "defender_spec": _spec(),
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ===================== 決定論値のテスト =====================


def test_simulate_deterministic_values(client):
    """乱数を振らない理論値が計算式どおりに返ること."""
    response = client.post(
        "/api/admin/simulate-combat",
        headers=HEADERS,
        json={
            "attacker_spec": _spec(armor=80, mobility=0.0),
            "attacker_weapon_id": "beam_rifle",
            "defender_spec": _spec(armor=100, mobility=0.0),
        },
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()

    # weapon.accuracy(75) - dist_penalty(0, optimal距離なので) - evasion_bonus(mobility*10=0)
    assert body["hit_chance"] == pytest.approx(75.0)
    # base_crit_rate = 0.05, ステータス補正なし
    assert body["crit_chance"] == pytest.approx(5.0)
    # クリティカル倍率 weapon.power * 1.2
    assert body["crit_damage"] == int(150 * 1.2)
    assert body["base_damage"] >= 1
    assert body["resistance_applied_damage"] >= 1
    assert body["monte_carlo"] is None


def test_simulate_pilot_stats_affect_hit_and_crit(client):
    """パイロットステータス（SHT/INT/TOU）が命中率・クリティカル率に反映されること."""
    baseline = client.post(
        "/api/admin/simulate-combat",
        headers=HEADERS,
        json={
            "attacker_spec": _spec(),
            "attacker_weapon_id": "beam_rifle",
            "defender_spec": _spec(),
        },
    ).json()

    boosted = client.post(
        "/api/admin/simulate-combat",
        headers=HEADERS,
        json={
            "attacker_spec": _spec(),
            "attacker_weapon_id": "beam_rifle",
            "attacker_pilot": {"sht": 50, "intel": 20},
            "defender_spec": _spec(),
        },
    ).json()

    assert boosted["hit_chance"] > baseline["hit_chance"]
    assert boosted["crit_chance"] > baseline["crit_chance"]


def test_simulate_melee_weapon_skips_resistance(client):
    """格闘武器は耐性計算をスキップする現行仕様に合わせていること."""
    response = client.post(
        "/api/admin/simulate-combat",
        headers=HEADERS,
        json={
            "attacker_spec": _spec(weapons=[HEAT_HAWK]),
            "attacker_weapon_id": "heat_hawk",
            "defender_spec": _spec(physical_resistance=0.5),
        },
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    # 耐性50%が無視されるため、適性(1.0)適用のみで base_damage と一致する
    assert body["resistance_applied_damage"] == body["base_damage"]


# ===================== モンテカルロ試行のテスト =====================


def test_simulate_monte_carlo_converges_to_deterministic(client):
    """モンテカルロ試行の実測命中率が理論値に近似すること（大数の法則）."""
    response = client.post(
        "/api/admin/simulate-combat",
        headers=HEADERS,
        json={
            "attacker_spec": _spec(),
            "attacker_weapon_id": "beam_rifle",
            "defender_spec": _spec(),
            "trials": 3000,
        },
    )
    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    mc = body["monte_carlo"]
    assert mc is not None
    assert mc["trials"] == 3000
    assert abs(mc["actual_hit_rate"] - body["hit_chance"]) < 10.0
    assert abs(mc["actual_crit_rate"] - body["crit_chance"]) < 10.0
    assert mc["min_damage"] <= mc["avg_damage"] <= mc["max_damage"]


def test_simulate_trials_out_of_range_rejected(client):
    """Trials が範囲外（1〜5000）の場合 422 が返ること."""
    response = client.post(
        "/api/admin/simulate-combat",
        headers=HEADERS,
        json={
            "attacker_spec": _spec(),
            "attacker_weapon_id": "beam_rifle",
            "defender_spec": _spec(),
            "trials": 10000,
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ===================== エラーケース =====================


def test_simulate_unknown_weapon_id_returns_422(client):
    """attacker_weapon_id が attacker_spec.weapons に存在しない場合 422 が返ること."""
    response = client.post(
        "/api/admin/simulate-combat",
        headers=HEADERS,
        json={
            "attacker_spec": _spec(),
            "attacker_weapon_id": "nonexistent_weapon",
            "defender_spec": _spec(),
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_simulate_invalid_attack_sector_returns_422(client):
    """attack_sector が不正な値の場合 422 が返ること."""
    response = client.post(
        "/api/admin/simulate-combat",
        headers=HEADERS,
        json={
            "attacker_spec": _spec(),
            "attacker_weapon_id": "beam_rifle",
            "defender_spec": _spec(),
            "attack_sector": "DIAGONAL",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
