import useSWR from "swr";
import { useAuth } from "@clerk/nextjs";
import { BlueprintCollectionItem } from "@/types/battle";
import { API_BASE_URL, useAuthFetcher, authKey } from "./auth";

/** ログイン中プレイヤーの設計図コレクション（図鑑）を取得するSWRフック */
export function useBlueprintCollection() {
  const { isLoaded, isSignedIn } = useAuth();
  const authFetcher = useAuthFetcher();
  const { data, error, isLoading } = useSWR<BlueprintCollectionItem[]>(
    authKey(`${API_BASE_URL}/api/blueprints/collection`, isLoaded, isSignedIn),
    authFetcher
  );

  return {
    collection: data,
    isLoading: !isLoaded || isLoading,
    isError: error,
  };
}
