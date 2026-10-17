import { WeaponSpec } from "@/types/weapon";

export type WeaponWarning = {
  code: "NO_MAX_AMMO" | "NO_EN_COST";
  label: string;
  detail: string;
};

// backend の CombatMixin._check_attack_resources と同じ近接判定。
// 近接武器は弾薬・EN を消費しないので、警告の対象にしない。
function isMeleeWeapon(spec: WeaponSpec): boolean {
  return spec.weapon_type === "MELEE" || spec.is_melee === true;
}

/** リソース消費の設定漏れを返す。backend は max_ammo が未設定・0 だと弾数無制限として扱う。 */
export function getWeaponWarnings(spec: WeaponSpec): WeaponWarning[] {
  if (isMeleeWeapon(spec)) return [];

  const warnings: WeaponWarning[] = [];
  if (spec.type === "BEAM") {
    if (!spec.en_cost) {
      warnings.push({
        code: "NO_EN_COST",
        label: "EN消費なし",
        detail: "ビーム武器の en_cost が未設定または 0 です。EN を消費せず撃ち続けられます。",
      });
    }
  } else if (!spec.max_ammo) {
    warnings.push({
      code: "NO_MAX_AMMO",
      label: "弾数未設定",
      detail: "実弾武器の max_ammo が未設定または 0 です。弾切れにならず撃ち続けられます。",
    });
  }
  return warnings;
}
