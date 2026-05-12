# backend/app/engine/battle_utils.py
"""戦闘ユーティリティ: フォーマット・チャッター関数群のミックスイン."""

import random
from typing import TYPE_CHECKING, Any

from app.core.npc_data import BATTLE_CHATTER
from app.models.models import BattleLog, MobileSuit

if TYPE_CHECKING:
    pass

# バトルログ保存時に除去するデバッグ専用フィールドのセット
_BATTLE_LOG_DEBUG_FIELDS: frozenset[str] = frozenset({"fuzzy_scores"})


def strip_debug_fields(logs: list[BattleLog]) -> list[dict[str, Any]]:
    """バトルログからデバッグ用フィールドを除去した dict リストを返す.

    DBへの保存前に呼び出すことで、不要なストレージ消費を削減する。
    APIレスポンス（BattleResponse.logs）には影響しない。

    Args:
        logs: 除去対象のバトルログリスト

    Returns:
        デバッグフィールド（fuzzy_scores 等）を除いた BattleLog 相当の dict リスト
    """
    return [
        {k: v for k, v in log.model_dump().items() if k not in _BATTLE_LOG_DEBUG_FIELDS}
        for log in logs
    ]


class BattleUtilsMixin:
    """戦闘ユーティリティメソッドのミックスイン.

    フォーマット・チャッター・ラベル変換などのピュアな補助関数群を提供する。
    """

    def _generate_chatter(self, unit: MobileSuit, chatter_type: str) -> str | None:
        """NPCのセリフを生成する.

        Args:
            unit: ユニット
            chatter_type: セリフの種類 (attack/hit/destroyed/miss)

        Returns:
            str | None: セリフ。NPCでない場合や確率で発言しない場合はNone
        """
        # NPCでない場合はセリフなし
        if not unit.personality:
            return None

        # 30%の確率でセリフを発言
        if random.random() > 0.3:
            return None

        # 性格に応じたセリフを取得
        personality = unit.personality
        if personality in BATTLE_CHATTER:
            chatter_list = BATTLE_CHATTER[personality].get(chatter_type, [])
            if chatter_list:
                return random.choice(chatter_list)

        return None

    def _format_actor_name(
        self, actor: MobileSuit, viewer_team_id: str | None = None
    ) -> str:
        """パイロット名付きの機体名を返す.

        Args:
            actor: 機体
            viewer_team_id: 視点チームID。指定された場合、そのチームから未索敵の機体は
                            「UNKNOWN機」と表示する。省略時はアクターが敵チームなら
                            プレイヤーチーム視点で自動判定する。

        Returns:
            - 未索敵の敵: 「UNKNOWN機」
            - パイロット名がある場合: 「[パイロット名]のMS名」
            - パイロット名がない場合: 「MS名」
        """
        # 索敵チェック: 視点チームIDを決定
        effective_viewer = viewer_team_id
        if effective_viewer is None and actor.team_id != self.player.team_id:  # type: ignore[attr-defined]
            # アクターが敵チームの場合、プレイヤー視点で索敵判定を行う
            effective_viewer = self.player.team_id  # type: ignore[attr-defined]

        if effective_viewer and actor.id not in self.team_detected_units.get(  # type: ignore[attr-defined]
            effective_viewer, set()
        ):
            return "UNKNOWN機"

        pilot_name = getattr(actor, "pilot_name", None)
        if pilot_name:
            return f"[{pilot_name}]の{actor.name}"
        return actor.name

    def _get_distance_label(self, distance: float) -> str:
        """距離を日本語ラベルに変換する.

        Args:
            distance: 距離(m)

        Returns:
            近距離 / 中距離 / 遠距離
        """
        if distance <= 200:
            return "近距離"
        if distance <= 400:
            return "中距離"
        return "遠距離"

    def _get_damage_description(self, damage: int, target: MobileSuit) -> str:
        """HP割合に基づくダメージ表現を返す.

        Args:
            damage: ダメージ量
            target: 攻撃対象

        Returns:
            致命的なヒット / 手痛いダメージ / ダメージ / 軽微なダメージ
        """
        ratio = damage / max(1, target.max_hp)
        if ratio >= 0.20:
            return "致命的なヒット"
        if ratio >= 0.10:
            return "手痛いダメージ"
        if ratio >= 0.05:
            return "ダメージ"
        return "軽微なダメージ"

    def _get_hp_status_comment(self, target: MobileSuit) -> str:
        """ダメージ後のHP残量に応じた状況コメントを返す.

        Args:
            target: 攻撃対象

        Returns:
            HP残量に応じた状況コメント（余裕がある場合は空文字）
        """
        ratio = target.current_hp / max(1, target.max_hp)
        if ratio <= 0.10:
            return " — 大破寸前...！（残りHP僅少）"
        if ratio <= 0.20:
            return " — 機体が限界に近い！"
        if ratio <= 0.50:
            return " — 戦闘継続能力が低下"
        return ""
