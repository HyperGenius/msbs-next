import { Weapon, WeaponSpec } from "./weapon";

/** 管理者用マスター機体のスペック定義 */
export interface MasterMobileSuitSpec {
    max_hp: number;
    armor: number;
    mobility: number;
    sensor_range: number;
    beam_resistance: number;
    physical_resistance: number;
    melee_aptitude: number;
    shooting_aptitude: number;
    accuracy_bonus: number;
    evasion_bonus: number;
    acceleration_bonus: number;
    turning_bonus: number;
    weapons: Weapon[];
}

/** 管理者用マスター機体エントリー（ショップ・初期配備の元データ） */
export interface MasterMobileSuit {
    id: string;
    name: string;
    /** 日本語表示名 */
    name_ja: string;
    /** 型番 (例: RGM-79) */
    model_number: string;
    price: number;
    faction: string;
    description: string;
    /** 武器スロット数 (1以上) */
    weapon_slot_count: number;
    /** ビームジェネレータLv (0以上) */
    beam_generator_lv: number;
    /** 購入画面用フレーバーテキスト（1〜2行程度）。未設定の場合は null */
    flavor_text: string | null;
    specs: MasterMobileSuitSpec;
}

/** マスター機体の新規追加リクエスト（MasterMobileSuitと同形） */
export type MasterMobileSuitCreate = MasterMobileSuit;

/** マスター機体の部分更新リクエスト */
export interface MasterMobileSuitUpdate {
    name?: string;
    name_ja?: string;
    model_number?: string;
    price?: number;
    faction?: string;
    description?: string;
    weapon_slot_count?: number;
    beam_generator_lv?: number;
    flavor_text?: string | null;
    specs?: MasterMobileSuitSpec;
}

/** 管理者用マスター武器エントリー（武器ショップの元データ）。
 *  id/name はテーブルカラムが正のため、weapon(JSON) 側は WeaponSpec (id/nameなし) を使う */
export interface MasterWeapon {
    id: string;
    name: string;
    price: number;
    description: string;
    /** 購入画面用フレーバーテキスト（1〜2行程度）。未設定の場合は null */
    flavor_text: string | null;
    weapon: WeaponSpec;
}

/** マスター武器の新規追加リクエスト（MasterWeaponと同形） */
export type MasterWeaponCreate = MasterWeapon;

/** マスター武器の部分更新リクエスト */
export interface MasterWeaponUpdate {
    name?: string;
    price?: number;
    description?: string;
    flavor_text?: string | null;
    weapon?: WeaponSpec;
}

/** 攻撃セクタ（正面・側面・背面） */
export type AttackSector = "FRONT" | "FRONT_SIDE" | "REAR_SIDE" | "REAR";

/** シミュレーション用パイロットステータス入力 */
export interface PilotStatsInput {
    sht: number;
    mel: number;
    intel: number;
    ref: number;
    tou: number;
    luk: number;
}

export const DEFAULT_PILOT_STATS: PilotStatsInput = {
    sht: 0,
    mel: 0,
    intel: 0,
    ref: 0,
    tou: 0,
    luk: 0,
};

/** 1対1 攻撃シミュレーションリクエスト */
export interface CombatSimulationRequest {
    attacker_spec: MasterMobileSuitSpec;
    attacker_weapon_id: string;
    attacker_pilot?: PilotStatsInput;
    defender_spec: MasterMobileSuitSpec;
    defender_pilot?: PilotStatsInput;
    distance?: number;
    attack_sector?: AttackSector;
    trials?: number;
}

/** モンテカルロ試行の実測統計 */
export interface MonteCarloCombatStats {
    trials: number;
    actual_hit_rate: number;
    actual_crit_rate: number;
    avg_damage: number;
    min_damage: number;
    max_damage: number;
    perfect_evade_rate: number;
}

/** 1対1 攻撃シミュレーションレスポンス */
export interface CombatSimulationResponse {
    hit_chance: number;
    crit_chance: number;
    base_damage: number;
    crit_damage: number;
    resistance_applied_damage: number;
    monte_carlo: MonteCarloCombatStats | null;
}

/** NPCの性格タイプ */
export type NpcPersonality = "AGGRESSIVE" | "CAUTIOUS" | "SNIPER";

/** NPC所有機体エントリー（Pilot詳細に含まれる） */
export interface NpcMobileSuit {
    id: string;
    name: string;
    max_hp: number;
    current_hp: number;
    armor: number;
    mobility: number;
    personality: NpcPersonality | null;
    is_ace: boolean;
    ace_id: string | null;
    pilot_name: string | null;
    bounty_exp: number;
    bounty_credits: number;
}

/** NPCパイロット一覧エントリー（管理者用レスポンス） */
export interface NpcPilot {
    id: string;
    user_id: string;
    name: string;
    npc_personality: NpcPersonality | null;
    /** ACE_PILOTS由来のエースパイロットかどうか（名前一致によるbest-effort判定） */
    is_ace: boolean;
    level: number;
    exp: number;
    credits: number;
    skill_points: number;
    status_points: number;
    sht: number;
    mel: number;
    intel: number;
    ref: number;
    tou: number;
    luk: number;
    awq: number;
    mobile_suit_count: number;
    created_at: string;
    updated_at: string;
}

/** NPCパイロット詳細（所有機体一覧付き） */
export interface NpcPilotDetail extends NpcPilot {
    mobile_suits: NpcMobileSuit[];
}

/** NPCパイロットの部分更新リクエスト */
export interface NpcPilotUpdate {
    npc_personality?: NpcPersonality;
    level?: number;
    exp?: number;
    credits?: number;
    skill_points?: number;
    status_points?: number;
    sht?: number;
    mel?: number;
    intel?: number;
    ref?: number;
    tou?: number;
    luk?: number;
    awq?: number;
}

/** NPC所有機体の部分更新リクエスト */
export interface NpcMobileSuitUpdate {
    name?: string;
    max_hp?: number;
    armor?: number;
    mobility?: number;
}
