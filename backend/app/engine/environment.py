"""環境タイプの効果を戦闘エンジンに渡すためのプロファイル."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentProfile:
    """戦闘に適用する環境タイプの効果.

    エンジンは DB を参照しない。呼び出し側が `MasterEnvironment` から作って渡す。
    """

    environment_id: str
    sensor_range_multiplier: float = 1.0
    # 射撃の命中率倍率 = 1 − ranged_accuracy_penalty·min(1, d / ranged_penalty_ref_distance)
    ranged_accuracy_penalty: float = 0.0
    ranged_penalty_ref_distance: float = 400.0
    # 戦域が障害物密度を指定しないときに使う。
    default_obstacle_density: str = "MEDIUM"
    # 機体の terrain_adaptability にこの環境のキーが無いときのランク。
    default_terrain_grade: str = "A"
