import os
import sys

# パスを通す（backendディレクトリ内で実行するため）
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.engine.simulation import BattleSimulator
from app.models.models import MobileSuit, Vector3, Weapon


def run():
    """シミュレーションを実行する."""
    # 1. 機体データ作成
    gundam = MobileSuit(
        id="ms01",
        name="ガンダム",
        max_hp=1000,
        current_hp=1000,
        armor=100,
        mobility=1.5,
        position=Vector3(x=0, y=0, z=0),  # 原点
        weapons=[
            Weapon(id="w01", name="ビームライフル", power=300, range=600, accuracy=80)
        ],
    )

    zaku = MobileSuit(
        id="ms02",
        name="ザクII",
        max_hp=800,
        current_hp=800,
        armor=50,
        mobility=1.0,
        position=Vector3(x=2000, y=2000, z=500),  # 遠く離れた場所
        weapons=[
            Weapon(id="w02", name="ザクマシンガン", power=100, range=400, accuracy=60)
        ],
    )

    print("--- シミュレーション開始 ---")
    print(f"{gundam.name} vs {zaku.name}")
    print(f"距離: {gundam.position.to_numpy()} <-> {zaku.position.to_numpy()}")
    print("-" * 30)

    # 2. シミュレーター初期化
    sim = BattleSimulator(gundam, zaku)

    # 3. ループ実行
    while not sim.is_finished and sim.turn < 20:  # 最大20ターンで打ち切り
        sim.process_turn()

    # 4. ログ出力
    for log in sim.logs:
        print(f"[Turn {log.turn}] {log.message}")


if __name__ == "__main__":
    run()
