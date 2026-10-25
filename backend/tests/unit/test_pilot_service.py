"""Tests for PilotService."""

from unittest.mock import MagicMock

import pytest
from sqlmodel import Session

from app.engine.objectives import ObjectiveResult, ObjectiveStatus
from app.models.models import MobileSuit, Pilot
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


def _escort(
    status: ObjectiveStatus, progress: int, player_survived: bool = True
) -> ObjectiveResult:
    return ObjectiveResult(
        status,
        progress=progress,
        required=2,
        total=3,
        lost=3 - progress,
        player_survived=player_survived,
    )


def test_calculate_battle_rewards_escort_tiers() -> None:
    """友軍を逃がす作戦は、全員離脱 > 必要数を満たした > 失敗の順に報酬が多い."""
    service = PilotService(MagicMock(spec=Session))

    full = service.calculate_battle_rewards(
        True, objective_result=_escort(ObjectiveStatus.SUCCESS, 3)
    )
    enough = service.calculate_battle_rewards(
        True, objective_result=_escort(ObjectiveStatus.SUCCESS, 2)
    )
    failed = service.calculate_battle_rewards(
        False, objective_result=_escort(ObjectiveStatus.FAILURE, 1)
    )

    assert full == (150, 750)
    assert enough == (100, 500)
    assert failed == (30, 150)  # 失敗の基本 20/100 + 離脱 1 機 × 10/50
    assert full > enough > failed


def test_calculate_battle_rewards_escort_player_down_and_kills() -> None:
    """プレイヤー機が撃破されていると基本報酬が減り、撃墜ボーナスは半分になる."""
    service = PilotService(MagicMock(spec=Session))

    down = service.calculate_battle_rewards(
        True, objective_result=_escort(ObjectiveStatus.SUCCESS, 2, False)
    )
    with_kills = service.calculate_battle_rewards(
        True, kills=2, objective_result=_escort(ObjectiveStatus.SUCCESS, 2)
    )

    assert down == (70, 350)
    assert with_kills == (110, 550)  # 基本 100/500 + 2 機 × 10/50 の半分


def test_calculate_battle_rewards_ignores_annihilation_result() -> None:
    """友軍を数えない目標（殲滅など）の結果を渡しても、勝敗と撃墜数で決める."""
    service = PilotService(MagicMock(spec=Session))

    result = ObjectiveResult(ObjectiveStatus.SUCCESS)

    assert service.calculate_battle_rewards(True, 3, result) == (130, 650)


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


def test_get_or_create_pilot_creates_new_pilot_with_starter_suit() -> None:
    """新規パイロット作成時にスターター機体が付与されることをテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    # パイロットが存在しない場合の Mock 設定
    mock_exec_result = MagicMock()
    mock_exec_result.first.return_value = None  # パイロットが存在しない
    session.exec.return_value = mock_exec_result

    # 新規パイロット作成
    pilot = service.get_or_create_pilot("test_user_123", "Test Pilot")

    # パイロットが作成されたことを確認
    assert pilot.user_id == "test_user_123"
    assert pilot.name == "Test Pilot"
    assert pilot.level == 1
    assert pilot.credits == 1000

    # session.add が2回呼ばれることを確認 (1回目: pilot, 2回目: mobile_suit)
    assert session.add.call_count == 2

    # session.commit が2回呼ばれることを確認 (1回目: pilot, 2回目: mobile_suit)
    assert session.commit.call_count == 2

    # 追加されたオブジェクトの確認
    add_calls = session.add.call_args_list
    # 1回目の呼び出しは Pilot
    pilot_add_call = add_calls[0][0][0]
    assert isinstance(pilot_add_call, Pilot)
    assert pilot_add_call.user_id == "test_user_123"

    # 2回目の呼び出しは MobileSuit (デフォルトは zaku_ii)
    mobile_suit_add_call = add_calls[1][0][0]
    assert isinstance(mobile_suit_add_call, MobileSuit)

    # スターター機体の名前に "Starter" が含まれることを確認
    assert "Starter" in mobile_suit_add_call.name
    assert mobile_suit_add_call.user_id == "test_user_123"
    assert mobile_suit_add_call.side == "PLAYER"


def test_create_starter_mobile_suit_with_custom_unit() -> None:
    """カスタムユニットIDでスターター機体を作成できることをテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    # GM機体を作成
    starter_suit = service._create_starter_mobile_suit("test_user_456", "gm")

    # 作成された機体を確認
    assert starter_suit.user_id == "test_user_456"
    assert "GM" in starter_suit.name or "Starter" in starter_suit.name
    assert starter_suit.side == "PLAYER"
    assert starter_suit.max_hp == 750  # GM の HP

    # session.add が呼ばれることを確認
    session.add.assert_called_once()
    session.commit.assert_called_once()


