# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.engine.simulation import BattleSimulator

# 自作モジュールのインポート
from app.models.models import BattleLog, MobileSuit

app = FastAPI(title="MSBS-Next API")

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


# --- API Endpoints ---


@app.get("/health")
def health() -> dict[str, str]:
    """ヘルスチェック用のエンドポイント."""
    return {"status": "ok", "message": "MSBS-Next API is running"}


@app.post("/api/battle/simulate", response_model=BattleResponse)
def simulate_battle(req: BattleRequest) -> BattleResponse:
    """POSTされた2機のデータを受け取り、シミュレーションを実行してログを返す."""
    # シミュレーター初期化
    sim = BattleSimulator(req.ms1, req.ms2)

    # 決着がつくか、最大ターン数(例:50)になるまで回す
    max_turns = 50
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    # 勝者判定（生き残っている方）
    winner_id = None
    if sim.ms1.current_hp > 0 and sim.ms2.current_hp <= 0:
        winner_id = sim.ms1.id
    elif sim.ms2.current_hp > 0 and sim.ms1.current_hp <= 0:
        winner_id = sim.ms2.id

    return BattleResponse(winner_id=winner_id, logs=sim.logs)
