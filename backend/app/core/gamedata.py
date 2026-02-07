"""ゲームデータ定義（ショップマスターデータなど）."""

from app.models.models import Weapon

# ショップで販売する機体のテンプレート定義
SHOP_LISTINGS = [
    {
        "id": "zaku_ii",
        "name": "Zaku II",
        "price": 500,
        "description": "量産型モビルスーツ。バランスの取れた性能で扱いやすい。",
        "specs": {
            "max_hp": 800,
            "armor": 50,
            "mobility": 1.0,
            "sensor_range": 500.0,
            "beam_resistance": 0.05,
            "physical_resistance": 0.2,
            "weapons": [
                Weapon(
                    id="zaku_mg",
                    name="Zaku Machine Gun",
                    power=100,
                    range=400,
                    accuracy=60,
                    type="PHYSICAL",
                    optimal_range=300.0,
                    decay_rate=0.08,
                )
            ],
        },
    },
    {
        "id": "dom",
        "name": "Dom",
        "price": 1200,
        "description": "重装甲型モビルスーツ。高い装甲と火力を持つが機動性は低い。",
        "specs": {
            "max_hp": 1000,
            "armor": 80,
            "mobility": 0.8,
            "sensor_range": 500.0,
            "beam_resistance": 0.1,
            "physical_resistance": 0.25,
            "weapons": [
                Weapon(
                    id="giant_bazooka",
                    name="Giant Bazooka",
                    power=180,
                    range=450,
                    accuracy=55,
                    type="PHYSICAL",
                    optimal_range=350.0,
                    decay_rate=0.1,
                )
            ],
        },
    },
    {
        "id": "gouf",
        "name": "Gouf",
        "price": 1000,
        "description": "白兵戦特化型モビルスーツ。高い機動性と近接戦闘能力を持つ。",
        "specs": {
            "max_hp": 850,
            "armor": 60,
            "mobility": 1.3,
            "sensor_range": 500.0,
            "beam_resistance": 0.08,
            "physical_resistance": 0.15,
            "weapons": [
                Weapon(
                    id="heat_rod",
                    name="Heat Rod",
                    power=140,
                    range=300,
                    accuracy=70,
                    type="PHYSICAL",
                    optimal_range=200.0,
                    decay_rate=0.12,
                )
            ],
        },
    },
    {
        "id": "gundam",
        "name": "Gundam",
        "price": 5000,
        "description": "連邦軍の最新鋭モビルスーツ。全ての性能が高水準。",
        "specs": {
            "max_hp": 1200,
            "armor": 100,
            "mobility": 1.5,
            "sensor_range": 600.0,
            "beam_resistance": 0.2,
            "physical_resistance": 0.1,
            "weapons": [
                Weapon(
                    id="beam_rifle",
                    name="Beam Rifle",
                    power=300,
                    range=600,
                    accuracy=80,
                    type="BEAM",
                    optimal_range=400.0,
                    decay_rate=0.05,
                )
            ],
        },
    },
    {
        "id": "gelgoog",
        "name": "Gelgoog",
        "price": 2500,
        "description": "ジオン軍の高性能機。ガンダムに匹敵する性能を持つ。",
        "specs": {
            "max_hp": 1100,
            "armor": 85,
            "mobility": 1.4,
            "sensor_range": 550.0,
            "beam_resistance": 0.15,
            "physical_resistance": 0.12,
            "weapons": [
                Weapon(
                    id="beam_rifle_gelgoog",
                    name="Beam Rifle",
                    power=280,
                    range=580,
                    accuracy=75,
                    type="BEAM",
                    optimal_range=400.0,
                    decay_rate=0.06,
                )
            ],
        },
    },
]


def get_shop_listing_by_id(item_id: str) -> dict | None:
    """IDから商品データを取得する.

    Args:
        item_id: 商品ID

    Returns:
        dict | None: 商品データ。見つからない場合はNone
    """
    for listing in SHOP_LISTINGS:
        if listing["id"] == item_id:
            return listing
    return None
