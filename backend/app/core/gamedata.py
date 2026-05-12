"""ゲームデータ定義（ショップマスターデータなど）.

DBからマスターデータを読み込み、TTLキャッシュとして保持する。
管理者用リロードAPIにより、キャッシュを強制クリアして最新DBデータを返す。
"""

import json
import os
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from app.models.models import MasterMobileSuit, MasterWeapon, Weapon

# マスターデータディレクトリのパス (backgrounds.json / STARTER_KITS 用)
_DATA_DIR = Path(
    os.environ.get(
        "MASTER_DATA_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "data" / "master"),
    )
)

# キャッシュ TTL 設定（秒）。0 を設定するとキャッシュ無効化（常にDB参照）
_CACHE_TTL_SEC: int = int(os.environ.get("MASTER_DATA_CACHE_TTL_SEC", "60"))

# インメモリキャッシュ
_shop_listings_cache: list[dict] | None = None
_weapon_shop_listings_cache: list[dict] | None = None
_backgrounds_cache: dict[str, dict[str, Any]] | None = None
_cache_expires_at: datetime | None = None


# 練習機マスターデータ（ショップには並ばない専用機体）
# 連邦・ジオン双方で全ステータスが同一
STARTER_KITS: dict[str, dict[str, Any]] = {
    "FEDERATION": {
        "id": "gm_trainer",
        "name": "RGM-79T GM Trainer",
        "description": "地球連邦軍の練習用モビルスーツ。全勢力共通の標準スペック。",
        "specs": {
            "max_hp": 700,
            "armor": 40,
            "mobility": 1.0,
            "sensor_range": 500.0,
            "beam_resistance": 0.0,
            "physical_resistance": 0.0,
            "melee_aptitude": 1.0,
            "shooting_aptitude": 1.0,
            "accuracy_bonus": 0.0,
            "evasion_bonus": 0.0,
            "acceleration_bonus": 1.0,
            "turning_bonus": 1.0,
            "weapons": [
                Weapon(
                    id="trainer_spray_gun",
                    name="Beam Spray Gun(Trainer)",
                    power=80,
                    range=400,
                    accuracy=60,
                    type="BEAM",
                    optimal_range=300.0,
                    decay_rate=0.08,
                    is_melee=False,
                )
            ],
        },
    },
    "ZEON": {
        "id": "zaku_ii_trainer",
        "name": "MS-06T Zaku II Trainer",
        "description": "ジオン公国軍の練習用モビルスーツ。全勢力共通の標準スペック。",
        "specs": {
            "max_hp": 700,
            "armor": 40,
            "mobility": 1.0,
            "sensor_range": 500.0,
            "beam_resistance": 0.0,
            "physical_resistance": 0.0,
            "melee_aptitude": 1.0,
            "shooting_aptitude": 1.0,
            "accuracy_bonus": 0.0,
            "evasion_bonus": 0.0,
            "acceleration_bonus": 1.0,
            "turning_bonus": 1.0,
            "weapons": [
                Weapon(
                    id="trainer_machine_gun",
                    name="Zaku Machine Gun(Trainer)",
                    power=80,
                    range=400,
                    accuracy=60,
                    type="PHYSICAL",
                    optimal_range=300.0,
                    decay_rate=0.08,
                    is_melee=False,
                )
            ],
        },
    },
}


# パイロット経歴マスターデータ
def _load_backgrounds_json() -> dict[str, dict[str, Any]]:
    """JSONファイルから経歴マスターデータを読み込む."""
    json_path = _DATA_DIR / "backgrounds.json"
    with open(json_path, encoding="utf-8") as f:
        raw_data: list[dict[str, Any]] = json.load(f)
    return {item["id"]: item for item in raw_data}


def _get_backgrounds() -> dict[str, dict[str, Any]]:
    """キャッシュ済みの経歴データを取得（未ロード時は自動ロード）."""
    global _backgrounds_cache
    if _backgrounds_cache is None:
        _backgrounds_cache = _load_backgrounds_json()
    return _backgrounds_cache


def get_background_by_id(background_id: str) -> dict[str, Any] | None:
    """経歴IDに対応した経歴データを取得する.

    Args:
        background_id: 経歴ID (ACADEMY_ELITE/STREET_SURVIVOR/EX_MECHANIC)

    Returns:
        dict | None: 経歴データ。見つからない場合はNone
    """
    return _get_backgrounds().get(background_id)


def get_starter_kit_by_faction(faction: str) -> dict[str, Any] | None:
    """勢力に対応した練習機データを取得する.

    Args:
        faction: 勢力コード (FEDERATION/ZEON)

    Returns:
        dict | None: 練習機データ。見つからない場合はNone
    """
    return STARTER_KITS.get(faction)


