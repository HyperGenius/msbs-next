"""ゲームデータ定義（ショップマスターデータなど）.

JSONファイルからマスターデータを読み込み、インメモリキャッシュとして保持する。
管理者用リロードAPIにより、サーバー再起動なしでデータを更新可能。
"""

import json
import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from app.models.models import Weapon

# マスターデータディレクトリのパス
_DATA_DIR = Path(
    os.environ.get(
        "MASTER_DATA_DIR",
        str(Path(__file__).resolve().parent.parent.parent / "data" / "master"),
    )
)

# インメモリキャッシュ
_shop_listings_cache: list[dict] | None = None
_weapon_shop_listings_cache: list[dict] | None = None


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
                    id="trainer_rifle",
                    name="Trainer Rifle",
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
                    id="trainer_rifle",
                    name="Trainer Rifle",
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
}


def get_starter_kit_by_faction(faction: str) -> dict[str, Any] | None:
    """勢力に対応した練習機データを取得する.

    Args:
        faction: 勢力コード (FEDERATION/ZEON)

    Returns:
        dict | None: 練習機データ。見つからない場合はNone
    """
    return STARTER_KITS.get(faction)


def _load_mobile_suits_json() -> list[dict]:
    """JSONファイルから機体マスターデータを読み込む."""
    json_path = _DATA_DIR / "mobile_suits.json"
    with open(json_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    listings = []
    for item in raw_data:
        specs = item["specs"]
        weapons = [Weapon(**w) for w in specs["weapons"]]
        specs_copy = {**specs, "weapons": weapons}
        listings.append(
            {
                "id": item["id"],
                "name": item["name"],
                "price": item["price"],
                "faction": item.get("faction", ""),
                "description": item["description"],
                "specs": specs_copy,
            }
        )
    return listings


def _load_weapons_json() -> list[dict]:
    """JSONファイルから武器マスターデータを読み込む."""
    json_path = _DATA_DIR / "weapons.json"
    with open(json_path, encoding="utf-8") as f:
        raw_data = json.load(f)

    listings = []
    for item in raw_data:
        weapon = Weapon(**item["weapon"])
        listings.append(
            {
                "id": item["id"],
                "name": item["name"],
                "price": item["price"],
                "description": item["description"],
                "weapon": weapon,
            }
        )
    return listings


def _get_shop_listings() -> list[dict]:
    """キャッシュ済みのショップリストを取得（未ロード時は自動ロード）."""
    global _shop_listings_cache
    if _shop_listings_cache is None:
        _shop_listings_cache = _load_mobile_suits_json()
    return _shop_listings_cache


def _get_weapon_shop_listings() -> list[dict]:
    """キャッシュ済みの武器ショップリストを取得（未ロード時は自動ロード）."""
    global _weapon_shop_listings_cache
    if _weapon_shop_listings_cache is None:
        _weapon_shop_listings_cache = _load_weapons_json()
    return _weapon_shop_listings_cache


def reload_master_data() -> dict[str, int]:
    """マスターデータのキャッシュをリロードする.

    Returns:
        dict[str, int]: リロードされたデータの件数
    """
    global _shop_listings_cache, _weapon_shop_listings_cache
    _shop_listings_cache = _load_mobile_suits_json()
    _weapon_shop_listings_cache = _load_weapons_json()
    return {
        "mobile_suits": len(_shop_listings_cache),
        "weapons": len(_weapon_shop_listings_cache),
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
