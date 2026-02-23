#!/usr/bin/env python3
# backend/scripts/run_batch.py
"""定期実行バッチスクリプト.

このスクリプトは以下の処理を行います:
1. マッチング: OPENルームのエントリーをグループ化し、不足分をNPCで埋める
2. シミュレーション: 各ルームで戦闘を実行
3. 結果保存: BattleResultを保存し、ルームのステータスを更新
"""

import os
import sys
import traceback
from datetime import UTC, datetime, timedelta

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session, select

from app.db import engine
from app.engine.simulation import BattleSimulator
from app.models.models import (
    BattleEntry,
    BattleResult,
    BattleRoom,
    MobileSuit,
    Vector3,
    Weapon,
)
from app.services.matching_service import MatchingService
from app.services.pilot_service import PilotService
from app.services.ranking_service import RankingService


def run_matching_phase(session: Session) -> list[BattleRoom]:
    """マッチングフェーズ: エントリーをルームに割り当てる.

    Args:
        session: データベースセッション

    Returns:
        マッチング完了したルームのリスト
    """
    print("=" * 60)
    print("マッチングフェーズを開始")
    print("=" * 60)

    matching_service = MatchingService(session)
    rooms = matching_service.create_rooms()

    print(f"\nマッチング完了: {len(rooms)} ルームが準備完了")
    return rooms


def run_simulation_phase(session: Session) -> None:
    """シミュレーションフェーズ: WAITINGルームで戦闘を実行.

    Args:
        session: データベースセッション
    """
    print("\n" + "=" * 60)
    print("シミュレーションフェーズを開始")
    print("=" * 60)

    # WAITING状態のルームを取得
    statement = select(BattleRoom).where(BattleRoom.status == "WAITING")
    waiting_rooms = list(session.exec(statement).all())

    if not waiting_rooms:
        print("実行対象のルームがありません")
        return

    print(f"{len(waiting_rooms)} ルームで戦闘を実行します\n")

    for room in waiting_rooms:
        try:
            print(f"ルームID: {room.id} の処理を開始")
            _process_room(session, room)
            print(f"ルームID: {room.id} の処理が完了しました\n")
        except Exception as e:
            print(f"エラー: ルームID {room.id} の処理中にエラーが発生しました")
            print(f"  {e}")
            traceback.print_exc()
            # エラーが発生してもルームの処理を継続
            continue


def _convert_snapshot_to_mobile_suit(snapshot: dict) -> MobileSuit:
    """スナップショットをMobileSuitオブジェクトに変換.

    Args:
        snapshot: MobileSuitのスナップショット辞書

    Returns:
        変換されたMobileSuitオブジェクト
    """
    # positionとvelocityをVector3オブジェクトに変換
    if "position" in snapshot and isinstance(snapshot["position"], dict):
        snapshot["position"] = Vector3(**snapshot["position"])
    if "velocity" in snapshot and isinstance(snapshot["velocity"], dict):
        snapshot["velocity"] = Vector3(**snapshot["velocity"])
    # weaponsフィールドをWeaponオブジェクトに変換
    if "weapons" in snapshot and isinstance(snapshot["weapons"], list):
        snapshot["weapons"] = [
            Weapon(**w) if isinstance(w, dict) else w for w in snapshot["weapons"]
        ]
    # MobileSuit モデルにないスナップショット固有のキーを除去
    ms_fields = set(MobileSuit.model_fields.keys())
    filtered = {k: v for k, v in snapshot.items() if k in ms_fields}
    return MobileSuit(**filtered)


def _prepare_battle_units(
    player_entries: list[BattleEntry], npc_entries: list[BattleEntry]
) -> tuple[MobileSuit, list[MobileSuit], dict]:
    """プレイヤーと敵ユニットを準備.

    Args:
        player_entries: プレイヤーエントリーのリスト
        npc_entries: NPCエントリーのリスト

    Returns:
        (プレイヤーユニット, 敵ユニットリスト, ユニットIDとエントリーのマッピング)
    """
    # 最初のプレイヤーをplayerとして設定
    player_unit = _convert_snapshot_to_mobile_suit(
        player_entries[0].mobile_suit_snapshot
    )
    player_unit.side = "PLAYER"

    # 他のユニットは全員敵として扱う
    enemy_units = []
    unit_to_entry_map = {}

    for entry in player_entries[1:] + npc_entries:
        enemy_unit = _convert_snapshot_to_mobile_suit(entry.mobile_suit_snapshot)
        enemy_unit.side = "ENEMY"
        enemy_units.append(enemy_unit)
        unit_to_entry_map[enemy_unit.id] = entry

    return player_unit, enemy_units, unit_to_entry_map


