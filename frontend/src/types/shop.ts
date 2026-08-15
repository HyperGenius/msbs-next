import { Weapon } from "./weapon";
import { MobileSuit } from "./mobileSuit";

/** ショップ商品の機体スペック詳細 */
export interface ShopItemSpecs {
    max_hp: number;
    armor: number;
    mobility: number;
    sensor_range: number;
    weapons: Weapon[];
    beam_resistance?: number;
    physical_resistance?: number;
    melee_aptitude?: number;
    shooting_aptitude?: number;
    accuracy_bonus?: number;
    evasion_bonus?: number;
    acceleration_bonus?: number;
    turning_bonus?: number;
}

/** ショップに陳列された機体商品 */
export interface ShopListing {
    id: string;
    name: string;
    price: number;
    description: string;
    specs: ShopItemSpecs;
}

/** 機体購入後のレスポンス */
export interface PurchaseResponse {
    message: string;
    mobile_suit_id: string;
    remaining_credits: number;
}

/** 機体の単一ステータス強化リクエスト */
export interface UpgradeRequest {
    mobile_suit_id: string;
    target_stat: "hp" | "armor" | "mobility" | "weapon_power" | "melee_aptitude" | "shooting_aptitude" | "accuracy_bonus" | "evasion_bonus" | "acceleration_bonus" | "turning_bonus";
    steps?: number;
}

/** 強化後のレスポンス（更新後の機体情報と消費クレジットを含む） */
export interface UpgradeResponse {
    message: string;
    mobile_suit: MobileSuit;
    remaining_credits: number;
    cost_paid: number;
}

/** 強化プレビューの情報（費用と強化後の値を事前確認するために使用） */
export interface UpgradePreview {
    mobile_suit_id: string;
    stat_type: string;
    current_value: number;
    new_value: number;
    cost: number;
    at_max_cap: boolean;
}

/** 複数ステータスの一括強化リクエスト（例: { "hp": 2, "armor": 1 }） */
export interface BulkUpgradeRequest {
    mobile_suit_id: string;
    upgrades: Record<string, number>;
}

/** 一括強化後のレスポンス */
export interface BulkUpgradeResponse {
    message: string;
    mobile_suit: MobileSuit;
    remaining_credits: number;
    total_cost_paid: number;
}

/** 武器ショップに陳列された武器商品 */
export interface WeaponListing {
    id: string;
    name: string;
    price: number;
    description: string;
    /** 購入画面用フレーバーテキスト（1〜2行程度）。未設定の場合は null */
    flavor_text: string | null;
    weapon: Weapon;
}

/** 武器購入後のレスポンス */
export interface WeaponPurchaseResponse {
    message: string;
    weapon_id: string;
    /** 購入によって生成されたプレイヤー武器インスタンスのID */
    player_weapon_id: string;
    remaining_credits: number;
}

/** 武器装備リクエスト（スロット番号を省略すると空きスロットに自動割り当て） */
export interface EquipWeaponRequest {
    player_weapon_id: string;
    slot_index?: number;
}

/**
 * 武器インスタンスの強化・改造差分（Issue #404）。
 * キー欠損時はバックエンド側で0/未変更として扱われる（既存の空 `{}` も安全）。
 * `weapon_power`（機体強化、`EngineeringService` 管理）とは別軸の武器個別改造。
 */
export interface WeaponCustomStats {
    power_bonus?: number;
    accuracy_bonus?: number;
    upgrade_level?: number;
}

/** プレイヤーが所有する武器インスタンス（マスターとは別に個別強化データを持つ） */
export interface PlayerWeapon {
    id: string;
    master_weapon_id: string;
    base_snapshot: Record<string, unknown>;
    custom_stats: WeaponCustomStats;
    equipped_ms_id: string | null;
    equipped_slot: number | null;
    acquired_at: string;
}

/** 武器改造で強化可能な custom_stats のキー（バックエンドの stat_type と一致させる） */
export type WeaponUpgradeStatType = "power_bonus" | "accuracy_bonus";

/**
 * 武器改造（custom_stats強化）リクエスト（Issue #411）。
 * 未装備の武器も改造可能。装備中の武器はバトル開始時に再同期される。
 */
export interface WeaponUpgradeRequest {
    target_stat: WeaponUpgradeStatType;
    steps?: number;
}

/** 武器改造後のレスポンス（更新後の武器インスタンスと消費クレジットを含む） */
export interface WeaponUpgradeResponse {
    message: string;
    player_weapon: PlayerWeapon;
    remaining_credits: number;
    cost_paid: number;
}

/** 武器改造プレビューの情報（費用と改造後の値を事前確認するために使用） */
export interface WeaponUpgradePreview {
    player_weapon_id: string;
    stat_type: WeaponUpgradeStatType;
    current_value: number;
    new_value: number;
    cost: number;
    at_max_cap: boolean;
}
