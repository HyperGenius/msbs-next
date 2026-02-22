# backend/app/services/matching_service.py
"""マッチング処理を行うサービス."""

import random
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlmodel import Session, select

from app.core.npc_data import ACE_PILOTS, PERSONALITY_TYPES
from app.models.models import BattleEntry, BattleRoom, MobileSuit, Pilot, Vector3, Weapon
from app.services.pilot_service import PilotService


class MatchingService:
    """マッチング処理サービス."""

    def __init__(
        self,
        session: Session,
        room_size: int = 8,
        ace_spawn_rate: float = 0.05,
        npc_persistence_rate: float = 0.5,
    ):
        """初期化.

        Args:
            session: データベースセッション
            room_size: 1ルームあたりの定員（デフォルト: 8機）
            ace_spawn_rate: エースパイロットの出現確率（デフォルト: 5%）
            npc_persistence_rate: 既存の永続化NPCを再利用する割合（デフォルト: 50%）
        """
        self.session = session
        self.room_size = room_size
        self.ace_spawn_rate = ace_spawn_rate
        self.npc_persistence_rate = npc_persistence_rate

    def create_rooms(self) -> list[BattleRoom]:
        """未処理のエントリーを取得し、ルームを作成する.

        Returns:
            作成されたルームのリスト
        """
        # ステータスが OPEN のルームを取得
        statement = select(BattleRoom).where(BattleRoom.status == "OPEN")
        open_rooms = self.session.exec(statement).all()

        if not open_rooms:
            print("マッチング対象のルームがありません")
            return []

        created_rooms = []

        for room in open_rooms:
            # このルームのエントリーを取得
            entry_statement = select(BattleEntry).where(BattleEntry.room_id == room.id)
            entries = list(self.session.exec(entry_statement).all())

            if not entries:
                print(f"ルーム {room.id} にエントリーがありません")
                # scheduled_atが過去の場合、翌日の同時刻に更新する
                now = datetime.now(UTC)
                scheduled_at = room.scheduled_at
                # Ensure scheduled_at is timezone-aware for comparison
                if scheduled_at.tzinfo is None:
                    scheduled_at = scheduled_at.replace(tzinfo=UTC)
                if scheduled_at < now:
                    # 翌日の同時刻に更新
                    new_scheduled_at = scheduled_at + timedelta(days=1)
                    room.scheduled_at = new_scheduled_at
                    self.session.add(room)
                    print(
                        f"  エントリーがないため、スケジュールを延期しました: {new_scheduled_at}"
                    )
                continue

            print(f"ルーム {room.id}: {len(entries)} 件のエントリーを処理中...")

            # 不足分をNPCで埋める
            player_entries = [e for e in entries if not e.is_npc]
            npc_count = max(0, self.room_size - len(entries))

            if npc_count > 0:
                print(f"  NPC {npc_count} 体を生成します")

                # エースパイロットの出現判定（1回のみ）
                # ace_spawned = False
                if random.random() < self.ace_spawn_rate:
                    ace_suit = self._create_ace_pilot()
                    self.session.add(ace_suit)
                    self.session.flush()

                    npc_entry = BattleEntry(
                        user_id=None,
                        room_id=room.id,
                        mobile_suit_id=ace_suit.id,
                        mobile_suit_snapshot=ace_suit.model_dump(),
                        is_npc=True,
                    )
                    self.session.add(npc_entry)
                    entries.append(npc_entry)
                    # ace_spawned = True
                    print(
                        f"  ★ エースパイロット出現: {ace_suit.pilot_name} ({ace_suit.name})"
                    )
                    npc_count -= 1

                # 既存の永続化NPCを一定割合で取得
                persist_count = round(npc_count * self.npc_persistence_rate)
                persistent_npcs = self.select_npcs_for_room(persist_count)
                # 実際に取得できた数に応じて新規生成数を調整
                new_count = npc_count - len(persistent_npcs)

                for npc_suit, npc_pilot in persistent_npcs:
                    # 位置をリセット
                    npc_suit.position = Vector3(
                        x=random.uniform(-500, 500),
                        y=random.uniform(-500, 500),
                        z=random.uniform(0, 500),
                    )
                    npc_suit.current_hp = npc_suit.max_hp
                    self.session.add(npc_suit)
                    self.session.flush()

                    snapshot = npc_suit.model_dump()
                    snapshot["npc_pilot_level"] = npc_pilot.level

                    npc_entry = BattleEntry(
                        user_id=npc_pilot.user_id,
                        room_id=room.id,
                        mobile_suit_id=npc_suit.id,
                        mobile_suit_snapshot=snapshot,
                        is_npc=True,
                    )
                    self.session.add(npc_entry)
                    entries.append(npc_entry)
                    print(
                        f"  ♻ 既存NPC再利用: {npc_suit.pilot_name or npc_suit.name} (Lv.{npc_pilot.level})"
                    )

                # 残りは新規NPCで埋める
                pilot_service = PilotService(self.session)
                for _ in range(new_count):
                    npc_suit = self._create_npc_mobile_suit()
                    self.session.add(npc_suit)
                    self.session.flush()  # IDを取得するためにflush

                    # 新規NPC用のパイロットレコードを作成
                    pilot_name = npc_suit.pilot_name or npc_suit.name
                    personality = npc_suit.personality or "AGGRESSIVE"
                    npc_pilot = pilot_service.create_npc_pilot(pilot_name, personality)

                    # 機体を NPC パイロットの user_id に紐付ける
                    npc_suit.user_id = npc_pilot.user_id
                    self.session.add(npc_suit)
                    self.session.flush()

                    snapshot = npc_suit.model_dump()
                    snapshot["npc_pilot_level"] = npc_pilot.level

                    # NPCエントリーを作成
                    npc_entry = BattleEntry(
                        user_id=npc_pilot.user_id,
                        room_id=room.id,
                        mobile_suit_id=npc_suit.id,
                        mobile_suit_snapshot=snapshot,
                        is_npc=True,
                    )
                    self.session.add(npc_entry)
                    entries.append(npc_entry)

            # ルームのステータスを更新
            room.status = "WAITING"
            self.session.add(room)

            print(
                f"  ルーム {room.id} のマッチング完了: プレイヤー {len(player_entries)} 名 + NPC {npc_count} 体"
            )
            created_rooms.append(room)

        # 変更をコミット
        self.session.commit()

        print(f"\nマッチング完了: {len(created_rooms)} ルーム")
        return created_rooms

    def select_npcs_for_room(self, count: int) -> list[tuple[MobileSuit, Pilot]]:
        """DBから既存の永続化NPCをランダムに選択する.

        Args:
            count: 取得するNPC数

        Returns:
            (MobileSuit, Pilot) のタプルのリスト
        """
        if count <= 0:
            return []

        # is_npc=True のパイロットを取得
        pilot_statement = select(Pilot).where(Pilot.is_npc == True)  # noqa: E712
        npc_pilots = list(self.session.exec(pilot_statement).all())

        if not npc_pilots:
            return []

        # ランダムにシャッフルして必要数を選択
        selected_pilots = random.sample(npc_pilots, min(count, len(npc_pilots)))

        result = []
        for pilot in selected_pilots:
            # このパイロットの user_id に紐づく機体を取得
            suit_statement = (
                select(MobileSuit)
                .where(MobileSuit.user_id == pilot.user_id)
                .where(MobileSuit.side == "ENEMY")
            )
            suit = self.session.exec(suit_statement).first()
            if suit:
                result.append((suit, pilot))

        return result

    def _create_npc_mobile_suit(self) -> MobileSuit:
        """NPCのモビルスーツを生成する.

        Returns:
            生成されたNPCのモビルスーツ
        """
        # ランダムなNPC名
        npc_names = [
            "Zaku II",
            "Gouf",
            "Dom",
            "Gelgoog",
            "Rick Dom",
            "Acguy",
            "Z'Gok",
            "Gyan",
        ]
        name = f"{random.choice(npc_names)} (NPC)"

        # ランダムな武器
        weapons = [
            Weapon(
                id=f"npc_weapon_{uuid.uuid4().hex[:8]}",
                name="Zaku Machine Gun",
                power=random.randint(80, 120),
                range=random.randint(350, 450),
                accuracy=random.randint(60, 75),
            ),
            Weapon(
                id=f"npc_weapon_{uuid.uuid4().hex[:8]}",
                name="Heat Hawk",
                power=random.randint(120, 180),
                range=random.randint(50, 150),
                accuracy=random.randint(75, 85),
            ),
        ]

        # ランダムなステータス
        max_hp = random.randint(600, 900)
        armor = random.randint(30, 70)
        mobility = random.uniform(0.8, 1.5)

        # ランダムな初期位置（1000m x 1000m x 500m の空間）
        position = Vector3(
            x=random.uniform(-500, 500),
            y=random.uniform(-500, 500),
            z=random.uniform(0, 500),
        )

        # ランダムな性格を付与
        personality = random.choice(PERSONALITY_TYPES)

        # 性格に応じた戦術を設定
        if personality == "AGGRESSIVE":
            tactics_options = {
                "priority": random.choice(["CLOSEST", "WEAKEST"]),
                "range": "MELEE",
            }
        elif personality == "CAUTIOUS":
            tactics_options = {
                "priority": random.choice(["WEAKEST", "RANDOM"]),
                "range": "BALANCED",
            }
        else:  # SNIPER
            tactics_options = {
                "priority": "CLOSEST",
                "range": "RANGED",
            }

        npc = MobileSuit(
            name=name,
            max_hp=max_hp,
            current_hp=max_hp,
            armor=armor,
            mobility=mobility,
            position=position,
            weapons=random.sample(weapons, k=random.randint(1, 2)),
            side="ENEMY",
            tactics=tactics_options,
            user_id=None,  # NPCはユーザーIDなし
            personality=personality,  # 性格を設定
        )

        return npc

    def _create_ace_pilot(self) -> MobileSuit:
        """エースパイロットのモビルスーツを生成する.

        Returns:
            生成されたエースパイロットのモビルスーツ
        """
        # ランダムにエースパイロットを選択
        ace_data = cast(dict[str, Any], random.choice(ACE_PILOTS))
        ms_data = cast(dict[str, Any], ace_data["mobile_suit"])

        # ランダムな初期位置（1000m x 1000m x 500m の空間）
        position = Vector3(
            x=random.uniform(-500, 500),
            y=random.uniform(-500, 500),
            z=random.uniform(0, 500),
        )

        # weaponsをWeaponオブジェクトに変換（辞書の場合）
        weapons_list = ms_data["weapons"]
        if weapons_list and isinstance(weapons_list[0], dict):
            weapons_list = [Weapon(**w) for w in weapons_list]

        ace = MobileSuit(
            name=ms_data["name"],
            max_hp=ms_data["max_hp"],
            current_hp=ms_data["max_hp"],
            armor=ms_data["armor"],
            mobility=ms_data["mobility"],
            sensor_range=ms_data["sensor_range"],
            beam_resistance=ms_data["beam_resistance"],
            physical_resistance=ms_data["physical_resistance"],
            max_en=ms_data.get("max_en", 1000),
            en_recovery=ms_data.get("en_recovery", 100),
            position=position,
            weapons=weapons_list,
            side="ENEMY",
            tactics=ms_data["tactics"],
            user_id=None,
            personality=ace_data["personality"],
            is_ace=True,
            ace_id=ace_data["id"],
            pilot_name=ace_data["pilot_name"],
            bounty_exp=ace_data["bounty_exp"],
            bounty_credits=ace_data["bounty_credits"],
        )

        return ace
