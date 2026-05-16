/** パイロットの進行データ（レベル・経験値・ステータスポイント・スキル状態を含む） */
export interface Pilot {
    id: string;
    user_id: string;
    name: string;
    faction: string;
    background: string;
    level: number;
    exp: number;
    credits: number;
    skill_points: number;
    /** 習得済みスキルのIDとレベルのマップ */
    skills: Record<string, number>;
    inventory?: Record<string, number>;
    /** 未割り振りのステータスポイント残数 */
    status_points: number;
    dex: number;
    intel: number;
    ref: number;
    tou: number;
    luk: number;
    awq: number;
    created_at: string;
    updated_at: string;
}
