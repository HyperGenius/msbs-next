"""Tests for PilotService skill functionality."""

from unittest.mock import MagicMock

import pytest
from sqlmodel import Session

from app.core.skills import SKILL_COST
from app.models.models import Pilot
from app.services.pilot_service import PilotService


def test_unlock_skill_success() -> None:
    """スキル習得の成功ケースをテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=2,
        exp=0,
        credits=1000,
        skill_points=5,
        skills={},
    )

    updated_pilot, message = service.unlock_skill(pilot, "accuracy_up")

    assert updated_pilot.skill_points == 5 - SKILL_COST
    assert updated_pilot.skills["accuracy_up"] == 1
    assert "命中率向上" in message


def test_unlock_skill_level_up() -> None:
    """既に習得済みのスキルのレベルアップをテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=3,
        exp=0,
        credits=1000,
        skill_points=3,
        skills={"accuracy_up": 2},
    )

    updated_pilot, message = service.unlock_skill(pilot, "accuracy_up")

    assert updated_pilot.skill_points == 2
    assert updated_pilot.skills["accuracy_up"] == 3


def test_unlock_skill_insufficient_sp() -> None:
    """SPが不足している場合のテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=1,
        exp=0,
        credits=1000,
        skill_points=0,
        skills={},
    )

    with pytest.raises(ValueError, match="スキルポイントが不足しています"):
        service.unlock_skill(pilot, "accuracy_up")


def test_unlock_skill_max_level() -> None:
    """スキルが最大レベルに達している場合のテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=10,
        exp=0,
        credits=1000,
        skill_points=5,
        skills={"accuracy_up": 10},  # max level
    )

    with pytest.raises(ValueError, match="最大レベルに達しています"):
        service.unlock_skill(pilot, "accuracy_up")


def test_unlock_skill_invalid_id() -> None:
    """存在しないスキルIDを指定した場合のテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=1,
        exp=0,
        credits=1000,
        skill_points=5,
        skills={},
    )

    with pytest.raises(ValueError, match="スキルが見つかりません"):
        service.unlock_skill(pilot, "invalid_skill_id")


def test_level_up_grants_skill_points() -> None:
    """レベルアップ時にSPが付与されることをテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=1,
        exp=90,
        credits=1000,
        skill_points=0,
        skills={},
    )

    # 20経験値追加でレベルアップ (必要経験値 100)
    updated_pilot, logs = service.add_rewards(pilot, 20, 100)

    assert updated_pilot.level == 2
    assert updated_pilot.skill_points == 1
    assert any("スキルポイント +1" in log for log in logs)


def test_multiple_level_ups_grant_multiple_skill_points() -> None:
    """複数回レベルアップ時に複数のSPが付与されることをテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=1,
        exp=50,
        credits=1000,
        skill_points=0,
        skills={},
    )

    # 300経験値追加で複数レベルアップ (Lv1->2: 100必要, Lv2->3: 200必要)
    updated_pilot, logs = service.add_rewards(pilot, 300, 500)

    assert updated_pilot.level == 3
    assert updated_pilot.skill_points == 2  # 2回のレベルアップで2 SP
    assert any("スキルポイント +2" in log for log in logs)
