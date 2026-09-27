import useSWR from "swr";
import { useAuth } from "@clerk/nextjs";
import { PlayerTechnologyProgress } from "@/types/battle";
import { API_BASE_URL, useAuthFetcher, authKey } from "./auth";

/** ログイン中プレイヤーの技術ごとのLv・累計断片数・断片の入手先を取得するSWRフック */
export function useTechnologies() {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading } = useSWR<PlayerTechnologyProgress[]>(
    authKey(`${API_BASE_URL}/api/technologies/me`, isLoaded, isSignedIn),
    authFetcher
  );

  return {
    technologies: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
  };
}
