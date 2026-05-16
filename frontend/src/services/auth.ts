import { useAuth } from "@clerk/nextjs";
import { useCallback } from "react";

/** バックエンドAPIのベースURL。本番は環境変数、開発時はlocalhost:8000にフォールバック */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

/**
 * Clerkの認証トークンをクライアントサイドで取得する（イベントハンドラ等、フックが使えない場所向け）
 * ユーザーが操作できる時点ではClerkの初期化は完了しているため、window.Clerkから直接取得する
 */
export async function getAuthToken(): Promise<string | null> {
  if (typeof window !== 'undefined') {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const clerk = (window as any).Clerk;
    if (clerk && clerk.session) {
      return await clerk.session.getToken();
    }
  }
  return null;
}

/** 認証不要なパブリックエンドポイント向けのSWRフェッチャー */
export const fetcher = async (url: string) => {
  const res = await fetch(url);
  if (!res.ok) {
    const error = new Error(`Failed to fetch data from ${url}: ${res.status} ${res.statusText}`) as Error & { status: number };
    error.status = res.status;
    throw error;
  }
  return res.json();
};

/**
 * Bearerトークン付きのSWRフェッチャーを返すフック
 * useAuth の getToken を利用するためClerk初期化完了後にトークンを正しく付与できる
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function useAuthFetcher(): (url: string) => Promise<any> {
  const { getToken } = useAuth();
  return useCallback(async (url: string) => {
    const token = await getToken();
    const headers: HeadersInit = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const res = await fetch(url, { headers });
    if (!res.ok) {
      const error = new Error(`Failed to fetch data from ${url}: ${res.status} ${res.statusText}`) as Error & { status: number };
      error.status = res.status;
      throw error;
    }
    return res.json();
  }, [getToken]);
}

/**
 * Clerk初期化完了かつサインイン済みの場合のみURLを返すSWRキーヘルパー
 * 認証完了前にSWRがリクエストを送出するのを防ぐ
 */
export function authKey(url: string, isLoaded: boolean, isSignedIn: boolean | null | undefined): string | null {
  return isLoaded && isSignedIn ? url : null;
}