def _run_simulation(
    player_unit: MobileSuit, enemy_units: list[MobileSuit]
) -> tuple[BattleSimulator, bool, int]:
    """戦闘シミュレーションを実行.

    Args:
        player_unit: プレイヤーユニット
        enemy_units: 敵ユニットリスト

    Returns:
        (シミュレーター, 勝利フラグ, 撃墜数)
    """
    simulator = BattleSimulator(player_unit, enemy_units)

    max_turns = 100
    turn_count = 0
    while not simulator.is_finished and turn_count < max_turns:
        simulator.process_turn()
        turn_count += 1

    print(f"  戦闘終了: {turn_count} ターン")

    # 勝敗判定
    primary_player_win = player_unit.current_hp > 0
    kills = sum(1 for e in enemy_units if e.current_hp <= 0)

    return simulator, primary_player_win, kills


def _save_battle_results(
    session: Session,
    room: BattleRoom,
    player_entries: list[BattleEntry],
    npc_entries: list[BattleEntry],
    simulator: BattleSimulator,
    primary_player_win: bool,
    kills: int,
    player_unit: MobileSuit,
    enemy_units: list[MobileSuit],
) -> None:
    """戦闘結果を保存し報酬を付与.

    Args:
        session: データベースセッション
        room: ルーム
        player_entries: プレイヤーエントリーリスト
        npc_entries: NPCエントリーリスト
        simulator: シミュレーター
        primary_player_win: 勝利フラグ
        kills: 撃墜数
        player_unit: プレイヤーユニット（スナップショット保存用）
        enemy_units: 敵ユニットリスト（スナップショット保存用）
    """
    pilot_service = PilotService(session)

    for entry in player_entries:
        # 各プレイヤーの勝敗を判定
        if entry.id == player_entries[0].id:
            individual_win_loss = "WIN" if primary_player_win else "LOSE"
            individual_kills = kills
        else:
            individual_win_loss = "LOSE"
            individual_kills = 0

        battle_result = BattleResult(
            user_id=entry.user_id,
            room_id=room.id,
            win_loss=individual_win_loss,
            logs=[log.model_dump() for log in simulator.logs],
            player_info=player_unit.model_dump(),
            enemies_info=[e.model_dump() for e in enemy_units],
        )
        session.add(battle_result)

        # 報酬を付与
        if entry.user_id:
            try:
                pilot_name = entry.mobile_suit_snapshot.get("name", "Unknown Pilot")
                pilot = pilot_service.get_or_create_pilot(entry.user_id, pilot_name)

                exp_gained, credits_gained = pilot_service.calculate_battle_rewards(
                    win=individual_win_loss == "WIN",
                    kills=individual_kills,
                )

                pilot, reward_logs = pilot_service.add_rewards(
                    pilot, exp_gained, credits_gained
                )

                print(f"  報酬付与 ({entry.user_id}): {', '.join(reward_logs)}")

            except Exception as e:
                print(f"  警告: 報酬付与エラー ({entry.user_id}): {e}")
                traceback.print_exc()

    # NPC の成長処理
    for npc_entry in npc_entries:
        if npc_entry.user_id:
            try:
                npc_pilot = pilot_service.get_npc_pilot(npc_entry.user_id)
                if npc_pilot:
                    # NPC はプレイヤーが勝てば敗北、プレイヤーが負ければ勝利
                    npc_win = not primary_player_win
                    exp_gained, credits_gained = pilot_service.calculate_battle_rewards(
                        win=npc_win,
                        kills=0,
                    )
                    npc_pilot, reward_logs = pilot_service.add_rewards(
                        npc_pilot, exp_gained, credits_gained
                    )
                    print(f"  NPC成長 ({npc_pilot.name}): {', '.join(reward_logs)}")
            except Exception as e:
                print(f"  警告: NPC成長エラー ({npc_entry.user_id}): {e}")
                traceback.print_exc()

    room.status = "COMPLETED"
    session.add(room)
    session.commit()


