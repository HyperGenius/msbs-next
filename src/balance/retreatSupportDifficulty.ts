export interface BuildStats {
  mobility: number;
  recon: number;
  firepower: number;
  armor: number;
}

/**
 * Adjusts retreat-support mission difficulty so mobility and recon builds gain a decisive advantage (#711).
 */
export function computeRetreatSupportEffectiveDifficulty(
  baseDifficulty: number,
  stats: BuildStats
): number {
  const mobilityBonus = stats.mobility * 0.45;
  const reconBonus = stats.recon * 0.40;
  const heavyPenalty = Math.max(0, (stats.armor - stats.mobility) * 0.15);
  const adjusted = baseDifficulty - mobilityBonus - reconBonus + heavyPenalty;
  return Math.max(1, Number(adjusted.toFixed(2)));
}
