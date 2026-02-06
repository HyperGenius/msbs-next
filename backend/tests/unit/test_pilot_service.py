"""Tests for PilotService."""

from unittest.mock import MagicMock

from sqlmodel import Session

from app.models.models import Pilot
from app.services.pilot_service import PilotService


def test_calculate_required_exp() -> None:
    """次のレベルに必要な経験値の計算をテスト."""
    assert PilotService.calculate_required_exp(1) == 100
    assert PilotService.calculate_required_exp(2) == 200
    assert PilotService.calculate_required_exp(5) == 500
    assert PilotService.calculate_required_exp(10) == 1000


def test_calculate_battle_rewards_win() -> None:
    """勝利時の報酬計算をテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    # 勝利、撃墜なし
    exp, credits = service.calculate_battle_rewards(win=True, kills=0)
    assert exp == 100
    assert credits == 500

    # 勝利、撃墜3機
    exp, credits = service.calculate_battle_rewards(win=True, kills=3)
    assert exp == 130  # 100 + 3*10
    assert credits == 650  # 500 + 3*50


def test_calculate_battle_rewards_lose() -> None:
    """敗北時の報酬計算をテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    # 敗北、撃墜なし
    exp, credits = service.calculate_battle_rewards(win=False, kills=0)
    assert exp == 20
    assert credits == 100

    # 敗北、撃墜2機
    exp, credits = service.calculate_battle_rewards(win=False, kills=2)
    assert exp == 40  # 20 + 2*10
    assert credits == 200  # 100 + 2*50


def test_add_rewards_no_level_up() -> None:
    """レベルアップなしの報酬付与をテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=1,
        exp=50,
        credits=1000,
    )

    updated_pilot, logs = service.add_rewards(pilot, 30, 200)

    assert updated_pilot.level == 1
    assert updated_pilot.exp == 80
    assert updated_pilot.credits == 1200
    assert len(logs) >= 1
    assert "経験値 +30, クレジット +200" in logs[0]


def test_add_rewards_with_level_up() -> None:
    """レベルアップありの報酬付与をテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=1,
        exp=90,
        credits=1000,
    )

    # 20経験値追加でレベルアップ (必要経験値 100)
    updated_pilot, logs = service.add_rewards(pilot, 20, 100)

    assert updated_pilot.level == 2
    assert updated_pilot.exp == 10  # 110 - 100
    assert updated_pilot.credits == 1100
    assert any("レベルアップ" in log for log in logs)


def test_add_rewards_multiple_level_ups() -> None:
    """複数レベルアップの報酬付与をテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=1,
        exp=50,
        credits=1000,
    )

    # 300経験値追加で複数レベルアップ
    # Lv1->2: 100必要, Lv2->3: 200必要
    # 50 + 300 = 350
    # 350 - 100 = 250 (Lv2)
    # 250 - 200 = 50 (Lv3)
    updated_pilot, logs = service.add_rewards(pilot, 300, 500)

    assert updated_pilot.level == 3
    assert updated_pilot.exp == 50
    assert updated_pilot.credits == 1500
    assert any("2 レベル上昇しました" in log for log in logs)
