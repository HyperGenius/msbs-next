import type { LocalSimMissionMaster, LocalSimMissionUnit } from "@/types/localSim";

/** 機体マスターかエースから作る機体か。そうなら直書きの性能は使わない */
export function referencesMaster(unit: LocalSimMissionUnit): boolean {
  return Boolean(unit.master_mobile_suit_id || unit.ace_id);
}

function isValidUnit(unit: LocalSimMissionUnit): boolean {
  if (referencesMaster(unit)) {
    const ratio = unit.current_hp_ratio;
    return ratio == null || (Number.isFinite(ratio) && ratio > 0 && ratio <= 1);
  }
  const weapon = unit.weapon;
  return (
    Boolean(unit.name) &&
    weapon !== undefined &&
    [unit.max_hp, unit.armor, unit.mobility, weapon.power, weapon.range, weapon.accuracy].every(Number.isFinite) &&
    (unit.max_hp as number) > 0
  );
}

/** 編集後の作戦マスターで、友軍・敵機・作戦目標の必要数が数として正しいか確かめる */
export function missionMasterError(master: LocalSimMissionMaster): string | null {
  const units = [...(master.allies_config ?? []), ...master.enemy_config.enemies];
  const bad = units.find((u) => !isValidUnit(u));
  if (bad) {
    const label = bad.name || bad.master_mobile_suit_id || bad.ace_id || "（名前なし）";
    return `作戦の機体「${label}」の値が不正です。`;
  }
  const required = master.objective?.params.required;
  if (required !== undefined && !(Number.isInteger(required) && (required as number) >= 0)) {
    return "作戦目標の必要数は 0 以上の整数にしてください。";
  }
  return null;
}
