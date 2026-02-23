"use client";

import { useState } from "react";
import {
  useCurrentTeam,
  useFriends,
  createTeam,
  inviteTeamMember,
  toggleTeamReady,
  leaveTeam,
  teamEntry,
} from "@/services/api";
import { MobileSuit } from "@/types/battle";

interface TeamFormationModalProps {
  onClose: () => void;
  mobileSuits?: MobileSuit[];
}

export default function TeamFormationModal({
  onClose,
  mobileSuits,
}: TeamFormationModalProps) {
  const { team, isLoading, mutate: mutateTeam } = useCurrentTeam();
  const { friends } = useFriends();
  const [teamName, setTeamName] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [selectedMsId, setSelectedMsId] = useState<string>("");

  const clearMessages = () => {
    setMessage("");
    setError("");
  };

  const handleCreateTeam = async () => {
    if (!teamName.trim()) return;
    clearMessages();
    try {
      await createTeam(teamName.trim());
      mutateTeam();
      setTeamName("");
      setMessage("チームを作成しました");
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    }
  };

  const handleInvite = async (userId: string) => {
    if (!team) return;
    clearMessages();
    try {
      await inviteTeamMember(team.id, userId);
      mutateTeam();
      setMessage("メンバーを招待しました");
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    }
  };

  const handleToggleReady = async () => {
    if (!team) return;
    clearMessages();
    try {
      await toggleTeamReady(team.id);
      mutateTeam();
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    }
  };

  const handleLeave = async () => {
    if (!team) return;
    clearMessages();
    try {
      await leaveTeam(team.id);
      mutateTeam();
      setMessage("チームを離脱しました");
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    }
  };

  const handleTeamEntry = async () => {
    if (!team || !selectedMsId) return;
    clearMessages();
    try {
      const result = await teamEntry({
        team_id: team.id,
        mobile_suit_id: selectedMsId,
      });
      setMessage(result.message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "エラーが発生しました");
    }
  };

  // フレンドのうち、まだチームに招待していないメンバーのリスト
  const invitableFriends = friends?.filter(
    (f) => !team?.members.some((m) => m.user_id === f.friend_user_id || m.user_id === f.user_id)
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-gray-900 border-4 border-cyan-800 rounded-lg p-6">
          {/* Header */}
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-bold text-cyan-400">
              Team Formation
            </h2>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-red-900 hover:bg-red-800 rounded font-bold transition-colors"
            >
              ✕
            </button>
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

          {isLoading && (
            <p className="text-gray-400 text-center py-8">読み込み中...</p>
          )}

          {/* No Team - Create Form */}
          {!isLoading && !team && (
            <div className="space-y-4">
              <p className="text-gray-400">
                チームに所属していません。新しいチームを作成しましょう。
              </p>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={teamName}
                  onChange={(e) => setTeamName(e.target.value)}
                  placeholder="チーム名を入力"
                  className="flex-1 bg-gray-800 border border-gray-700 rounded px-4 py-2 text-gray-200 placeholder-gray-600 focus:border-cyan-500 focus:outline-none"
                />
                <button
                  onClick={handleCreateTeam}
                  disabled={!teamName.trim()}
                  className="px-6 py-2 bg-cyan-800 hover:bg-cyan-700 disabled:bg-gray-700 disabled:text-gray-500 text-cyan-200 rounded font-bold transition-colors"
                >
                  作成
                </button>
              </div>
            </div>
          )}

          {/* Team Details */}
          {!isLoading && team && (
            <div className="space-y-6">
              {/* Team Info */}
              <div className="bg-gray-800 border border-cyan-800/50 rounded-lg p-4">
                <div className="flex justify-between items-center mb-3">
                  <div>
                    <h3 className="text-xl font-bold text-cyan-400">
                      {team.name}
                    </h3>
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        team.status === "READY"
                          ? "bg-green-900 text-green-300"
                          : "bg-yellow-900 text-yellow-300"
                      }`}
                    >
                      {team.status === "READY" ? "準備完了" : "編成中"}
                    </span>
                  </div>
                </div>

                {/* Members */}
                <div className="space-y-2 mt-4">
                  <h4 className="text-sm font-bold text-gray-400 uppercase tracking-wider">
                    Members ({team.members.length}/3)
                  </h4>
                  {team.members.map((member) => (
                    <div
                      key={member.user_id}
                      className="bg-gray-900 border border-gray-700 rounded p-3 flex justify-between items-center"
                    >
                      <div className="flex items-center gap-3">
                        <span
                          className={`w-3 h-3 rounded-full ${
                            member.is_ready ? "bg-green-400" : "bg-gray-600"
                          }`}
                        />
                        <span className="text-gray-200">
                          {member.user_id === team.owner_user_id
                            ? "👑 "
                            : ""}
                          {member.user_id}
                        </span>
                      </div>
                      <span
                        className={`text-xs ${
                          member.is_ready
                            ? "text-green-400"
                            : "text-gray-500"
                        }`}
                      >
                        {member.is_ready ? "READY" : "NOT READY"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Invite Friends */}
              {invitableFriends && invitableFriends.length > 0 && team.members.length < 3 && (
                <div className="bg-gray-800 border border-cyan-800/50 rounded-lg p-4">
                  <h4 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">
                    フレンドを招待
                  </h4>
                  <div className="space-y-2">
                    {invitableFriends.map((friend) => (
                      <div
                        key={friend.id}
                        className="bg-gray-900 border border-gray-700 rounded p-3 flex justify-between items-center"
                      >
                        <span className="text-gray-200">
                          {friend.pilot_name || friend.friend_user_id}
                        </span>
                        <button
                          onClick={() => handleInvite(friend.friend_user_id)}
                          className="px-3 py-1 bg-cyan-900/50 hover:bg-cyan-800 text-cyan-300 rounded text-sm transition-colors"
                        >
                          招待
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={handleToggleReady}
                  className="px-6 py-2 bg-green-800 hover:bg-green-700 text-green-200 rounded font-bold transition-colors"
                >
                  Ready 切替
                </button>

                {team.status === "READY" && mobileSuits && mobileSuits.length > 0 && (
                  <div className="flex gap-2 items-center">
                    <select
                      value={selectedMsId}
                      onChange={(e) => setSelectedMsId(e.target.value)}
                      className="bg-gray-800 border border-gray-700 rounded px-3 py-2 text-gray-200"
                    >
                      <option value="">機体を選択</option>
                      {mobileSuits.map((ms) => (
                        <option key={ms.id} value={ms.id}>
                          {ms.name}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={handleTeamEntry}
                      disabled={!selectedMsId}
                      className="px-6 py-2 bg-yellow-700 hover:bg-yellow-600 disabled:bg-gray-700 disabled:text-gray-500 text-yellow-200 rounded font-bold transition-colors"
                    >
                      チームエントリー
                    </button>
                  </div>
                )}

                <button
                  onClick={handleLeave}
                  className="px-6 py-2 bg-red-900/50 hover:bg-red-800 text-red-300 rounded font-bold transition-colors"
                >
                  離脱
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
