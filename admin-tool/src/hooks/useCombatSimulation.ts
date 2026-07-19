/* admin-tool/src/hooks/useCombatSimulation.ts */
"use client";

import { useState } from "react";
import { CombatSimulationRequest, CombatSimulationResponse } from "@/types/admin";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const ADMIN_API_KEY = process.env.NEXT_PUBLIC_ADMIN_API_KEY || "";

const ENDPOINT = `${API_BASE_URL}/api/admin/simulate-combat`;

/**
 * 1対1 攻撃シミュレーションAPIを呼び出すフック
 */
export function useCombatSimulation() {
  const [result, setResult] = useState<CombatSimulationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  async function simulate(payload: CombatSimulationRequest): Promise<CombatSimulationResponse> {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(ENDPOINT, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": ADMIN_API_KEY,
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Simulation failed: ${res.status}`);
      }
      const data: CombatSimulationResponse = await res.json();
      setResult(data);
      return data;
    } catch (e) {
      const err = e instanceof Error ? e : new Error("Unknown error");
      setError(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }

  function reset() {
    setResult(null);
    setError(null);
  }

  return { result, isLoading, error, simulate, reset };
}