def test_get_or_create_pilot_returns_existing_pilot() -> None:
    """既存のパイロットが存在する場合は新規作成しないことをテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    # 既存のパイロットを Mock
    existing_pilot = Pilot(
        user_id="existing_user",
        name="Existing Pilot",
        level=5,
        exp=250,
        credits=3000,
    )

    mock_exec_result = MagicMock()
    mock_exec_result.first.return_value = existing_pilot
    session.exec.return_value = mock_exec_result

    # 既存パイロットを取得
    pilot = service.get_or_create_pilot("existing_user", "Existing Pilot")

    # 既存のパイロットが返されることを確認
    assert pilot == existing_pilot

    # session.add が呼ばれないことを確認（新規作成していない）
    session.add.assert_not_called()
    session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# ステータスポイント付与・割り振りのテスト
# ---------------------------------------------------------------------------


def test_add_rewards_grants_status_points_on_level_up() -> None:
    """レベルアップ時にステータスポイントが付与されることをテスト."""
    from app.services.pilot_service import STATUS_POINTS_PER_LEVEL

    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=1,
        exp=90,
        credits=1000,
        status_points=0,
    )

    updated_pilot, logs = service.add_rewards(pilot, 20, 0)

    # Lv1→2 でレベルアップ: STATUS_POINTS_PER_LEVEL 分ポイント付与
    assert updated_pilot.status_points == STATUS_POINTS_PER_LEVEL
    assert any("ステータスポイント" in log for log in logs)


def test_add_rewards_grants_status_points_multiple_level_ups() -> None:
    """複数レベルアップ時に累積ステータスポイントが付与されることをテスト."""
    from app.services.pilot_service import STATUS_POINTS_PER_LEVEL

    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=1,
        exp=50,
        credits=1000,
        status_points=0,
    )

    # Lv1→3 のダブルレベルアップ
    updated_pilot, _ = service.add_rewards(pilot, 300, 0)

    assert updated_pilot.level == 3
    assert updated_pilot.status_points == STATUS_POINTS_PER_LEVEL * 2


def test_allocate_status_points_basic() -> None:
    """基本的なステータスポイント割り振りをテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=5,
        exp=0,
        credits=1000,
        status_points=10,
        sht=0,
        mel=0,
        intel=0,
        ref=0,
        tou=0,
        luk=0,
    )

    updated_pilot = service.allocate_status_points(
        pilot, sht=2, mel=1, intel=2, ref=1, tou=2, luk=2
    )

    assert updated_pilot.sht == 2
    assert updated_pilot.mel == 1
    assert updated_pilot.intel == 2
    assert updated_pilot.ref == 1
    assert updated_pilot.tou == 2
    assert updated_pilot.luk == 2
    assert updated_pilot.status_points == 0  # 10 - (2+1+2+1+2+2)


def test_allocate_status_points_insufficient_points() -> None:
    """所持ポイント不足時はエラーになることをテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=2,
        exp=0,
        credits=1000,
        status_points=3,
    )

    with pytest.raises(ValueError, match="ステータスポイントが不足しています"):
        service.allocate_status_points(pilot, sht=5)  # 5 > 3


def test_allocate_status_points_negative_value_raises() -> None:
    """負の値を指定するとエラーになることをテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=5,
        exp=0,
        credits=1000,
        status_points=10,
    )

    with pytest.raises(ValueError, match="0以上"):
        service.allocate_status_points(pilot, sht=-1)


def test_allocate_status_points_partial() -> None:
    """一部のステータスにだけ割り振ることができるテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=5,
        exp=0,
        credits=1000,
        status_points=10,
        sht=0,
        mel=0,
        intel=0,
        ref=0,
        tou=0,
        luk=0,
    )

    updated_pilot = service.allocate_status_points(pilot, luk=4)

    assert updated_pilot.luk == 4
    assert updated_pilot.sht == 0
    assert updated_pilot.status_points == 6  # 10 - 4


def test_allocate_status_points_zero_allocation() -> None:
    """ゼロポイントを割り振ってもエラーにならないことをテスト."""
    session = MagicMock(spec=Session)
    service = PilotService(session)

    pilot = Pilot(
        user_id="test_user",
        name="Test Pilot",
        level=5,
        exp=0,
        credits=1000,
        status_points=5,
    )

    updated_pilot = service.allocate_status_points(pilot)  # all zeros

    assert updated_pilot.status_points == 5  # unchanged


def test_calculate_bounty_sums_killed_aces_only() -> None:
    """撃破したエース機の懸賞金だけを合計する."""
    ace = MobileSuit(
        name="Ace", max_hp=1, is_ace=True, bounty_exp=500, bounty_credits=900
    )
    other_ace = MobileSuit(
        name="Ace2", max_hp=1, is_ace=True, bounty_exp=10, bounty_credits=20
    )
    grunt = MobileSuit(name="Grunt", max_hp=1, bounty_exp=99, bounty_credits=99)

    assert PilotService.calculate_bounty([ace, other_ace, grunt]) == (510, 920)
    assert PilotService.calculate_bounty([grunt]) == (0, 0)
    assert PilotService.calculate_bounty([]) == (0, 0)
