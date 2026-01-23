from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, select

# DB関連
from app.core.auth import get_current_user_optional
from app.db import get_session
from app.engine.simulation import BattleSimulator
from app.models.models import BattleLog, MobileSuit, Vector3
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
    ms1_info: MobileSuit
    ms2_info: MobileSuit


# --- API Endpoints ---


@app.get("/health")
def health() -> dict[str, str]:
    """ヘルスチェック."""
    return {"status": "ok", "message": "MSBS-Next API is running"}


@app.post("/api/battle/simulate", response_model=BattleResponse)
async def simulate_battle(
    session: Session = Depends(get_session),
    user_id: str | None = Depends(get_current_user_optional)
) -> BattleResponse:
    """DBから機体データを取得してシミュレーションを実行する."""
    # 1. DBから全機体データを取得 (SQLModel)
    statement = select(MobileSuit).limit(2)
    results = session.exec(statement).all()
    data = list(results)

    if len(data) < 2:
        raise HTTPException(
            status_code=400,
            detail="Not enough Mobile Suits in DB. Please run seed script or add data.",
        )

    # 2. シミュレーション用にデータを準備
    # DBから取得した直後の ms_data.weapons は list[dict] になっています。
    # シミュレーションロジックは list[Weapon] (オブジェクト) を期待しているため、
    # model_validate を通して強制的にオブジェクトへ変換します。

    # model_dump() で一度辞書化し、model_validate() で再パースしてネストされたモデルも復元
    ms1 = MobileSuit.model_validate(data[0].model_dump())
    ms2 = MobileSuit.model_validate(data[1].model_dump())

    # 戦闘開始位置のリセット (DBには保存しない一時的な状態)
    ms1.current_hp = ms1.max_hp
    ms1.position = Vector3(x=-500, y=-500, z=0)

    ms2.current_hp = ms2.max_hp
    ms2.position = Vector3(x=500, y=500, z=0)

    # 3. シミュレーション実行
    sim = BattleSimulator(ms1, ms2)
    max_turns = 50
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    # 勝者判定 (UUIDをstrに変換して比較)
    winner_id = None
    if ms1.current_hp > 0 and ms2.current_hp <= 0:
        winner_id = str(ms1.id)
    elif ms2.current_hp > 0 and ms1.current_hp <= 0:
        winner_id = str(ms2.id)

    return BattleResponse(
        winner_id=winner_id, logs=sim.logs, ms1_info=ms1, ms2_info=ms2
    )
