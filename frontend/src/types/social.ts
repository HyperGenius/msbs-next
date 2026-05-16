/** フレンド関係レコード（リクエスト中・承認済みを含む） */
export interface Friend {
    id: string;
    user_id: string;
    friend_user_id: string;
    status: "PENDING" | "ACCEPTED" | "BLOCKED";
    /** フレンドのパイロット名（未登録の場合はnull） */
    pilot_name: string | null;
    created_at: string;
}

/** チームの参加メンバー情報 */
export interface TeamMember {
    user_id: string;
    /** バトルエントリー可能かを示すReadyフラグ */
    is_ready: boolean;
    joined_at: string;
}

/** チーム情報 */
export interface Team {
    id: string;
    owner_user_id: string;
    name: string;
    status: "FORMING" | "READY" | "DISBANDED";
    members: TeamMember[];
    created_at: string;
}

/** チームバトルエントリーのリクエスト */
export interface TeamEntryRequest {
    team_id: string;
    mobile_suit_id: string;
}

/** チームバトルエントリー後のレスポンス（全メンバー分のエントリーIDを含む） */
export interface TeamEntryResponse {
    message: string;
    entry_ids: string[];
    room_id: string;
}
