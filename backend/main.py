# backend/main.py

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# DB関連
from app.db import supabase
from app.engine.simulation import BattleSimulator
from app.models.models import BattleLog, MobileSuit, Vector3

# Router
from app.routers import mobile_suits

app = FastAPI(title="MSBS-Next API")

# Routerの登録
app.include_router(mobile_suits.router)

# --- CORS設定 (Frontendからのアクセスを許可) ---
origins = [
    "http://localhost:3000",  # Next.js local
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Schemas ---
class BattleRequest(BaseModel):
    """リクエストボディの定義: 戦わせる2機を受け取る."""

    ms1: MobileSuit
    ms2: MobileSuit


class BattleResponse(BaseModel):
    """レスポンスの定義: ログと勝者IDを返す."""

    winner_id: str | None
    logs: list[BattleLog]
    ms1_info: MobileSuit
    ms2_info: MobileSuit


# --- API Endpoints ---


@app.get("/health")
def health() -> dict[str, str]:
    """ヘルスチェック用のエンドポイント."""
    return {"status": "ok", "message": "MSBS-Next API is running"}


@app.post("/api/battle/simulate", response_model=BattleResponse)
def simulate_battle() -> BattleResponse:
    """DBから機体データを取得してシミュレーションを実行する."""
    # 1. DBから全機体データを取得 (本来はID指定などで絞り込む)
    response = supabase.table("mobile_suits").select("*").execute()
    data = response.data

    if len(data) < 2:
        raise HTTPException(status_code=400, detail="Not enough Mobile Suits in DB")

    # Seedデータでは [0]=ガンダム, [1]=ザク と仮定
    # ※ 本来はランダムマッチングやID指定ロジックが入ります
    ms1_data = data[0]
    ms2_data = data[1]

    # 2. Pydanticモデルに変換 & 戦闘用パラメータの注入
    # DBには「位置」や「現在HP」がないので、ここで設定します

    # MS1 (ガンダム) の初期化
    ms1 = MobileSuit(
        **ms1_data,  # name, max_hp, armor, mobility, weaponsなどを展開
        current_hp=ms1_data["max_hp"],  # type: ignore
        position=Vector3(x=-500, y=-500, z=0),  # 初期位置
    )  # type: ignore

    # MS2 (ザク) の初期化
    ms2 = MobileSuit(
        **ms2_data,
        current_hp=ms2_data["max_hp"],  # type: ignore
        position=Vector3(x=500, y=500, z=0),
    )  # type: ignore

    # 3. シミュレーション実行
    sim = BattleSimulator(ms1, ms2)
    max_turns = 50
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    # 勝者判定
    winner_id = None
    if sim.ms1.current_hp > 0 and sim.ms2.current_hp <= 0:
        winner_id = sim.ms1.id
    elif sim.ms2.current_hp > 0 and sim.ms1.current_hp <= 0:
        winner_id = sim.ms2.id

    return BattleResponse(
        winner_id=winner_id, logs=sim.logs, ms1_info=ms1, ms2_info=ms2
    )
