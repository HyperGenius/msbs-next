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
from app.models.models import BattleEntry, BattleResult, BattleRoom, MobileSuit
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


def _process_room(session: Session, room: BattleRoom) -> None:
    """個別ルームの戦闘シミュレーションを実行.

    Args:
        session: データベースセッション
        room: 処理対象のルーム
    """
    # このルームのエントリーを取得
    entry_statement = select(BattleEntry).where(BattleEntry.room_id == room.id)
    entries = list(session.exec(entry_statement).all())

    if not entries:
        print("  警告: エントリーが見つかりません")
        return

    print(f"  参加者: {len(entries)} 機")

    # プレイヤーとエネミーに分ける
    # 簡易版: 最初のプレイヤーエントリーをplayer、残りをenemiesとする
    player_entries = [e for e in entries if not e.is_npc]
    npc_entries = [e for e in entries if e.is_npc]

    if not player_entries:
        print("  警告: プレイヤーエントリーがありません")
        return

    # 多人数対戦形式: 全員をenemiesとして扱い、最初のプレイヤーだけplayerとする
    # （本来はチーム分けなど高度な処理が必要だが、ここでは簡易実装）
    player_snapshot = player_entries[0].mobile_suit_snapshot
    player_unit = MobileSuit(**player_snapshot)
    player_unit.side = "PLAYER"

    # 他のユニットは全員敵として扱う
    enemy_units = []
    unit_to_entry_map = {}  # MobileSuit ID -> BattleEntry のマッピング

    for entry in player_entries[1:] + npc_entries:
        enemy_snapshot = entry.mobile_suit_snapshot
        enemy_unit = MobileSuit(**enemy_snapshot)
        enemy_unit.side = "ENEMY"
        enemy_units.append(enemy_unit)
        unit_to_entry_map[enemy_unit.id] = entry

    print(f"  プレイヤー: {player_unit.name}")
    print(f"  敵機: {len(enemy_units)} 機")

    # シミュレーション実行
    simulator = BattleSimulator(player_unit, enemy_units)

    max_turns = 100
    turn_count = 0
    while not simulator.is_finished and turn_count < max_turns:
        simulator.process_turn()
        turn_count += 1

    print(f"  戦闘終了: {turn_count} ターン")

    # 勝敗判定: プレイヤーが生き残っていれば勝利
    primary_player_win = player_unit.current_hp > 0

    # 撃墜数をカウント
    kills = sum(1 for e in enemy_units if e.current_hp <= 0)

    if primary_player_win:
        print(f"  結果: プレイヤー勝利 (撃墜: {kills}機)")
    else:
        print(f"  結果: プレイヤー敗北 (撃墜: {kills}機)")

    # 結果を保存（プレイヤーごと）
    pilot_service = PilotService(session)

    for entry in player_entries:
        # 各プレイヤーの勝敗を判定
        if entry.id == player_entries[0].id:
            # 最初のプレイヤー（実際にシミュレートされた）
            individual_win_loss = "WIN" if primary_player_win else "LOSE"
            individual_kills = kills
        else:
            # 他のプレイヤー（敵側として扱われた）
            # 実装簡略化のため、全員敗北扱い
            # TODO: 将来的にはチーム分けや複数の同時シミュレーションを実装
            individual_win_loss = "LOSE"
            individual_kills = 0

        battle_result = BattleResult(
            user_id=entry.user_id,
            room_id=room.id,
            win_loss=individual_win_loss,
            logs=[log.model_dump() for log in simulator.logs],
        )
        session.add(battle_result)

        # 報酬を付与（プレイヤーのみ）
        if entry.user_id:
            try:
                # パイロット情報を取得または作成
                pilot_name = entry.mobile_suit_snapshot.get("name", "Unknown Pilot")
                pilot = pilot_service.get_or_create_pilot(entry.user_id, pilot_name)

                # 報酬を計算
                exp_gained, credits_gained = pilot_service.calculate_battle_rewards(
                    win=individual_win_loss == "WIN",
                    kills=individual_kills,
                )

                # 報酬を付与
                pilot, reward_logs = pilot_service.add_rewards(
                    pilot, exp_gained, credits_gained
                )

                print(f"  報酬付与 ({entry.user_id}): {', '.join(reward_logs)}")

            except Exception as e:
                print(f"  警告: 報酬付与エラー ({entry.user_id}): {e}")
                traceback.print_exc()

    # ルームのステータスを更新
    room.status = "COMPLETED"
    session.add(room)

    # 変更をコミット
    session.commit()

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
