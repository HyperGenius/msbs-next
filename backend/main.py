import json
import os
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import Depends, FastAPI, HTTPException

if TYPE_CHECKING:
    from app.engine.calculator import PilotStats
from collections.abc import AsyncIterator

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, desc, select

# DB関連
from app.core.auth import get_current_user, get_current_user_optional
from app.db import get_session
from app.engine.battle_digest import compute_unit_kills
from app.engine.battle_utils import serialize_obstacles, strip_debug_fields
from app.engine.simulation import BattleSimulator
from app.models.models import (
    BattleField,
    BattleLog,
    BattleLogRecord,
    BattleResult,
    BattleResultSummary,
    Mission,
    MobileSuit,
    Vector3,
    Weapon,
)
from app.routers import (
    admin,
    engineering,
    entries,
    friends,
    mobile_suits,
    pilots,
    player_weapons,
    rankings,
    shop,
    teams,
)
from app.services.battle_digest_service import compute_battle_digest_fields

app = FastAPI(title="MSBS-Next API", redirect_slashes=False)

# --- CORS設定 ---
# ローカル環境と本番環境のオリジンを設定
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    # admin-tool（ゲームバランス調整用ローカルツール）
    "http://localhost:3100",
    "http://127.0.0.1:3100",
]

# 本番環境のVercelドメインを追加
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    # カンマ区切りで複数のオリジンを追加可能
    origins.extend(
        [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Routerの登録
app.include_router(mobile_suits.router)
app.include_router(entries.router)
app.include_router(pilots.router)
app.include_router(shop.router)
app.include_router(engineering.router)
app.include_router(rankings.router)
app.include_router(friends.router)
app.include_router(teams.router)
app.include_router(admin.router)
app.include_router(admin.weapon_router)
app.include_router(admin.simulation_router)
app.include_router(admin.npc_router)
app.include_router(player_weapons.router)

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
    obstacles_info: list[dict] | None = None
    rewards: BattleRewards | None = None
    map_bounds: tuple[float, float] | None = None


# --- API Endpoints ---


def _resolve_npc_pilot_stats(enemies: list[MobileSuit]) -> "dict[str, PilotStats]":
    """エース NPC のパイロットステータスを npc_data マスターから解決する (Phase E-2).

    is_ace=True かつ ace_id が設定されているユニットのみを対象とし、
    npc_data.ACE_PILOTS の "stats" キーからステータスを取得する。
    "stats" キーがない場合は simulation.py 側で personality から自動解決される。
    """
    from app.core.npc_data import get_ace_pilot_by_id
    from app.engine.calculator import PilotStats

    result: dict[str, PilotStats] = {}
    for enemy in enemies:
        ace_id = enemy.ace_id
        if not (getattr(enemy, "is_ace", False) and ace_id):
            continue
        ace_data = get_ace_pilot_by_id(ace_id)
        if ace_data and "stats" in ace_data:
            s = ace_data["stats"]
            result[str(enemy.id)] = PilotStats(
                sht=s.get("sht", 8),
                mel=s.get("mel", 8),
                intel=s.get("intel", 8),
                ref=s.get("ref", 8),
                tou=s.get("tou", 8),
                luk=s.get("luk", 8),
            )
    return result


def _build_enemies_from_config(enemy_configs: list[dict]) -> list[MobileSuit]:
    """ミッション設定から敵ユニットリストを生成する."""
    enemies = []
    for enemy_config in enemy_configs:
        pos_dict = enemy_config.get("position", {"x": 500, "y": 0, "z": 0})
        weapon_dict = enemy_config.get("weapon", {})
        terrain_adapt = enemy_config.get(
            "terrain_adaptability",
            {"SPACE": "A", "GROUND": "A", "COLONY": "A", "UNDERWATER": "C"},
        )
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
    return enemies


def _snapshot_spawn_positions(
    player: MobileSuit, enemies: list[MobileSuit]
) -> tuple[Vector3, dict[uuid.UUID, Vector3]]:
    """スポーン領域適用直後（戦闘開始前）の位置を退避する.

    `sim.step()` はplayer/enemiesオブジェクトを直接書き換えるため、戦闘ループ後には
    バトル終了時点の最終位置になってしまう。BattleViewerのt=0初期表示にはスポーン位置が
    必要なため、レスポンス構築前に元へ戻せるようここで退避しておく。
    """
    return (
        player.position.model_copy(),
        {enemy.id: enemy.position.model_copy() for enemy in enemies},
    )


def _restore_spawn_positions(
    player: MobileSuit,
    enemies: list[MobileSuit],
    spawn_positions: tuple[Vector3, dict[uuid.UUID, Vector3]],
) -> None:
    """player_info/enemies_info/ms_snapshotに反映する位置をスポーン位置へ戻す."""
    player_spawn_position, enemy_spawn_positions = spawn_positions
    player.position = player_spawn_position
    for enemy in enemies:
        enemy.position = enemy_spawn_positions[enemy.id]


@app.get("/health")
def health() -> dict[str, str]:
    """ヘルスチェック."""
    return {"status": "ok", "message": "MSBS-Next API is running"}


@app.post("/api/admin/reload-master")
async def reload_master() -> dict:
    """マスターデータをリロードする（管理者用）."""
    from app.core.gamedata import reload_master_data

    result = reload_master_data()
    return {"status": "ok", "reloaded": result}


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
    player_pilot_stats = None
    if user_id:
        from app.engine.calculator import PilotStats
        from app.models.models import Pilot

        pilot_statement = select(Pilot).where(Pilot.user_id == user_id)
        pilot = session.exec(pilot_statement).first()
        if pilot:
            player_skills = pilot.skills
            player_pilot_stats = PilotStats(
                sht=pilot.sht,
                mel=pilot.mel,
                intel=pilot.intel,
                ref=pilot.ref,
                tou=pilot.tou,
                luk=pilot.luk,
            )

    # 4. ミッション設定から敵機を生成
    enemy_configs = mission.enemy_config.get("enemies", [])
    enemies = _build_enemies_from_config(enemy_configs)

    # 4.5. エース NPC のパイロットステータスを npc_data マスターから解決 (Phase E-2)
    npc_pilot_stats = _resolve_npc_pilot_stats(enemies)

    # 5. シミュレーション実行（スキルと環境を渡す）
    sim = BattleSimulator(
        player,
        enemies,
        player_skills=player_skills,
        environment=mission.environment,
        player_pilot_stats=player_pilot_stats,
        npc_pilot_stats=npc_pilot_stats,
        battlefield=BattleField(),
    )
    spawn_positions = _snapshot_spawn_positions(player, enemies)

    max_steps = 50
    steps_used = 0
    for _ in range(max_steps):
        if sim.is_finished:
            break
        sim.step()
        steps_used += 1

    # 6. 勝者判定と撃墜数カウント
    winner_id = None
    win_loss = "DRAW"
    kills = compute_unit_kills(sim.logs, player.id)

    if player.current_hp > 0 and all(e.current_hp <= 0 for e in enemies):
        # プレイヤー勝利
        winner_id = str(player.id)
        win_loss = "WIN"
    elif player.current_hp <= 0 and any(e.current_hp > 0 for e in enemies):
        # 敵勝利（少なくとも1体の敵が生き残っている）
        winner_id = "ENEMY"
        win_loss = "LOSE"

    # 7. 報酬の計算と付与（ユーザーがログインしている場合）
    rewards = None
    exp_gained = 0
    credits_gained = 0
    level_up = False
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

        level_up = pilot.level > level_before

        rewards = BattleRewards(
            exp_gained=exp_gained,
            credits_gained=credits_gained,
            level_before=level_before,
            level_after=pilot.level,
            total_exp=pilot.exp,
            total_credits=pilot.credits,
        )

    # 8. バトルログをDBに保存（battle_logsテーブル）
    battle_log_record = BattleLogRecord(
        mission_id=mission_id,
        logs=strip_debug_fields(sim.logs),
        created_at=datetime.now(UTC),
    )
    session.add(battle_log_record)
    session.flush()

    # 9. 戦闘ダイジェスト（一言ログ）を生成する（Issue #415）
    #    BattleResultのもう一つの生成箇所 scripts/run_batch.py と共通のヘルパーを使う
    #    （個別実装すると片方だけ更新漏れになる事故が起きるため）
    digest_fields = compute_battle_digest_fields(
        session=session,
        user_id=user_id,
        player=player,
        logs=sim.logs,
        kills=kills,
        win_loss=win_loss,
        steps_used=steps_used,
        max_steps=max_steps,
    )

    # player_info/enemies_info/ms_snapshot にはバトル後の最終位置ではなくスポーン位置を
    # 反映する（BattleViewerが再生開始前=t=0時点でこの位置を初期表示に使うため。
    # 最終位置のままだとフィールド外にMSが表示されるバグになる）。勝敗判定・報酬計算・
    # ダイジェスト集計（compute_battle_digest_fields）はバトル後の最終状態を前提とする
    # ため、これらの集計処理より後、レスポンス構築の直前でのみ位置を戻す。
    _restore_spawn_positions(player, enemies, spawn_positions)

    # 10. バトル結果をDBに保存（リプレイ用スナップショット・詳細情報含む）
    obstacles_data = serialize_obstacles(sim.obstacles)
    battle_result = BattleResult(
        user_id=user_id,
        mission_id=mission_id,
        battle_log_id=battle_log_record.id,
        win_loss=win_loss,
        environment=mission.environment,
        player_info=player.model_dump(),
        enemies_info=[e.model_dump() for e in enemies],
        obstacles_info=obstacles_data,
        ms_snapshot=player.model_dump(),
        map_bounds=list(sim.map_bounds),
        kills=kills,
        exp_gained=exp_gained,
        credits_gained=credits_gained,
        level_before=rewards.level_before if rewards else 0,
        level_after=rewards.level_after if rewards else 0,
        level_up=level_up,
        is_read=False,
        created_at=datetime.now(UTC),
        **digest_fields,
    )
    session.add(battle_result)
    session.commit()

    return BattleResponse(
        winner_id=winner_id,
        logs=sim.logs,
        player_info=player,
        enemies_info=enemies,
        obstacles_info=obstacles_data,
        rewards=rewards,
        map_bounds=sim.map_bounds,
    )


@app.get("/api/missions", response_model=list[Mission])
async def get_missions(
    session: Session = Depends(get_session),
) -> list[Mission]:
    """ミッション一覧を取得する."""
    statement = select(Mission)
    missions = session.exec(statement).all()
    return list(missions)


@app.get("/api/battles", response_model=list[BattleResultSummary])
async def get_battle_history(
    session: Session = Depends(get_session),
    user_id: str | None = Depends(get_current_user_optional),
    limit: int = 50,
) -> list[BattleResult]:
    """バトル履歴を取得する（最新順、logsを除く軽量レスポンス）."""
    statement = (
        select(BattleResult).order_by(desc(BattleResult.created_at)).limit(limit)
    )

    # ユーザーIDでフィルタ（認証されている場合）
    if user_id:
        statement = statement.where(BattleResult.user_id == user_id)

    battles = session.exec(statement).all()
    return list(battles)


@app.get("/api/battles/unread", response_model=list[BattleResultSummary])
async def get_unread_battles(
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> list[BattleResult]:
    """ログインユーザーの未読バトル結果を取得する（最新順）."""
    statement = (
        select(BattleResult)
        .where(BattleResult.user_id == user_id)
        .where(BattleResult.is_read == False)  # noqa: E712
        .order_by(desc(BattleResult.created_at))
    )
    battles = session.exec(statement).all()
    return list(battles)


@app.post("/api/battles/{battle_id}/read")
async def mark_battle_as_read(
    battle_id: str,
    session: Session = Depends(get_session),
    user_id: str = Depends(get_current_user),
) -> dict[str, str]:
    """バトル結果を既読にする."""
    try:
        battle_uuid = uuid.UUID(battle_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid battle ID format") from e

    battle = session.get(BattleResult, battle_uuid)
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")

    if battle.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    battle.is_read = True
    session.add(battle)
    session.commit()

    return {"message": "Battle marked as read"}


@app.get("/api/battles/{battle_id}", response_model=BattleResultSummary)
async def get_battle_detail(
    battle_id: str,
    session: Session = Depends(get_session),
) -> BattleResult:
    """特定のバトル結果の詳細を取得する."""
    try:
        battle_uuid = uuid.UUID(battle_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid battle ID format") from e

    battle = session.get(BattleResult, battle_uuid)
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")

    return battle


async def _ndjson_lines(entries: list[dict]) -> AsyncIterator[bytes]:
    """バトルログdictの列をNDJSON（1行1エントリ）のバイト列として逐次生成する.

    `JSONResponse(entries)` は送出前にリスト全体を1個の巨大なJSON文字列へ
    シリアライズしてからまとめて返すため、その文字列自体がプロセスメモリに
    乗る（Issue #488）。1件ずつシリアライズしてyieldすることで、ASGIサーバーが
    チャンクを送出し終えた分から解放でき、ピークメモリをレスポンス全体のサイズに
    比例させずに済む。
    """
    for entry in entries:
        yield (json.dumps(entry, ensure_ascii=False) + "\n").encode("utf-8")


@app.get(
    "/api/battles/{battle_id}/logs",
    response_class=StreamingResponse,
    responses={
        200: {
            "content": {"application/x-ndjson": {}},
            "description": (
                "NDJSON形式のバトルログ（1行1エントリ、各行はBattleLog相当のJSON）"
            ),
        }
    },
)
async def get_battle_logs(
    battle_id: str,
    session: Session = Depends(get_session),
) -> StreamingResponse:
    """バトルリプレイ用ログを取得する（遅延ロード）.

    大規模バトル（room_size=50/100等）ではログが数万〜十数万件に及ぶ。
    DBのdictをBattleLogオブジェクト化→response_modelで再バリデーション、という
    経路はオブジェクト生成のオーバーヘッドでOOMする（Issue #486、対応済み）。
    さらにレスポンス全体を1個のJSON文字列として組み立てる経路も、その文字列自体が
    レスポンスサイズに比例したメモリを消費するため、NDJSON（`application/x-ndjson`,
    1行1エントリのJSON）でチャンク単位に逐次送出する（Issue #488）。

    保存時点で既にBattleLog相当のJSON互換dictとして検証済みのため、ここでは
    オブジェクト化を挟まずそのままNDJSON化して返す。

    注意: 実体は `application/x-ndjson`（改行区切りJSON）であり、単一のJSON配列
    ではない。`response_model=list[BattleLog]` を付けるとOpenAPI上
    `application/json` の配列レスポンスとして表示されクライアント実装を誤誘導する
    ため、代わりに `responses` で実際のcontent-typeを明示している。レスポンスの
    型・形式を変更する場合は `responses` の記述も合わせて更新すること。
    """
    try:
        battle_uuid = uuid.UUID(battle_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid battle ID format") from e

    battle = session.get(BattleResult, battle_uuid)
    if not battle:
        raise HTTPException(status_code=404, detail="Battle not found")

    if battle.battle_log_id is None:
        return StreamingResponse(_ndjson_lines([]), media_type="application/x-ndjson")

    log_record = session.get(BattleLogRecord, battle.battle_log_id)
    if not log_record:
        return StreamingResponse(_ndjson_lines([]), media_type="application/x-ndjson")

    return StreamingResponse(
        _ndjson_lines(log_record.logs), media_type="application/x-ndjson"
    )
