"""武器改造(WeaponEngineeringService)のテスト."""

import pytest
from fastapi import status
from sqlmodel import Session

from app.core.auth import get_current_user
from app.models.models import MobileSuit, Pilot, PlayerWeapon
from app.services.weapon_engineering_service import WeaponEngineeringService
from main import app


@pytest.fixture
def pilot(session: Session) -> Pilot:
    """テスト用パイロット."""
    pilot = Pilot(
        user_id="weapon_eng_test_user",
        name="Test Pilot",
        level=1,
        exp=0,
        credits=100000,
    )
    session.add(pilot)
    session.commit()
    session.refresh(pilot)
    return pilot


@pytest.fixture
def player_weapon(session: Session, pilot: Pilot) -> PlayerWeapon:
    """未装備のテスト用武器インスタンス（power=100, accuracy=60）."""
    pw = PlayerWeapon(
        user_id=pilot.user_id,
        master_weapon_id="zaku_mg",
        base_snapshot={
            "power": 100,
            "range": 400,
            "accuracy": 60,
            "type": "PHYSICAL",
        },
        custom_stats={},
    )
    session.add(pw)
    session.commit()
    session.refresh(pw)
    return pw


def test_calculate_upgrade_cost_power_bonus() -> None:
    """power_bonus のコスト計算式を検証."""
    cost = WeaponEngineeringService.calculate_upgrade_cost("power_bonus", 0)
    assert cost == 60  # int(60 * (1 + 0/30))

    cost_after = WeaponEngineeringService.calculate_upgrade_cost("power_bonus", 30)
    assert cost_after == 120  # int(60 * (1 + 30/30))


def test_calculate_upgrade_cost_invalid_stat() -> None:
    """未知の stat_type は ValueError."""
    with pytest.raises(ValueError, match="Invalid stat type"):
        WeaponEngineeringService.calculate_upgrade_cost("upgrade_level", 0)


def test_upgrade_power_bonus_unequipped_weapon(
    session: Session, pilot: Pilot, player_weapon: PlayerWeapon
) -> None:
    """未装備の武器でも改造でき、custom_stats.power_bonus が加算されることを確認."""
    service = WeaponEngineeringService(session)
    initial_credits = pilot.credits

    updated_pw, updated_pilot, cost = service.upgrade_stat(
        str(player_weapon.id), "power_bonus", pilot
    )

    assert updated_pw.custom_stats["power_bonus"] == 5
    assert updated_pilot.credits == initial_credits - cost
    assert cost == 60


def test_upgrade_accuracy_bonus(
    session: Session, pilot: Pilot, player_weapon: PlayerWeapon
) -> None:
    """accuracy_bonus の改造で custom_stats が更新されることを確認."""
    service = WeaponEngineeringService(session)

    updated_pw, _, _ = service.upgrade_stat(
        str(player_weapon.id), "accuracy_bonus", pilot, steps=2
    )

    assert updated_pw.custom_stats["accuracy_bonus"] == pytest.approx(2.0)


def test_upgrade_power_bonus_respects_cap(
    session: Session, pilot: Pilot, player_weapon: PlayerWeapon
) -> None:
    """power_bonus は base値(100)の200%、つまり bonus上限100で頭打ちになることを確認."""
    player_weapon.custom_stats = {"power_bonus": 99}
    session.add(player_weapon)
    session.commit()
    session.refresh(player_weapon)

    service = WeaponEngineeringService(session)
    updated_pw, _, _ = service.upgrade_stat(str(player_weapon.id), "power_bonus", pilot)
    assert updated_pw.custom_stats["power_bonus"] == 100

    with pytest.raises(ValueError, match="上限"):
        service.upgrade_stat(str(player_weapon.id), "power_bonus", pilot)


def test_upgrade_accuracy_bonus_respects_cap(
    session: Session, pilot: Pilot, player_weapon: PlayerWeapon
) -> None:
    """accuracy_bonus は base値(60)の130%、つまり bonus上限18で頭打ちになることを確認."""
    player_weapon.custom_stats = {"accuracy_bonus": 17.5}
    session.add(player_weapon)
    session.commit()
    session.refresh(player_weapon)

    service = WeaponEngineeringService(session)
    updated_pw, _, _ = service.upgrade_stat(
        str(player_weapon.id), "accuracy_bonus", pilot
    )
    assert updated_pw.custom_stats["accuracy_bonus"] == pytest.approx(18.0)

    with pytest.raises(ValueError, match="上限"):
        service.upgrade_stat(str(player_weapon.id), "accuracy_bonus", pilot)


