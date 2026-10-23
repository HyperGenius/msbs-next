import useSWR from "swr";
import { AvailableMissionsResponse } from "@/types/battle";
import { API_BASE_URL, fetcher } from "./auth";

/** 次回の開催でエントリーできる作戦と、その開催の戦域を取得するSWRフック（ログイン不要） */
export function useAvailableMissions() {
  const { data, error, isLoading } = useSWR<AvailableMissionsResponse>(
    `${API_BASE_URL}/api/missions/available`,
    fetcher
  );

  return {
    availableMissions: data?.missions,
    theater: data?.theater ?? null,
    isLoading,
    isError: error,
  };
}
