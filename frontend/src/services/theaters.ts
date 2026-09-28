import useSWR from "swr";
import { TheaterForecast } from "@/types/battle";
import { API_BASE_URL, fetcher } from "./auth";

/** 今回と次回以降の開催の戦域予報を取得するSWRフック（ログイン不要） */
export function useTheaterForecast(days = 3) {
  const { data, error, isLoading } = useSWR<TheaterForecast[]>(
    `${API_BASE_URL}/api/theaters/forecast?days=${days}`,
    fetcher
  );

  return {
    forecasts: data,
    isLoading,
    isError: error,
  };
}
