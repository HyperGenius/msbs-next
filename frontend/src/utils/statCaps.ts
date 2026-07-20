/**
 * 機体強化ステータスの上限値（全MS共通・固定値）
 *
 * backend/app/services/engineering_service.py の MAX_*_CAP 定数と一致させること。
 * バックエンドとフロントエンドで別々に定義・同期しているため、
 * 片方を変更した場合はもう片方も必ず更新する。
 */
export const STAT_CAPS = {
  hp: 2000,
  armor: 120,
  mobility: 3.0,
  melee_aptitude: 2.0,
  shooting_aptitude: 2.0,
  accuracy_bonus: 10.0,
  evasion_bonus: 10.0,
  acceleration_bonus: 2.0,
  turning_bonus: 2.0,
} as const;