# --- TTL キャッシュ補助関数 ---


def _is_cache_expired() -> bool:
    """キャッシュが期限切れかどうかを返す."""
    if _CACHE_TTL_SEC == 0:
        return True
    if _cache_expires_at is None:
        return True
    return datetime.now(UTC) >= _cache_expires_at


def _refresh_cache_expiry() -> None:
    """キャッシュの有効期限を更新する."""
    global _cache_expires_at
    if _CACHE_TTL_SEC > 0:
        _cache_expires_at = datetime.now(UTC) + timedelta(seconds=_CACHE_TTL_SEC)
    else:
        _cache_expires_at = None


# --- DB ロード関数 ---


def _load_mobile_suits_from_db() -> list[dict]:
    """DBから機体マスターデータを読み込む."""
    from app import db as _app_db

    with Session(_app_db.engine) as db_session:
        records = db_session.exec(select(MasterMobileSuit)).all()

    listings = []
    for record in records:
        specs_raw = record.specs
        weapons = [Weapon(**w) for w in specs_raw.get("weapons", [])]
        specs_copy = {**specs_raw, "weapons": weapons}
        listings.append(
            {
                "id": record.id,
                "name": record.name,
                "price": record.price,
                "faction": record.faction,
                "description": record.description,
                "specs": specs_copy,
            }
        )
    return listings


def _load_weapons_from_db() -> list[dict]:
    """DBから武器マスターデータを読み込む."""
    from app import db as _app_db

    with Session(_app_db.engine) as db_session:
        records = db_session.exec(select(MasterWeapon)).all()

    listings = []
    for record in records:
        weapon = Weapon(**record.weapon)
        listings.append(
            {
                "id": record.id,
                "name": record.name,
                "price": record.price,
                "description": record.description,
                "weapon": weapon,
            }
        )
    return listings


def _get_shop_listings() -> list[dict]:
    """キャッシュ済みの機体ショップリストを取得（TTL 期限切れ時はDB再取得）."""
    global _shop_listings_cache
    if _shop_listings_cache is None or _is_cache_expired():
        _shop_listings_cache = _load_mobile_suits_from_db()
        _refresh_cache_expiry()
    return _shop_listings_cache


def _get_weapon_shop_listings() -> list[dict]:
    """キャッシュ済みの武器ショップリストを取得（TTL 期限切れ時はDB再取得）."""
    global _weapon_shop_listings_cache
    if _weapon_shop_listings_cache is None or _is_cache_expired():
        _weapon_shop_listings_cache = _load_weapons_from_db()
        _refresh_cache_expiry()
    return _weapon_shop_listings_cache


def get_master_mobile_suits(session: Session) -> list[dict]:
    """マスター機体データを生データ（辞書リスト）で返す.

    DBから全件取得する。weaponsフィールドはdictのまま（JSON出力に向く）。

    Args:
        session: DBセッション

    Returns:
        list[dict]: マスター機体データの生辞書リスト
    """
    records = session.exec(select(MasterMobileSuit)).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "price": r.price,
            "faction": r.faction,
            "description": r.description,
            "specs": r.specs,
        }
        for r in records
    ]


def save_master_mobile_suits(session: Session, data: list[dict]) -> None:
    """マスター機体データをDBへ一括保存し、インメモリキャッシュを無効化する.

    既存レコードは更新し、提供されたリストに存在しないレコードは削除する。

    Args:
        session: DBセッション
        data: 保存するマスター機体データの辞書リスト
    """
    global _shop_listings_cache, _cache_expires_at

    existing = {r.id: r for r in session.exec(select(MasterMobileSuit)).all()}
    incoming_ids: set[str] = set()

    for item in data:
        item_id = item["id"]
        incoming_ids.add(item_id)

        specs = item.get("specs", {})
        # Weapon オブジェクトを辞書に変換
        if isinstance(specs, dict) and "weapons" in specs:
            specs = {
                **specs,
                "weapons": [
                    w.model_dump() if hasattr(w, "model_dump") else w
                    for w in specs["weapons"]
                ],
            }

        if item_id in existing:
            record = existing[item_id]
            record.name = item["name"]
            record.price = item["price"]
            record.faction = item.get("faction", "")
            record.description = item["description"]
            record.specs = specs
            record.updated_at = datetime.now(UTC)
            session.add(record)
        else:
            record = MasterMobileSuit(
                id=item_id,
                name=item["name"],
                price=item["price"],
                faction=item.get("faction", ""),
                description=item["description"],
                specs=specs,
            )
            session.add(record)

    # 提供されたリストに存在しないレコードを削除
    for existing_id, record in existing.items():
        if existing_id not in incoming_ids:
            session.delete(record)

    session.commit()

    # キャッシュを無効化
    _shop_listings_cache = None
    _cache_expires_at = None


