/* frontend/src/app/garage/page.tsx */
"use client";

import Link from "next/link";
import Header from "@/components/Header";
import { SciFiButton, SciFiHeading, SciFiPanel } from "@/components/ui";
import { useGarageEditor } from "./hooks/useGarageEditor";
import MobileSuitList from "./components/MobileSuitList";
import MobileSuitEditor from "./components/MobileSuitEditor";
import WeaponChangeModal from "./components/WeaponChangeModal";

export default function GaragePage() {
  const {
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
    setFormData,
    setPreviewWeaponId,
    handleSelectMs,
    handleSubmit,
    handleOpenWeaponModal,
    handleCloseWeaponModal,
    handleEquipWeapon,
  } = useGarageEditor();

  if (isError) {
    return (
      <div className="min-h-screen bg-[#050505] text-[#00ff41] p-8 font-mono">
        <div className="max-w-6xl mx-auto">
          <SciFiPanel variant="secondary">
            <div className="p-6">
              <p className="text-[#ffb000] font-bold text-xl mb-2">ERROR: データ取得失敗</p>
              <p className="text-sm">Backendが起動しているか確認してください。</p>
            </div>
          </SciFiPanel>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-[#050505] text-[#00ff41] p-4 sm:p-6 md:p-8 font-mono">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <Header />
        <div className="mb-4 sm:mb-8 border-b-2 border-[#00ff41]/30 pb-4">
          <div className="flex flex-col sm:flex-row gap-4 sm:gap-0 justify-between items-start sm:items-center">
            <div>
              <SciFiHeading level={2} className="text-xl sm:text-2xl">GARAGE - Mobile Suit Hangar</SciFiHeading>
              <p className="text-xs sm:text-sm text-[#00ff41]/60 ml-0 sm:ml-5">機体管理システム</p>
            </div>
            <Link href="/" className="w-full sm:w-auto">
              <SciFiButton variant="primary" size="sm" className="w-full sm:w-auto">&lt; Back to Simulator</SciFiButton>
            </Link>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <SciFiPanel variant="accent">
              <div className="p-8">
                <p className="text-xl animate-pulse text-[#00f0ff]">LOADING DATA...</p>
              </div>
            </SciFiPanel>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            {/* Left Pane: 機体リスト */}
            <MobileSuitList
              mobileSuits={mobileSuits}
              selectedMs={selectedMs}
              onSelect={handleSelectMs}
            />

            {/* Right Pane: ステータス編集フォーム */}
            <MobileSuitEditor
              selectedMs={selectedMs}
              formData={formData}
              isSaving={isSaving}
              successMessage={successMessage}
              onFormDataChange={setFormData}
              onSubmit={handleSubmit}
              onOpenWeaponModal={handleOpenWeaponModal}
            />
          </div>
        )}

        {/* Weapon Change Modal */}
        {showWeaponModal && selectedMs && (
          <WeaponChangeModal
            selectedMs={selectedMs}
            selectedWeaponSlot={selectedWeaponSlot}
            weaponListings={weaponListings}
            pilot={pilot}
            previewWeaponId={previewWeaponId}
            onSetPreviewWeaponId={setPreviewWeaponId}
            onEquipWeapon={handleEquipWeapon}
            onClose={handleCloseWeaponModal}
          />
        )}
      </div>
    </main>
  );
}

