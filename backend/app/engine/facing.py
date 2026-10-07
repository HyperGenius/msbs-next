# backend/app/engine/facing.py
"""胴体の向きと移動の向きのずれによる速度の割引."""

import math

from app.engine.constants import (
    BACKPEDAL_ANGLE_DEG,
    FACING_SPEED_MODIFIER_BACK,
    FACING_SPEED_MODIFIER_FRONT,
    FACING_SPEED_MODIFIER_SIDE,
)


def facing_offset_deg(body_heading_deg: float, movement_heading_deg: float) -> float:
    """胴体の向きと移動の向きのずれを 0〜180 度で返す."""
    return abs(((movement_heading_deg - body_heading_deg + 180.0) % 360.0) - 180.0)


def _ease(start: float, end: float, t: float) -> float:
    """区間の両端で傾き 0 になるように、start から end へつなぐ (t は 0〜1)."""
    return start + (end - start) * (1.0 - math.cos(math.pi * t)) / 2.0


def facing_speed_modifier(
    body_heading_deg: float, movement_heading_deg: float
) -> float:
    """最高速度に掛ける係数を返す.

    前・横・後ろの 3 点の値を、90 度ごとの区間でつなぐ。
    各点で傾きを 0 にするのは、向きのわずかな揺れで速度が変わらないようにするため。
    """
    offset = facing_offset_deg(body_heading_deg, movement_heading_deg)
    if offset <= 90.0:
        return _ease(
            FACING_SPEED_MODIFIER_FRONT, FACING_SPEED_MODIFIER_SIDE, offset / 90.0
        )
    return _ease(
        FACING_SPEED_MODIFIER_SIDE, FACING_SPEED_MODIFIER_BACK, (offset - 90.0) / 90.0
    )


def is_backpedaling(body_heading_deg: float, movement_heading_deg: float) -> bool:
    """胴体を向けた方と逆へ動いている（後退中）かを返す."""
    return (
        facing_offset_deg(body_heading_deg, movement_heading_deg) > BACKPEDAL_ANGLE_DEG
    )


def is_unit_backpedaling(resources: dict) -> bool:
    """`unit_resources` の向きから、後退中かを返す."""
    return is_backpedaling(
        resources.get("body_heading_deg", 0.0),
        resources.get("movement_heading_deg", 0.0),
    )
