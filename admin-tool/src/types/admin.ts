import { Weapon } from "./weapon";

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
    price: number;
    faction: string;
    description: string;
    specs: MasterMobileSuitSpec;
}

/** マスター機体の新規追加リクエスト（MasterMobileSuitと同形） */
export type MasterMobileSuitCreate = MasterMobileSuit;

/** マスター機体の部分更新リクエスト */
export interface MasterMobileSuitUpdate {
    name?: string;
    price?: number;
    faction?: string;
    description?: string;
    specs?: MasterMobileSuitSpec;
}

/** 管理者用マスター武器エントリー（武器ショップの元データ） */
export interface MasterWeapon {
    id: string;
    name: string;
    price: number;
    description: string;
    weapon: Weapon;
}

/** マスター武器の新規追加リクエスト（MasterWeaponと同形） */
export type MasterWeaponCreate = MasterWeapon;

/** マスター武器の部分更新リクエスト */
export interface MasterWeaponUpdate {
    name?: string;
    price?: number;
    description?: string;
    weapon?: Weapon;
}
