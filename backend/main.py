from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

# DB関連
from app.core.auth import get_current_user_optional
from app.db import get_session
from app.engine.simulation import BattleSimulator
from app.models.models import BattleLog, MobileSuit, Vector3, Weapon
from app.routers import mobile_suits

app = FastAPI(title="MSBS-Next API")

# --- CORS設定 ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routerの登録
app.include_router(mobile_suits.router)

# --- Response Schemas ---
# models.py にあるクラスを使用する形でも良いですが、
# レスポンス構造用に定義が必要であればここに書くか models.py に Pydantic モデルとして定義します。
# ここでは簡易的にPydanticのBaseModelを使って定義しなおすか、SQLModelをそのまま使います。


class BattleResponse(BaseModel):
    """戦闘結果レスポンス."""

    winner_id: str | None
    logs: list[BattleLog]
    player_info: MobileSuit
    enemies_info: list[MobileSuit]


# --- API Endpoints ---


@app.get("/health")
def health() -> dict[str, str]:
    """ヘルスチェック."""
    return {"status": "ok", "message": "MSBS-Next API is running"}


@app.post("/api/battle/simulate", response_model=BattleResponse)
async def simulate_battle(
    session: Session = Depends(get_session),
    user_id: str | None = Depends(get_current_user_optional),
) -> BattleResponse:
    """DBから機体データを取得してシミュレーションを実行する."""
    # 1. プレイヤー機体を取得（最初の1機）
    player_statement = select(MobileSuit).limit(1)
    player_results = session.exec(player_statement).all()

    if len(player_results) < 1:
        raise HTTPException(
            status_code=400,
            detail="Not enough Mobile Suits in DB. Please run seed script or add data.",
        )

    # 2. プレイヤー機体を準備
    player = MobileSuit.model_validate(player_results[0].model_dump())
    player.current_hp = player.max_hp
    player.position = Vector3(x=0, y=0, z=0)
    player.side = "PLAYER"

    # 3. 敵機を動的に生成（ザクII × 3機）
    enemies = []
    enemy_positions = [
        Vector3(x=500, y=-200, z=0),
        Vector3(x=500, y=0, z=0),
        Vector3(x=500, y=200, z=0),
    ]

    for i, pos in enumerate(enemy_positions):
        enemy = MobileSuit(
            name=f"ザクII #{i+1}",
            max_hp=80,
            current_hp=80,
            armor=5,
            mobility=1.2,
            position=pos,
            weapons=[
                Weapon(
                    id=f"zaku_mg_{i}",
                    name="ザクマシンガン",
                    power=15,
                    range=400,
                    accuracy=70,
                )
            ],
            side="ENEMY",
        )
        enemies.append(enemy)

    # 4. シミュレーション実行
    sim = BattleSimulator(player, enemies)
    max_turns = 50
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    # 勝者判定
    winner_id = None
    if player.current_hp > 0 and all(e.current_hp <= 0 for e in enemies):
        winner_id = str(player.id)
    elif player.current_hp <= 0:
        # 敵の誰かが生き残っていれば敵の勝利
        winner_id = "ENEMY"

    return BattleResponse(
        winner_id=winner_id,
        logs=sim.logs,
        player_info=player,
        enemies_info=enemies,
    )
