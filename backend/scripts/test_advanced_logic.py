"""Debug script to demonstrate advanced battle logic with weapon types and resistances."""

import os
import sys

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def run_beam_vs_beam_resistant():
    """ビーム兵器 vs 対ビーム装甲のテスト."""
    print("=" * 60)
    print("テスト1: ビーム兵器 vs 対ビーム装甲")
    print("=" * 60)

    # ビーム兵器を持つガンダム
    gundam = MobileSuit(
        name="ガンダム (ビーム)",
        max_hp=1000,
        current_hp=1000,
        armor=100,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="w01",
                name="ビームライフル",
                power=300,
                range=600,
                accuracy=80,
                type="BEAM",
                optimal_range=400.0,
                decay_rate=0.05,
            )
        ],
        side="PLAYER",
        beam_resistance=0.2,
        physical_resistance=0.1,
    )

    # 対ビーム装甲を持つザク
    zaku = MobileSuit(
        name="ザクII (対ビーム装甲30%)",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        position=Vector3(x=400, y=0, z=0),  # 最適射程に配置
        weapons=[
            Weapon(
                id="w02",
                name="ザクマシンガン",
                power=100,
                range=400,
                accuracy=60,
                type="PHYSICAL",
                optimal_range=300.0,
                decay_rate=0.08,
            )
        ],
        side="ENEMY",
        beam_resistance=0.3,  # 30%カット
        physical_resistance=0.05,
    )

    print(f"{gundam.name} vs {zaku.name}")
    print(f"初期距離: {400}m (ビームライフルの最適射程)")
    print(f"ザクの対ビーム装甲: {zaku.beam_resistance * 100}%")
    print("-" * 60)

    sim = BattleSimulator(gundam, [zaku])

    # 5ターン実行
    for _ in range(5):
        if sim.is_finished:
            break
        sim.process_turn()

    # ログ出力
    for log in sim.logs:
        print(f"[Turn {log.turn}] {log.message}")

    print(f"\n残りHP: {gundam.name}={gundam.current_hp}, {zaku.name}={zaku.current_hp}")
    print()


def run_physical_vs_physical_resistant():
    """実弾兵器 vs 対実弾装甲のテスト."""
    print("=" * 60)
    print("テスト2: 実弾兵器 vs 対実弾装甲")
    print("=" * 60)

    # 実弾兵器を持つザク
    zaku_attacker = MobileSuit(
        name="ザクII (実弾)",
        max_hp=800,
        current_hp=800,
        armor=60,
        mobility=1.2,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="w03",
                name="ザクマシンガン改",
                power=150,
                range=450,
                accuracy=70,
                type="PHYSICAL",
                optimal_range=300.0,
                decay_rate=0.08,
            )
        ],
        side="PLAYER",
        beam_resistance=0.05,
        physical_resistance=0.25,  # 25%カット
    )

    # 対実弾装甲を持つガンダム
    gundam_defender = MobileSuit(
        name="ガンダム (対実弾装甲20%)",
        max_hp=1000,
        current_hp=1000,
        armor=100,
        mobility=1.5,
        position=Vector3(x=300, y=0, z=0),  # 最適射程に配置
        weapons=[
            Weapon(
                id="w04",
                name="ビームライフル",
                power=300,
                range=600,
                accuracy=80,
                type="BEAM",
                optimal_range=400.0,
                decay_rate=0.05,
            )
        ],
        side="ENEMY",
        beam_resistance=0.15,
        physical_resistance=0.2,  # 20%カット
    )

    print(f"{zaku_attacker.name} vs {gundam_defender.name}")
    print(f"初期距離: {300}m (マシンガンの最適射程)")
    print(f"ガンダムの対実弾装甲: {gundam_defender.physical_resistance * 100}%")
    print("-" * 60)

    sim = BattleSimulator(zaku_attacker, [gundam_defender])

    # 5ターン実行
    for _ in range(5):
        if sim.is_finished:
            break
        sim.process_turn()

    # ログ出力
    for log in sim.logs:
        print(f"[Turn {log.turn}] {log.message}")

    print(
        f"\n残りHP: {zaku_attacker.name}={zaku_attacker.current_hp}, {gundam_defender.name}={gundam_defender.current_hp}"
    )
    print()


def run_optimal_range_test():
    """最適射程のテスト."""
    print("=" * 60)
    print("テスト3: 最適射程の効果")
    print("=" * 60)

    gundam = MobileSuit(
        name="ガンダム",
        max_hp=1000,
        current_hp=1000,
        armor=100,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),
        weapons=[
            Weapon(
                id="w05",
                name="ビームライフル",
                power=300,
                range=600,
                accuracy=80,
                type="BEAM",
                optimal_range=400.0,
                decay_rate=0.05,
            )
        ],
        side="PLAYER",
        beam_resistance=0.2,
        physical_resistance=0.1,
    )

    # ケース1: 最適射程（400m）
    zaku_optimal = MobileSuit(
        name="ザクII (最適射程)",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        position=Vector3(x=400, y=0, z=0),
        weapons=[
            Weapon(
                id="w06",
                name="ザクマシンガン",
                power=100,
                range=400,
                accuracy=60,
                type="PHYSICAL",
                optimal_range=300.0,
                decay_rate=0.08,
            )
        ],
        side="ENEMY",
        beam_resistance=0.05,
        physical_resistance=0.2,
    )

    print("ケース1: 敵は最適射程（400m）に配置")
    sim1 = BattleSimulator(gundam, [zaku_optimal])
    sim1.process_turn()
    for log in sim1.logs:
        if log.actor_id == gundam.id:
            print(f"  {log.message}")

    # ケース2: 遠距離（600m）
    gundam.current_hp = 1000  # リセット
    zaku_far = MobileSuit(
        name="ザクII (遠距離)",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        position=Vector3(x=600, y=0, z=0),
        weapons=[
            Weapon(
                id="w07",
                name="ザクマシンガン",
                power=100,
                range=400,
                accuracy=60,
                type="PHYSICAL",
                optimal_range=300.0,
                decay_rate=0.08,
            )
        ],
        side="ENEMY",
        beam_resistance=0.05,
        physical_resistance=0.2,
    )

    print("\nケース2: 敵は遠距離（600m）に配置")
    sim2 = BattleSimulator(gundam, [zaku_far])
    sim2.process_turn()
    for log in sim2.logs:
        if log.actor_id == gundam.id:
            print(f"  {log.message}")

    print()


if __name__ == "__main__":
    run_beam_vs_beam_resistant()
    run_physical_vs_physical_resistant()
    run_optimal_range_test()
    print("=" * 60)
    print("すべてのテスト完了！")
    print("=" * 60)
