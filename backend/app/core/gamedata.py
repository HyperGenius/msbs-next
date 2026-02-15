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
        "id": "gm",
        "name": "RGM-79 GM",
        "price": 500,
        "description": "連邦軍の量産型モビルスーツ。ビーム兵器を装備したバランス型。",
        "specs": {
            "max_hp": 750,
            "armor": 45,
            "mobility": 1.1,
            "sensor_range": 520.0,
            "beam_resistance": 0.1,
            "physical_resistance": 0.15,
            "weapons": [
                Weapon(
                    id="beam_spray_gun",
                    name="Beam Spray Gun",
                    power=120,
                    range=450,
                    accuracy=65,
                    type="BEAM",
                    optimal_range=320.0,
                    decay_rate=0.09,
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


# 武器ショップで販売する武器のマスターデータ
WEAPON_SHOP_LISTINGS = [
    {
        "id": "zaku_mg",
        "name": "Zaku Machine Gun",
        "price": 200,
        "description": "ザク用マシンガン。連射性能に優れた実弾兵器。",
        "weapon": Weapon(
            id="zaku_mg",
            name="Zaku Machine Gun",
            power=100,
            range=400,
            accuracy=60,
            type="PHYSICAL",
            optimal_range=300.0,
            decay_rate=0.08,
        ),
    },
    {
        "id": "giant_bazooka",
        "name": "Giant Bazooka",
        "price": 400,
        "description": "高火力バズーカ。装甲貫通力に優れる。",
        "weapon": Weapon(
            id="giant_bazooka",
            name="Giant Bazooka",
            power=180,
            range=450,
            accuracy=55,
            type="PHYSICAL",
            optimal_range=350.0,
            decay_rate=0.1,
        ),
    },
    {
        "id": "heat_rod",
        "name": "Heat Rod",
        "price": 350,
        "description": "ヒートロッド。近距離戦闘に特化した武器。",
        "weapon": Weapon(
            id="heat_rod",
            name="Heat Rod",
            power=140,
            range=300,
            accuracy=70,
            type="PHYSICAL",
            optimal_range=200.0,
            decay_rate=0.12,
        ),
    },
    {
        "id": "beam_rifle",
        "name": "Beam Rifle",
        "price": 800,
        "description": "ガンダム用ビームライフル。高威力・高精度のビーム兵器。",
        "weapon": Weapon(
            id="beam_rifle",
            name="Beam Rifle",
            power=300,
            range=600,
            accuracy=80,
            type="BEAM",
            optimal_range=400.0,
            decay_rate=0.05,
        ),
    },
    {
        "id": "beam_rifle_gelgoog",
        "name": "Beam Rifle (Gelgoog)",
        "price": 700,
        "description": "ゲルググ用ビームライフル。バランスの取れたビーム兵器。",
        "weapon": Weapon(
            id="beam_rifle_gelgoog",
            name="Beam Rifle",
            power=280,
            range=580,
            accuracy=75,
            type="BEAM",
            optimal_range=400.0,
            decay_rate=0.06,
        ),
    },
    {
        "id": "hyper_bazooka",
        "name": "Hyper Bazooka",
        "price": 600,
        "description": "超高火力バズーカ。単発威力に優れる重武装。",
        "weapon": Weapon(
            id="hyper_bazooka",
            name="Hyper Bazooka",
            power=250,
            range=500,
            accuracy=50,
            type="PHYSICAL",
            optimal_range=350.0,
            decay_rate=0.12,
            max_ammo=8,
            cool_down_turn=1,
        ),
    },
    {
        "id": "beam_saber",
        "name": "Beam Saber",
        "price": 450,
        "description": "ビームサーベル。近接戦闘用の高出力ビーム兵器。",
        "weapon": Weapon(
            id="beam_saber",
            name="Beam Saber",
            power=200,
            range=150,
            accuracy=85,
            type="BEAM",
            optimal_range=100.0,
            decay_rate=0.15,
            en_cost=50,
        ),
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


def get_weapon_listing_by_id(weapon_id: str) -> dict | None:
    """IDから武器商品データを取得する.

    Args:
        weapon_id: 武器ID

    Returns:
        dict | None: 武器商品データ。見つからない場合はNone
    """
    for listing in WEAPON_SHOP_LISTINGS:
        if listing["id"] == weapon_id:
            return listing
    return None
