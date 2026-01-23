# backend/scripts/seed.py
import os
import sys

# パスを通す
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from sqlmodel import Session

from app.db import engine
from app.models.models import MobileSuit, Weapon

# 武器データ
rifle = Weapon(id="w1", name="Beam Rifle", power=300, range=600, accuracy=80)
mg = Weapon(id="w2", name="Zaku MG", power=100, range=400, accuracy=60)

# 機体データ
gundam = MobileSuit(
    name="Gundam", max_hp=1000, armor=100, mobility=1.5, weapons=[rifle]
)
zaku = MobileSuit(name="Zaku II", max_hp=800, armor=50, mobility=1.0, weapons=[mg])

with Session(engine) as session:
    session.add(gundam)
    session.add(zaku)
    session.commit()

exit()
