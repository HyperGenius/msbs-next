import useSWR from "swr";
import { LeaderboardEntry, PlayerProfile } from "@/types/battle";
import { enrichMobileSuit } from "@/utils/rankUtils";
import { EnrichedMobileSuit } from "./mobileSuit";
import { API_BASE_URL, fetcher } from "./auth";

/** mobile_suitフィールドがランク情報付きEnrichedMobileSuitに変換されたプロフィール型 */
export type EnrichedPlayerProfile = Omit<PlayerProfile, "mobile_suit"> & {
  mobile_suit: EnrichedMobileSuit | null;
};

/** 現在シーズンのランキング一覧を取得するSWRフック（認証不要・パブリック） */
export function useRankings(limit: number = 100) {
  const { data, error, isLoading, mutate } = useSWR<LeaderboardEntry[]>(
    `${API_BASE_URL}/api/rankings/current?limit=${limit}`,
    fetcher
  );

  return {
    rankings: data,
    isLoading,
    isError: error,
    mutate,
  };
}

/**
 * 指定ユーザーの公開プロフィールを取得するSWRフック
 * 機体情報にはランク情報を付与して返す。userIdがnullの場合はフェッチしない
 */
export function usePlayerProfile(userId: string | null) {
  const { data, error, isLoading } = useSWR<PlayerProfile>(
    userId ? `${API_BASE_URL}/api/rankings/pilot/${userId}/profile` : null,
    fetcher
  );

  const profile: EnrichedPlayerProfile | undefined = data
    ? {
        ...data,
        mobile_suit: data.mobile_suit ? enrichMobileSuit(data.mobile_suit) : null,
      }
    : undefined;

  return {
    profile,
    isLoading,
    isError: error,
  };
}
