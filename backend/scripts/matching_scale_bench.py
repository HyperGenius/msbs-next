#!/usr/bin/env python3
# backend/scripts/matching_scale_bench.py
"""マッチングフェーズのDBラウンドトリップ計測ベンチマーク（Issue #448）.

`MatchingService.create_rooms()` の NPC補充処理（永続化NPC取得のN+1、
新規NPC生成ループの `session.flush()` 多発）を最適化した効果を確認するため、
room_size = 8 / 50 / 100 でルームを1部屋ずつ作成し、SQL発行回数と処理時間を
計測する。in-memory SQLite を使うため Neon への実レイテンシは再現できないが、
「クエリ発行回数が room_size に対して線形に膨れ上がらないか」は確認できる。

Usage:
    python scripts/matching_scale_bench.py
    python scripts/matching_scale_bench.py --sizes 8,50,100
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import sys
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db import json_serializer
from app.models.models import (
    BattleEntry,
    BattleRoom,
    MobileSuit,
    Pilot,
    Vector3,
    Weapon,
)
from app.services.matching_service import MatchingService


def _seed_persistent_npc_pool(session: Session, count: int) -> None:
    """既存の永続化NPC（Pilot + MobileSuit）を count 体分あらかじめDBに投入する."""
    for i in range(count):
        user_id = f"npc-pool-{uuid.uuid4().hex[:8]}"
        pilot = Pilot(
            user_id=user_id,
            name=f"Persistent NPC {i}",
            is_npc=True,
            npc_personality="AGGRESSIVE",
            level=1,
            exp=0,
            credits=0,
        )
        suit = MobileSuit(
            name=f"Persistent NPC Suit {i}",
            max_hp=800,
            current_hp=800,
            armor=40,
            mobility=1.0,
            position=Vector3(x=0, y=0, z=0),
            weapons=[
                Weapon(
                    id=f"npc_pool_weapon_{i}",
                    name="Heat Hawk",
                    power=120,
                    range=100,
                    accuracy=80,
                )
            ],
            side="ENEMY",
            user_id=user_id,
        )
        session.add(pilot)
        session.add(suit)
    session.commit()


def _seed_room(session: Session, player_count: int) -> BattleRoom:
    """OPENルームを1つ作成し、player_count人分のプレイヤーエントリーを詰める."""
    room = BattleRoom(status="OPEN", scheduled_at=datetime.now(UTC))
    session.add(room)
    session.flush()

    for i in range(player_count):
        user_id = f"player-{uuid.uuid4().hex[:8]}"
        suit = MobileSuit(
            name=f"Player Suit {i}",
            max_hp=1000,
            current_hp=1000,
            armor=50,
            mobility=1.0,
            position=Vector3(x=0, y=0, z=0),
            weapons=[
                Weapon(
                    id=f"weapon_{i}",
                    name="Beam Rifle",
                    power=100,
                    range=500,
                    accuracy=80,
                )
            ],
            side="PLAYER",
            user_id=user_id,
        )
        session.add(suit)
        session.flush()

        entry = BattleEntry(
            user_id=user_id,
            room_id=room.id,
            mobile_suit_id=suit.id,
            mobile_suit_snapshot=suit.model_dump(),
            is_npc=False,
        )
        session.add(entry)

    session.commit()
    return room


def bench_room_size(room_size: int, player_count: int) -> tuple[int, float]:
    """指定 room_size で1ルームぶんの create_rooms() を実行し、(SQL発行回数, 秒) を返す."""
    engine = create_engine("sqlite:///:memory:", json_serializer=json_serializer)
    SQLModel.metadata.create_all(engine)

    query_count = 0

    def _count_queries(*_args: object, **_kwargs: object) -> None:
        nonlocal query_count
        query_count += 1

    event.listen(engine, "before_cursor_execute", _count_queries)

    with Session(engine) as session:
        # 永続化NPC再利用の効果を測るため、あらかじめ再利用対象のNPCプールを用意しておく
        # （npc_persistence_rate=0.5 で半数が再利用対象になる想定のため room_size 分用意）
        _seed_persistent_npc_pool(session, room_size)
        _seed_room(session, player_count)

        query_count = 0  # 計測対象は create_rooms() 呼び出し以降のみ
        matching_service = MatchingService(session, room_size=room_size)

        start = time.perf_counter()
        with contextlib.redirect_stdout(io.StringIO()):
            matching_service.create_rooms()
        elapsed = time.perf_counter() - start

    return query_count, elapsed


def main() -> None:
    """CLI エントリポイント: 引数を解析しベンチマークを実行して結果を表示する."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes",
        type=str,
        default="8,50,100",
        help="カンマ区切りの room_size 一覧（デフォルト: 8,50,100）",
    )
    parser.add_argument(
        "--player-count",
        type=int,
        default=1,
        help="事前投入するプレイヤーエントリー数（残りはNPCで補充される、デフォルト: 1）",
    )
    args = parser.parse_args()

    sizes = [int(s.strip()) for s in args.sizes.split(",") if s.strip()]

    print(f"{'room_size':>10} | {'sql queries':>12} | {'elapsed sec':>12}")
    print("-" * 40)
    for size in sizes:
        query_count, elapsed = bench_room_size(size, args.player_count)
        print(f"{size:>10} | {query_count:>12} | {elapsed:>12.4f}")


if __name__ == "__main__":
    main()