def _process_room(session: Session, room: BattleRoom) -> None:
    """個別ルームの戦闘シミュレーションを実行.

    Args:
        session: データベースセッション
        room: 処理対象のルーム
    """
    # エントリーを取得
    entry_statement = select(BattleEntry).where(BattleEntry.room_id == room.id)
    entries = list(session.exec(entry_statement).all())

    if not entries:
        print("  警告: エントリーが見つかりません")
        return

    print(f"  参加者: {len(entries)} 機")

    # プレイヤーとNPCに分ける
    player_entries = [e for e in entries if not e.is_npc]
    npc_entries = [e for e in entries if e.is_npc]

    if not player_entries:
        print("  警告: プレイヤーエントリーがありません")
        return

    # ユニット準備
    player_unit, enemy_units, _ = _prepare_battle_units(player_entries, npc_entries)

    print(f"  プレイヤー: {player_unit.name}")
    print(f"  敵機: {len(enemy_units)} 機")

    # シミュレーション実行
    simulator, primary_player_win, kills = _run_simulation(player_unit, enemy_units)

    if primary_player_win:
        print(f"  結果: プレイヤー勝利 (撃墜: {kills}機)")
    else:
        print(f"  結果: プレイヤー敗北 (撃墜: {kills}機)")

    # 結果保存
    _save_battle_results(
        session,
        room,
        player_entries,
        npc_entries,
        simulator,
        primary_player_win,
        kills,
        player_unit,
        enemy_units,
    )

    print("  結果を保存しました")


def create_next_open_room(session: Session) -> None:
    """次の募集期間用の OPEN ルームを作成する.

    Args:
        session: データベースセッション
    """
    print("\n" + "=" * 60)
    print("次回バトル用ルーム作成フェーズを開始")
    print("=" * 60)

    # 既存の OPEN ルームがあるか確認
    statement = select(BattleRoom).where(BattleRoom.status == "OPEN")
    existing_room = session.exec(statement).first()

    if existing_room:
        print("既存のOPENルームが存在します。スキップします。")
        print(f"  ルームID: {existing_room.id}")
        print(f"  予定時刻: {existing_room.scheduled_at}")
        return

    # 次の21:00 JST (= 12:00 UTC) を予定時刻とする
    now = datetime.now(UTC)
    scheduled_time = now.replace(hour=12, minute=0, second=0, microsecond=0)
    if now.hour >= 12:
        scheduled_time += timedelta(days=1)

    new_room = BattleRoom(
        status="OPEN",
        scheduled_at=scheduled_time,
    )
    session.add(new_room)
    session.commit()
    session.refresh(new_room)

    print("新しいOPENルームを作成しました")
    print(f"  ルームID: {new_room.id}")
    print(f"  予定時刻: {new_room.scheduled_at}")


def update_rankings(session: Session) -> None:
    """ランキング更新フェーズ: バトル結果を集計してランキングを更新.

    Args:
        session: データベースセッション
    """
    print("\n" + "=" * 60)
    print("ランキング更新フェーズを開始")
    print("=" * 60)

    ranking_service = RankingService(session)
    ranking_service.calculate_ranking()

    print("ランキングを更新しました")


def main() -> None:
    """メイン処理."""
    print("\n" + "=" * 60)
    print("定期実行バッチを開始")
    print("=" * 60 + "\n")

    with Session(engine) as session:
        # フェーズ1: マッチング
        run_matching_phase(session)

        # フェーズ2: シミュレーション
        run_simulation_phase(session)

        # フェーズ3: ランキング更新
        update_rankings(session)

        # フェーズ4: 次回バトル用のルームを作成
        create_next_open_room(session)

    print("\n" + "=" * 60)
    print("定期実行バッチが完了しました")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n致命的なエラー: {e}")
        traceback.print_exc()
        sys.exit(1)
