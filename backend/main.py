from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlmodel import Session, desc, select

# DB関連
from app.core.auth import get_current_user_optional
from app.db import get_session
from app.engine.simulation import BattleSimulator
from app.models.models import (
    BattleLog,
    BattleResult,
    Mission,
    MobileSuit,
    Vector3,
    Weapon,
)
from app.routers import engineering, entries, mobile_suits, pilots, shop

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
app.include_router(entries.router)
app.include_router(pilots.router)
app.include_router(shop.router)
app.include_router(engineering.router)

# --- Response Schemas ---
# models.py にあるクラスを使用する形でも良いですが、
# レスポンス構造用に定義が必要であればここに書くか models.py に Pydantic モデルとして定義します。
# ここでは簡易的にPydanticのBaseModelを使って定義しなおすか、SQLModelをそのまま使います。


class BattleRewards(BaseModel):
    """戦闘報酬."""

    exp_gained: int
    credits_gained: int
    level_before: int
    level_after: int
    total_exp: int
    total_credits: int


class BattleResponse(BaseModel):
    """戦闘結果レスポンス."""

    winner_id: str | None
    logs: list[BattleLog]
    player_info: MobileSuit
    enemies_info: list[MobileSuit]
    rewards: BattleRewards | None = None


# --- API Endpoints ---


@app.get("/health")
def health() -> dict[str, str]:
    """ヘルスチェック."""
    return {"status": "ok", "message": "MSBS-Next API is running"}


@app.post("/api/battle/simulate", response_model=BattleResponse)
async def simulate_battle(
    mission_id: int = 1,
    session: Session = Depends(get_session),
    user_id: str | None = Depends(get_current_user_optional),
) -> BattleResponse:
    """DBから機体データを取得してシミュレーションを実行する."""
    # 1. ミッション情報を取得
    mission = session.get(Mission, mission_id)
    if not mission:
        raise HTTPException(
            status_code=404,
            detail=f"Mission {mission_id} not found.",
        )

    # 2. プレイヤー機体を取得（最初の1機）
    player_statement = select(MobileSuit).limit(1)
    player_results = session.exec(player_statement).all()

    if len(player_results) < 1:
        raise HTTPException(
            status_code=400,
            detail="Not enough Mobile Suits in DB. Please run seed script or add data.",
        )

    # 3. プレイヤー機体を準備
    player = MobileSuit.model_validate(player_results[0].model_dump())
    player.current_hp = player.max_hp
    player.position = Vector3(x=0, y=0, z=0)
    player.side = "PLAYER"

    # 3.5. パイロットスキルを取得（ユーザーがログインしている場合）
    player_skills: dict[str, int] = {}
    if user_id:
        from app.models.models import Pilot

        pilot_statement = select(Pilot).where(Pilot.user_id == user_id)
        pilot = session.exec(pilot_statement).first()
        if pilot:
            player_skills = pilot.skills

    # 4. ミッション設定から敵機を生成
    enemies = []
    enemy_configs = mission.enemy_config.get("enemies", [])

    for enemy_config in enemy_configs:
        pos_dict = enemy_config.get("position", {"x": 500, "y": 0, "z": 0})
        weapon_dict = enemy_config.get("weapon", {})
        terrain_adapt = enemy_config.get("terrain_adaptability", {"SPACE": "A", "GROUND": "A", "COLONY": "A", "UNDERWATER": "C"})

        enemy = MobileSuit(
            name=enemy_config.get("name", "ザクII"),
            max_hp=enemy_config.get("max_hp", 80),
            current_hp=enemy_config.get("max_hp", 80),
            armor=enemy_config.get("armor", 5),
            mobility=enemy_config.get("mobility", 1.2),
            position=Vector3(**pos_dict),
            terrain_adaptability=terrain_adapt,
            weapons=[
                Weapon(
                    id=weapon_dict.get("id", "weapon"),
                    name=weapon_dict.get("name", "Weapon"),
                    power=weapon_dict.get("power", 15),
                    range=weapon_dict.get("range", 400),
                    accuracy=weapon_dict.get("accuracy", 70),
                )
            ],
            side="ENEMY",
        )
        enemies.append(enemy)

    # 5. シミュレーション実行（スキルと環境を渡す）
    sim = BattleSimulator(player, enemies, player_skills=player_skills, environment=mission.environment)
    max_turns = 50
    while not sim.is_finished and sim.turn < max_turns:
        sim.process_turn()

    # 6. 勝者判定と撃墜数カウント
    winner_id = None
    win_loss = "DRAW"
    kills = sum(1 for e in enemies if e.current_hp <= 0)

    if player.current_hp > 0 and all(e.current_hp <= 0 for e in enemies):
        # プレイヤー勝利
        winner_id = str(player.id)
        win_loss = "WIN"
    elif player.current_hp <= 0 and any(e.current_hp > 0 for e in enemies):
        # 敵勝利（少なくとも1体の敵が生き残っている）
        winner_id = "ENEMY"
        win_loss = "LOSE"

    # 7. バトル結果をDBに保存
    battle_result = BattleResult(
        user_id=user_id,
        mission_id=mission_id,
        win_loss=win_loss,
        logs=sim.logs,
        created_at=datetime.now(UTC),
    )
    session.add(battle_result)
    session.commit()

    # 8. 報酬の計算と付与（ユーザーがログインしている場合）
    rewards = None
    if user_id:
        from app.services.pilot_service import PilotService

        pilot_service = PilotService(session)

        # パイロット情報を取得または作成
        pilot = pilot_service.get_or_create_pilot(user_id, player.name)
        level_before = pilot.level

        # 報酬を計算
        exp_gained, credits_gained = pilot_service.calculate_battle_rewards(
            win=win_loss == "WIN",
            kills=kills,
        )

        # 報酬を付与
        pilot, reward_logs = pilot_service.add_rewards(
            pilot, exp_gained, credits_gained
        )

        rewards = BattleRewards(
            exp_gained=exp_gained,
            credits_gained=credits_gained,
            level_before=level_before,
            level_after=pilot.level,
            total_exp=pilot.exp,
            total_credits=pilot.credits,
        )

    return BattleResponse(
        winner_id=winner_id,
        logs=sim.logs,
        player_info=player,
        enemies_info=enemies,
        rewards=rewards,
    )


@app.get("/api/missions", response_model=list[Mission])
async def get_missions(
    session: Session = Depends(get_session),
) -> list[Mission]:
    """ミッション一覧を取得する."""
    statement = select(Mission)
    missions = session.exec(statement).all()
    return list(missions)


@app.get("/api/battles", response_model=list[BattleResult])
async def get_battle_history(
    session: Session = Depends(get_session),
    user_id: str | None = Depends(get_current_user_optional),
    limit: int = 50,
) -> list[BattleResult]:
    """バトル履歴を取得する（最新順）."""
    statement = (
        select(BattleResult).order_by(desc(BattleResult.created_at)).limit(limit)
    )

    # ユーザーIDでフィルタ（認証されている場合）
    if user_id:
        statement = statement.where(BattleResult.user_id == user_id)

    battles = session.exec(statement).all()
    return list(battles)


@app.get("/api/battles/{battle_id}", response_model=BattleResult)
async def get_battle_detail(
    battle_id: str,
    session: Session = Depends(get_session),
) -> BattleResult:
    """特定のバトル結果の詳細を取得する."""
    import uuid

    try:
        battle_uuid = uuid.UUID(battle_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid battle ID format") from e

    battle = session.get(BattleResult, battle_uuid)
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")

    return battle
