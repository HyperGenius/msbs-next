import { Vector3 } from "./geometry";
import { Weapon, Tactics } from "./weapon";

/** モビルスーツの全ステータス（バトル中のスナップショットとAPIレスポンスで共用） */
export interface MobileSuit {
    id: string;
    user_id?: string | null;
    name: string;
    max_hp: number;
    current_hp: number;
    armor: number;
    mobility: number;
    sensor_range?: number;
    position: Vector3;
    weapons: Weapon[];
    side: "PLAYER" | "ENEMY";
    team_id?: string | null;
    tactics: Tactics;
    beam_resistance?: number;
    physical_resistance?: number;
    melee_aptitude?: number;
    shooting_aptitude?: number;
    accuracy_bonus?: number;
    evasion_bonus?: number;
    acceleration_bonus?: number;
    turning_bonus?: number;
    terrain_adaptability?: Record<string, string>;
    max_en?: number;
    en_recovery?: number;
    max_propellant?: number;
    /** NPC の場合のパイロットレベル（スナップショットから） */
    npc_pilot_level?: number;
    /** NPC フラグ（スナップショットから） */
    is_npc?: boolean;
    /** HP ランク (S〜E) - APIから付与される */
    hp_rank?: string;
    /** 装甲ランク (S〜E) - APIから付与される */
    armor_rank?: string;
    /** 機動性ランク (S〜E) - APIから付与される */
    mobility_rank?: string;
}

/** ガレージ機能で機体を更新する際のリクエスト型（部分更新可） */
export interface MobileSuitUpdate {
    name?: string;
    max_hp?: number;
    armor?: number;
    mobility?: number;
    tactics?: Tactics;
    melee_aptitude?: number;
    shooting_aptitude?: number;
    accuracy_bonus?: number;
    evasion_bonus?: number;
    acceleration_bonus?: number;
    turning_bonus?: number;
}

/** ミッション定義（ミッション選択画面で使用） */
export interface Mission {
    id: number;
    name: string;
    difficulty: number;
    description: string;
    environment?: string;
    special_effects?: string[];
    enemy_config: {
        enemies: Array<{
            name: string;
            max_hp: number;
            armor: number;
            mobility: number;
            position: Vector3;
            weapon: Weapon;
            terrain_adaptability?: Record<string, string>;
        }>;
    };
}