def get_master_weapons(session: Session) -> list[dict]:
    """マスター武器データを生データ（辞書リスト）で返す.

    DBから全件取得する。weaponフィールドはdictのまま（JSON出力に向く）。

    Args:
        session: DBセッション

    Returns:
        list[dict]: マスター武器データの生辞書リスト
    """
    records = session.exec(select(MasterWeapon)).all()
    return [
        {
            "id": r.id,
            "name": r.name,
            "price": r.price,
            "description": r.description,
            "weapon": r.weapon,
        }
        for r in records
    ]


def save_master_weapons(session: Session, data: list[dict]) -> None:
    """マスター武器データをDBへ一括保存し、インメモリキャッシュを無効化する.

    既存レコードは更新し、提供されたリストに存在しないレコードは削除する。

    Args:
        session: DBセッション
        data: 保存するマスター武器データの辞書リスト
    """
    global _weapon_shop_listings_cache, _cache_expires_at

    existing = {r.id: r for r in session.exec(select(MasterWeapon)).all()}
    incoming_ids: set[str] = set()

    for item in data:
        item_id = item["id"]
        incoming_ids.add(item_id)

        weapon_data = item.get("weapon", {})
        if hasattr(weapon_data, "model_dump"):
            weapon_data = weapon_data.model_dump()

        if item_id in existing:
            record = existing[item_id]
            record.name = item["name"]
            record.price = item["price"]
            record.description = item["description"]
            record.weapon = weapon_data
            record.updated_at = datetime.now(UTC)
            session.add(record)
        else:
            record = MasterWeapon(
                id=item_id,
                name=item["name"],
                price=item["price"],
                description=item["description"],
                weapon=weapon_data,
            )
            session.add(record)

    # 提供されたリストに存在しないレコードを削除
    for existing_id, record in existing.items():
        if existing_id not in incoming_ids:
            session.delete(record)

    session.commit()

    # キャッシュを無効化
    _weapon_shop_listings_cache = None
    _cache_expires_at = None


def reload_master_data() -> dict[str, int]:
    """マスターデータのTTLキャッシュをクリアし、最新DB件数を返す.

    Returns:
        dict[str, int]: 各マスターデータの件数
    """
    global \
        _shop_listings_cache, \
        _weapon_shop_listings_cache, \
        _backgrounds_cache, \
        _cache_expires_at
    _shop_listings_cache = None
    _weapon_shop_listings_cache = None
    _backgrounds_cache = None
    _cache_expires_at = None

    from app import db as _app_db

    with Session(_app_db.engine) as db_session:
        ms_count = len(db_session.exec(select(MasterMobileSuit)).all())
        w_count = len(db_session.exec(select(MasterWeapon)).all())

    bg_count = len(_get_backgrounds())

    return {
        "mobile_suits": ms_count,
        "weapons": w_count,
        "backgrounds": bg_count,
    }


# 後方互換: モジュールレベルの変数としてアクセス可能なプロパティ
# 既存コードで SHOP_LISTINGS / WEAPON_SHOP_LISTINGS を直接参照している箇所に対応
class _LazyListProxy:
    """遅延読み込みリストプロキシ."""

    def __init__(self, getter: Callable[[], list[dict[str, Any]]]) -> None:
        self._getter = getter

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self._getter())

    def __len__(self) -> int:
        return len(self._getter())

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self._getter()[index]


SHOP_LISTINGS = _LazyListProxy(_get_shop_listings)
WEAPON_SHOP_LISTINGS = _LazyListProxy(_get_weapon_shop_listings)


def get_shop_listing_by_id(item_id: str) -> dict | None:
    """IDから商品データを取得する.

    Args:
        item_id: 商品ID

    Returns:
        dict | None: 商品データ。見つからない場合はNone
    """
    for listing in _get_shop_listings():
        if listing["id"] == item_id:
            return listing
    return None


def get_weapon_listing_by_id(weapon_id: str) -> dict | None:
    """IDから武器商品データを取得する.

    Args:
        weapon_id: 武器ID

    Returns:
        dict | None: 武器商品データ。見つからない場合はNone
    """
    for listing in _get_weapon_shop_listings():
        if listing["id"] == weapon_id:
            return listing
    return None