def test_upgrade_insufficient_credits(
    session: Session, pilot: Pilot, player_weapon: PlayerWeapon
) -> None:
    """所持金不足時は RuntimeError."""
    pilot.credits = 10
    session.add(pilot)
    session.commit()

    service = WeaponEngineeringService(session)
    with pytest.raises(RuntimeError, match="Insufficient credits"):
        service.upgrade_stat(str(player_weapon.id), "power_bonus", pilot)


def test_upgrade_rejects_other_users_weapon(
    session: Session, player_weapon: PlayerWeapon
) -> None:
    """所有者以外は改造できない."""
    other_pilot = Pilot(
        user_id="other_user",
        name="Other Pilot",
        level=1,
        exp=0,
        credits=100000,
    )
    session.add(other_pilot)
    session.commit()
    session.refresh(other_pilot)

    service = WeaponEngineeringService(session)
    with pytest.raises(ValueError, match="アクセス権"):
        service.upgrade_stat(str(player_weapon.id), "power_bonus", other_pilot)


def test_get_upgrade_preview(session: Session, player_weapon: PlayerWeapon) -> None:
    """プレビューが現在値・改造後の値・コストを返すことを確認."""
    service = WeaponEngineeringService(session)
    preview = service.get_upgrade_preview(str(player_weapon.id), "power_bonus")

    assert preview["current_value"] == 0
    assert preview["new_value"] == 5
    assert preview["cost"] == 60
    assert preview["at_max_cap"] is False


def test_upgrade_api_endpoint(
    client, session, pilot: Pilot, player_weapon: PlayerWeapon
):
    """POST /api/player-weapons/{pw_id}/upgrade が custom_stats を更新することを確認."""
    initial_credits = pilot.credits
    app.dependency_overrides[get_current_user] = lambda: pilot.user_id
    try:
        response = client.post(
            f"/api/player-weapons/{player_weapon.id}/upgrade",
            json={"target_stat": "power_bonus", "steps": 1},
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["player_weapon"]["custom_stats"]["power_bonus"] == 5
        assert data["cost_paid"] == 60
        assert data["remaining_credits"] == initial_credits - 60
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_upgrade_api_endpoint_at_max_cap_returns_400(
    client, session, pilot: Pilot, player_weapon: PlayerWeapon
):
    """上限到達時、改造APIは400を返す."""
    player_weapon.custom_stats = {"power_bonus": 100}
    session.add(player_weapon)
    session.commit()

    app.dependency_overrides[get_current_user] = lambda: pilot.user_id
    try:
        response = client.post(
            f"/api/player-weapons/{player_weapon.id}/upgrade",
            json={"target_stat": "power_bonus", "steps": 1},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_upgrade_preview_api_endpoint(
    client, session, pilot: Pilot, player_weapon: PlayerWeapon
):
    """GET /api/player-weapons/{pw_id}/upgrade-preview/{stat_type} を確認."""
    app.dependency_overrides[get_current_user] = lambda: pilot.user_id
    try:
        response = client.get(
            f"/api/player-weapons/{player_weapon.id}/upgrade-preview/accuracy_bonus"
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["current_value"] == 0
        assert data["new_value"] == pytest.approx(1.0)
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_entry_creation_resyncs_equipped_weapon_upgrades(client, session, pilot: Pilot):
    """装備中の武器を改造した後、エントリー登録時に MobileSuit.weapons に反映されることを確認.

    再装備しなくても、バトル開始（エントリー）前に改造差分が反映される必要がある
    （Issue #411 要件4）。
    """
    mobile_suit = MobileSuit(
        user_id=pilot.user_id,
        name="Test Zaku",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        weapons=[
            {
                "id": "zaku_mg",
                "name": "Zaku Machine Gun",
                "power": 100,
                "range": 400,
                "accuracy": 60,
            }
        ],
        side="PLAYER",
    )
    session.add(mobile_suit)
    session.commit()
    session.refresh(mobile_suit)

    player_weapon = PlayerWeapon(
        user_id=pilot.user_id,
        master_weapon_id="zaku_mg",
        base_snapshot={
            "id": "zaku_mg",
            "name": "Zaku Machine Gun",
            "power": 100,
            "range": 400,
            "accuracy": 60,
            "type": "PHYSICAL",
        },
        custom_stats={},
        equipped_ms_id=mobile_suit.id,
        equipped_slot=0,
    )
    session.add(player_weapon)
    session.commit()
    session.refresh(player_weapon)

    service = WeaponEngineeringService(session)
    service.upgrade_stat(str(player_weapon.id), "power_bonus", pilot, steps=2)

    app.dependency_overrides[get_current_user] = lambda: pilot.user_id
    try:
        response = client.post(
            "/api/entries",
            json={"mobile_suit_id": str(mobile_suit.id)},
        )
        assert response.status_code == status.HTTP_200_OK
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    session.refresh(mobile_suit)
    assert mobile_suit.weapons[0]["power"] == 110  # 100 + 5*2
