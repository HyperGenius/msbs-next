import { Vector3 } from "./geometry";
import { Weapon, Tactics } from "./weapon";

/** 部位名 (Issue #503)。欠損部位を除きこれら6種で構成される */
export type PartName =
    | "HEAD"
    | "TORSO"
    | "RIGHT_ARM"
    | "LEFT_ARM"
    | "RIGHT_LEG"
    | "LEFT_LEG";

/** 部位単体のHP/装甲状態 (Issue #503) */
export interface PartState {
    max_hp: number;
    current_hp: number;
    armor: number;
    destroyed: boolean;
}

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
    /** ブースト中の EN 消費量 (/s) */
    boost_en_cost?: number;
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
    /** 武器スロット数 (マスター機体由来。未取得時は既存の2枠機体として扱う) */
    weapon_slot_count?: number;
    /** ビームジェネレータLv (マスター機体由来。required_beam_generator_lv がこの値を超えるBEAM武器は装備不可) */
    beam_generator_lv?: number;
    /** 欠損部位のリスト (Issue #503。例: 脚部のないMSは ["RIGHT_LEG", "LEFT_LEG"]) */
    missing_parts?: PartName[];
    /** 部位別HP/装甲状態 (Issue #503)。欠損部位はキーに含まれない */
    parts?: Partial<Record<PartName, PartState>>;
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
