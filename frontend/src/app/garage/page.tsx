/* frontend/src/app/garage/page.tsx */
"use client";

import Link from "next/link";
import { SciFiButton, SciFiHeading, SciFiPanel } from "@/components/ui";
import { useGarageEditor } from "./hooks/useGarageEditor";
import MobileSuitList from "./components/MobileSuitList";
import CustomizationModal from "./components/CustomizationModal";
import WeaponChangeModal from "./components/WeaponChangeModal";

export default function GaragePage() {
  const {
    mobileSuits,
    isLoading,
    isError,
    pilot,
    weaponListings,
    selectedMs,
    showCustomizationModal,
    isSaving,
    successMessage,
    showWeaponModal,
    selectedWeaponSlot,
    previewWeaponId,
    formData,
    setFormData,
    setPreviewWeaponId,
    handleSelectMs,
    handleCloseCustomizationModal,
    handleUpgraded,
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
        <div className="mb-4 sm:mb-8 border-b-2 border-[#00ff41]/30 pb-4">
          <div className="flex flex-col sm:flex-row gap-4 sm:gap-0 justify-between items-start sm:items-center">
            <div>
              <SciFiHeading level={2} className="text-xl sm:text-2xl">GARAGE - Mobile Suit Hangar</SciFiHeading>
              <p className="text-xs sm:text-sm text-[#00ff41]/60 ml-0 sm:ml-5">機体管理システム — 機体をクリックしてカスタマイズ</p>
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
          <div className="max-w-3xl mx-auto">
            {/* 機体リスト（全幅表示） */}
            <MobileSuitList
              mobileSuits={mobileSuits}
              selectedMs={selectedMs}
              onSelect={handleSelectMs}
            />
          </div>
        )}

        {/* Customization Modal */}
        {showCustomizationModal && selectedMs && (
          <CustomizationModal
            mobileSuit={selectedMs}
            pilot={pilot}
            formData={formData}
            isSaving={isSaving}
            successMessage={successMessage}
            onFormDataChange={setFormData}
            onSubmit={handleSubmit}
            onOpenWeaponModal={handleOpenWeaponModal}
            onUpgraded={handleUpgraded}
            onClose={handleCloseCustomizationModal}
          />
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

