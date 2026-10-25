# backend/app/services/mission_master_loader.py
"""作戦の機体が参照する機体マスターとエースを DB から読む."""

from sqlmodel import Session, col, select

from app.core.gamedata import ace_pilot_to_data
from app.models.models import AcePilot, MasterMobileSuit, Mission, Weapon
from app.services.mission_battle import MissionMasters, referenced_master_ids
from app.services.mobile_suit_service import MobileSuitService


def load_mission_masters(session: Session, mission: Mission) -> MissionMasters:
    """作戦の機体が参照する機体マスターとエースを読む.

    DB に無い参照は入れない。組み立て（`build_mission_battle()`）で失敗させるため。
    返す機体マスターはセッションから切り離したコピーで、武器の `master_weapon_id` を書き込む。
    並びは作戦で出てくる順にする（ロスターに保存したときの差分を安定させるため）。
    """
    mobile_suit_ids, ace_ids = referenced_master_ids(mission)
    records = {
        record.id: record
        for record in session.exec(
            select(MasterMobileSuit).where(
                col(MasterMobileSuit.id).in_(mobile_suit_ids)
            )
        ).all()
    }
    mobile_suits: dict[str, MasterMobileSuit] = {}
    for master_id in mobile_suit_ids:
        if master_id not in records:
            continue
        master = MasterMobileSuit.model_validate(records[master_id].model_dump())
        weapons = [Weapon(**w) for w in master.specs["weapons"]]
        MobileSuitService.link_master_weapons(session, weapons)
        master.specs = {
            **master.specs,
            "weapons": [w.model_dump(mode="json") for w in weapons],
        }
        mobile_suits[master_id] = master
    aces = {}
    for ace_id in ace_ids:
        ace = session.get(AcePilot, ace_id)
        if ace is not None:
            aces[ace_id] = ace_pilot_to_data(ace.model_dump())
    return MissionMasters(mobile_suits=mobile_suits, aces=aces)
