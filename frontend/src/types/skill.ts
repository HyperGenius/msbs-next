import { Pilot } from "./pilot";

/** スキルの定義情報（スキルツリー表示・習得判定に使用） */
export interface SkillDefinition {
    id: string;
    name: string;
    description: string;
    /** 1レベルあたりの効果量 */
    effect_per_level: number;
    max_level: number;
}

/** スキル習得・レベルアップのリクエスト */
export interface SkillUnlockRequest {
    skill_id: string;
}

/** スキル習得後のレスポンス（更新後のパイロット情報を含む） */
export interface SkillUnlockResponse {
    pilot: Pilot;
    message: string;
}
