import useSWR from "swr";
import { SkillDefinition, SkillUnlockRequest, SkillUnlockResponse } from "@/types/battle";
import { API_BASE_URL, getAuthToken, fetcher } from "./auth";

/** ゲーム内で習得可能なスキル定義一覧を取得するSWRフック（認証不要・パブリック） */
export function useSkills() {
  const { data, error, isLoading } = useSWR<SkillDefinition[]>(
    `${API_BASE_URL}/api/pilots/skills`,
    fetcher
  );

  return {
    skills: data,
    isLoading,
    isError: error,
  };
}

/**
 * スキルを習得または強化する
 * 未習得スキルは新規習得、習得済みスキルはレベルアップになる
 */
export async function unlockSkill(skillId: string): Promise<SkillUnlockResponse> {
  const token = await getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const request: SkillUnlockRequest = { skill_id: skillId };

  const res = await fetch(`${API_BASE_URL}/api/pilots/skills/unlock`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to unlock skill: ${res.status} ${res.statusText}`);
  }

  return res.json();
}
