# backend/app/services/mobile_suit_service.py
from sqlmodel import Session, select

from app.models.models import MobileSuit, MobileSuitUpdate


class MobileSuitService:
    """機体データを操作するサービス."""

    @staticmethod
    def get_all_mobile_suits(session: Session) -> list[MobileSuit]:
        """全機体データを取得する."""
        statement = select(MobileSuit).order_by(MobileSuit.name)
        results = session.exec(statement).all()
        return list(results)

    @staticmethod
    def update_mobile_suit(
        session: Session, ms_id: str, update_data: MobileSuitUpdate
    ) -> MobileSuit | None:
        """機体データを更新する."""
        # IDで検索
        statement = select(MobileSuit).where(MobileSuit.id == ms_id)
        ms = session.exec(statement).first()

        if not ms:
            return None

        # データの更新 (Pydantic v2 style)
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(ms, key, value)

        session.add(ms)
        session.commit()
        session.refresh(ms)

        return ms
