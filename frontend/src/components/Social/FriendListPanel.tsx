"use client";

import { useState } from "react";
import { useUser } from "@clerk/nextjs";
import {
  useFriends,
  useFriendRequests,
  sendFriendRequest,
  acceptFriendRequest,
  rejectFriendRequest,
  removeFriend,
} from "@/services/api";

interface FriendListPanelProps {
  onClose: () => void;
}

export default function FriendListPanel({ onClose }: FriendListPanelProps) {
  const { user } = useUser();
  const myUserId = user?.id ?? "";
  const { friends, isLoading, mutate: mutateFriends } = useFriends();
  const {
    requests,
    isLoading: requestsLoading,
    mutate: mutateRequests,
  } = useFriendRequests();
  const [tab, setTab] = useState<"friends" | "requests" | "add">("friends");
  const [addUserId, setAddUserId] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const handleSendRequest = async () => {
    if (!addUserId.trim()) return;
    setError("");
    setMessage("");
    try {
      await sendFriendRequest(addUserId.trim());
      setMessage("リクエストを送信しました");
      setAddUserId("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    }
  };

  const handleAccept = async (userId: string) => {
    try {
      await acceptFriendRequest(userId);
      mutateRequests();
      mutateFriends();
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    }
  };

  const handleReject = async (userId: string) => {
    try {
      await rejectFriendRequest(userId);
      mutateRequests();
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    }
  };

  const handleRemove = async (userId: string) => {
    try {
      await removeFriend(userId);
      mutateFriends();
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-gray-900 border-4 border-green-800 rounded-lg p-6">
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-green-400">
              Friends
            </h2>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-red-900 hover:bg-red-800 rounded font-bold transition-colors"
            >
              ✕
            </button>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 mb-6">
            {(
              [
                { key: "friends", label: "フレンド一覧" },
                {
                  key: "requests",
                  label: `リクエスト${requests?.length ? ` (${requests.length})` : ""}`,
                },
                { key: "add", label: "＋ 追加" },
              ] as const
            ).map(({ key, label }) => (
              <button
                key={key}
                onClick={() => {
                  setTab(key);
                  setMessage("");
                  setError("");
                }}
                className={`px-4 py-2 rounded font-bold transition-colors ${
                  tab === key
                    ? "bg-green-800 text-green-200"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Error/Message */}
          {error && (
            <div className="bg-red-900/30 border border-red-500 p-3 rounded mb-4">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}
          {message && (
            <div className="bg-green-900/30 border border-green-500 p-3 rounded mb-4">
              <p className="text-green-400 text-sm">{message}</p>
            </div>
          )}

          {/* Friends Tab */}
          {tab === "friends" && (
            <div className="space-y-3">
              {isLoading && (
                <p className="text-gray-400 text-center py-4">読み込み中...</p>
              )}
              {friends && friends.length === 0 && (
                <p className="text-gray-500 text-center py-8">
                  フレンドがいません。「＋ 追加」タブからリクエストを送りましょう。
                </p>
              )}
              {friends?.map((friend) => (
                <div
                  key={friend.id}
                  className="bg-gray-800 border border-green-800/50 rounded-lg p-4 flex justify-between items-center"
                >
                  <div>
                    <p className="text-green-400 font-bold">
                      {friend.pilot_name || "Unknown Pilot"}
                    </p>
                    <p className="text-gray-500 text-xs">
                      ID: {friend.user_id === myUserId ? friend.friend_user_id : friend.user_id}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      const otherId =
                        friend.user_id === myUserId
                          ? friend.friend_user_id
                          : friend.user_id;
                      handleRemove(otherId);
                    }}
                    className="px-3 py-1 bg-red-900/50 hover:bg-red-800 text-red-300 rounded text-sm transition-colors"
                  >
                    解除
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* Requests Tab */}
          {tab === "requests" && (
            <div className="space-y-3">
              {requestsLoading && (
                <p className="text-gray-400 text-center py-4">読み込み中...</p>
              )}
              {requests && requests.length === 0 && (
                <p className="text-gray-500 text-center py-8">
                  受信中のリクエストはありません。
                </p>
              )}
              {requests?.map((req) => (
                <div
                  key={req.id}
                  className="bg-gray-800 border border-yellow-800/50 rounded-lg p-4 flex justify-between items-center"
                >
                  <div>
                    <p className="text-yellow-400 font-bold">
                      {req.pilot_name || "Unknown Pilot"}
                    </p>
                    <p className="text-gray-500 text-xs">
                      From: {req.user_id}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleAccept(req.user_id)}
                      className="px-3 py-1 bg-green-900/50 hover:bg-green-800 text-green-300 rounded text-sm transition-colors"
                    >
                      承認
                    </button>
                    <button
                      onClick={() => handleReject(req.user_id)}
                      className="px-3 py-1 bg-red-900/50 hover:bg-red-800 text-red-300 rounded text-sm transition-colors"
                    >
                      拒否
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Add Friend Tab */}
          {tab === "add" && (
            <div className="space-y-4">
              <p className="text-gray-400 text-sm">
                フレンドリクエストを送信するには、相手のユーザーIDを入力してください。
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={addUserId}
                  onChange={(e) => setAddUserId(e.target.value)}
                  placeholder="ユーザーID を入力"
                  className="flex-1 bg-gray-800 border border-gray-700 rounded px-4 py-2 text-gray-200 placeholder-gray-600 focus:border-green-500 focus:outline-none"
                />
                <button
                  onClick={handleSendRequest}
                  disabled={!addUserId.trim()}
                  className="px-6 py-2 bg-green-800 hover:bg-green-700 disabled:bg-gray-700 disabled:text-gray-500 text-green-200 rounded font-bold transition-colors"
                >
                  送信
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
