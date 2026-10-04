/** 予報に出すミノフスキー濃度の段階 */
export type MinovskyLevel = "LOW" | "MEDIUM" | "HIGH";

/** 1回分の開催の戦域予報（GET /api/theaters/forecast） */
export interface TheaterForecast {
  /** 開催予定時刻（ISO 8601、UTC） */
  scheduled_at: string;
  /** 募集中のルームの開催か */
  is_current: boolean;
  theater_id: string;
  theater_name: string;
  environment_id: string;
  environment_name: string;
  /** 機体に地形適正の設定が無いときのランク */
  default_terrain_grade: string;
  /** ミノフスキー濃度（0〜1） */
  minovsky_density: number;
  minovsky_level: MinovskyLevel;
  /** 有利・不利のヒント */
  hint: string;
  description: string;
}
