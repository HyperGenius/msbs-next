/* frontend/src/app/garage/hooks/useGarageEditor.ts */
"use client";

import { useState } from "react";
import {
  useMobileSuits,
  updateMobileSuit,
  usePilot,
  useWeaponListings,
  equipWeapon,
} from "@/services/api";
import { MobileSuit } from "@/types/battle";

/**
 * ガレージ編集画面の状態管理・API呼び出しをまとめたカスタムフック
 */
export function useGarageEditor() {
  const { mobileSuits, isLoading, isError, mutate } = useMobileSuits();
  const { pilot } = usePilot();
  const { weaponListings } = useWeaponListings();

  const [selectedMs, setSelectedMs] = useState<MobileSuit | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showWeaponModal, setShowWeaponModal] = useState(false);
  const [selectedWeaponSlot, setSelectedWeaponSlot] = useState(0);
  const [previewWeaponId, setPreviewWeaponId] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: "",
    max_hp: 0,
    armor: 0,
    mobility: 0,
    tactics: {
      priority: "CLOSEST" as
        | "CLOSEST"
        | "WEAKEST"
        | "RANDOM"
        | "STRONGEST"
        | "THREAT",
      range: "BALANCED" as "MELEE" | "RANGED" | "BALANCED" | "FLEE",
    },
  });

  // 機体選択時の処理
  const handleSelectMs = (ms: MobileSuit) => {
    setSelectedMs(ms);
    setFormData({
      name: ms.name,
      max_hp: ms.max_hp,
      armor: ms.armor,
      mobility: ms.mobility,
      tactics: ms.tactics || {
        priority: "CLOSEST",
        range: "BALANCED",
      },
    });
    setSuccessMessage(null);
  };

  // フォーム送信処理
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedMs) return;

    setIsSaving(true);
    setSuccessMessage(null);

    try {
      const updatedData = await updateMobileSuit(selectedMs.id, formData);
      setSuccessMessage("機体データを更新しました");
      mutate();
      setSelectedMs(updatedData);
    } catch (error) {
      console.error("Update error:", error);
      alert("更新に失敗しました。");
    } finally {
      setIsSaving(false);
    }
  };

  // 武器変更モーダルを開く
  const handleOpenWeaponModal = (slotIndex: number) => {
    setSelectedWeaponSlot(slotIndex);
    setPreviewWeaponId(null);
    setShowWeaponModal(true);
  };

  // 武器変更モーダルを閉じる
  const handleCloseWeaponModal = () => {
    setShowWeaponModal(false);
    setPreviewWeaponId(null);
  };

  // 武器を装備
  const handleEquipWeapon = async (weaponId: string) => {
    if (!selectedMs) return;

    setIsSaving(true);
    try {
      const updatedMs = await equipWeapon(selectedMs.id, {
        weapon_id: weaponId,
        slot_index: selectedWeaponSlot,
      });
      setSuccessMessage("武器を装備しました");
      setShowWeaponModal(false);
      setPreviewWeaponId(null);
      mutate();
      setSelectedMs(updatedMs);
    } catch (error) {
      console.error("Equip error:", error);
      alert(
        error instanceof Error ? error.message : "武器の装備に失敗しました"
      );
    } finally {
      setIsSaving(false);
    }
  };

  return {
    // data
    mobileSuits,
    isLoading,
    isError,
    pilot,
    weaponListings,
    selectedMs,
    isSaving,
    successMessage,
    showWeaponModal,
    selectedWeaponSlot,
    previewWeaponId,
    formData,
    // setters
    setFormData,
    setPreviewWeaponId,
    // handlers
    handleSelectMs,
    handleSubmit,
    handleOpenWeaponModal,
    handleCloseWeaponModal,
    handleEquipWeapon,
  };
}
