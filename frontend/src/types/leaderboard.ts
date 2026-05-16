import { MobileSuit } from "./mobileSuit";

/** ランキング一覧の1エントリー */
export interface LeaderboardEntry {
    rank: number;
    user_id: string;
    pilot_name: string;
    wins: number;
    losses: number;
    kills: number;
    credits_earned: number;
}

/** パイロットの公開プロフィール情報（ランキング詳細画面で使用） */
export interface PlayerProfile {
    pilot_name: string;
    level: number;
    wins: number;
    losses: number;
    kills: number;
    /** 現在乗っている機体。未所持の場合はnull */
    mobile_suit: MobileSuit | null;
    /** 習得済みスキルのIDとレベルのマップ */
    skills: Record<string, number>;
}
