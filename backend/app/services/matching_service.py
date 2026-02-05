# backend/app/services/matching_service.py
"""マッチング処理を行うサービス."""

import random
import uuid

from sqlmodel import Session, select

from app.models.models import BattleEntry, BattleRoom, MobileSuit, Vector3, Weapon


class MatchingService:
    """マッチング処理サービス."""

    def __init__(self, session: Session, room_size: int = 8):
        """初期化.

        Args:
            session: データベースセッション
            room_size: 1ルームあたりの定員（デフォルト: 8機）
        """
        self.session = session
        self.room_size = room_size

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
            entry_statement = select(BattleEntry).where(
                BattleEntry.room_id == room.id
            )
            entries = list(self.session.exec(entry_statement).all())

            if not entries:
                print(f"ルーム {room.id} にエントリーがありません")
                continue

            print(f"ルーム {room.id}: {len(entries)} 件のエントリーを処理中...")

            # 不足分をNPCで埋める
            player_entries = [e for e in entries if not e.is_npc]
            npc_count = max(0, self.room_size - len(entries))

            if npc_count > 0:
                print(f"  NPC {npc_count} 体を生成します")
                for _ in range(npc_count):
                    npc_suit = self._create_npc_mobile_suit()
                    self.session.add(npc_suit)
                    self.session.flush()  # IDを取得するためにflush

                    # NPCエントリーを作成
                    npc_entry = BattleEntry(
                        user_id=None,
                        room_id=room.id,
                        mobile_suit_id=npc_suit.id,
                        mobile_suit_snapshot=npc_suit.model_dump(),
                        is_npc=True,
                    )
                    self.session.add(npc_entry)
                    entries.append(npc_entry)

            # ルームのステータスを更新
            room.status = "WAITING"
            self.session.add(room)

            print(f"  ルーム {room.id} のマッチング完了: プレイヤー {len(player_entries)} 名 + NPC {npc_count} 体")
            created_rooms.append(room)

        # 変更をコミット
        self.session.commit()

        print(f"\nマッチング完了: {len(created_rooms)} ルーム")
        return created_rooms

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

        # ランダムな戦術
        tactics_options = {
            "priority": random.choice(["CLOSEST", "WEAKEST", "RANDOM"]),
            "range": random.choice(["MELEE", "RANGED", "BALANCED"]),
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
        )

        return npc
