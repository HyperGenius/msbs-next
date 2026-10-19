/* frontend/src/app/garage/page.tsx */
"use client";

import { SciFiHeading, SciFiPanel } from "@/components/ui";
import { useGarageEditor } from "./hooks/useGarageEditor";
import MobileSuitList from "./components/MobileSuitList";
import WeaponInventoryList from "./components/WeaponInventoryList";
import CustomizationModal from "./components/CustomizationModal";
import WeaponChangeModal from "./components/WeaponChangeModal";

export default function GaragePage() {
  const {
    mobileSuits,
    isLoading,
    isError,
    pilot,
    weaponListings,
    playerWeapons,
    selectedMs,
    showCustomizationModal,
    isSaving,
    successMessage,
    showWeaponModal,
    selectedWeaponSlot,
    previewWeaponId,
    formData,
    activeTab,
    setFormData,
    setPreviewWeaponId,
    setActiveTab,
    handleSelectMs,
    handleCloseCustomizationModal,
    handleUpgraded,
    handleSubmit,
    handleOpenWeaponModal,
    handleCloseWeaponModal,
    handleEquipWeapon,
    handleNavigateToEquippedMs,
    handleEquipFromInventory,
    handleWeaponUpgraded,
  } = useGarageEditor();

  if (isError) {
    return (
      <div className="min-h-full bg-[#050505] text-[#00ff41] p-8 font-mono">
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

  // モバイルではページを main の高さに合わせ、タブの中のリストだけをスクロールさせる。
  // md 以上は main の高さ固定が外れるので、従来どおりページ全体をスクロールさせる。
  return (
    <div className="h-full overflow-hidden md:h-auto md:min-h-full md:overflow-visible bg-[#050505] text-[#00ff41] px-4 pb-3 sm:p-6 md:p-8 font-mono flex flex-col">
      <div className="max-w-6xl mx-auto w-full flex flex-col flex-1 min-h-0">
        {/* スマホでは見出しとタブを 1 行にまとめ、リストに使える高さを確保する */}
        <div className="shrink-0 mb-3 sm:mb-8 border-b-2 border-[#00ff41]/30 pb-2 sm:pb-4 flex items-end justify-between gap-2 sm:block">
          <div className="flex flex-col sm:flex-row gap-4 sm:gap-0 justify-between items-start sm:items-center">
            <div>
              <SciFiHeading level={2} className="text-xl sm:text-2xl">GARAGE</SciFiHeading>
            </div>
          </div>

          {/* タブ切り替え: 機体一覧 / 所持武器一覧 */}
          <div className="flex gap-1 sm:mt-4">
            <button
              type="button"
              aria-pressed={activeTab === "MOBILE_SUITS"}
              onClick={() => setActiveTab("MOBILE_SUITS")}
              className={`px-4 py-2 text-xs sm:text-sm font-bold font-mono tracking-wider transition-all whitespace-nowrap ${
                activeTab === "MOBILE_SUITS"
                  ? "bg-[#00ff41]/20 text-[#00ff41] border-b-2 border-[#00ff41]"
                  : "text-[#00ff41]/40 hover:text-[#00ff41]/70 hover:bg-[#00ff41]/5"
              }`}
            >
              機体一覧
            </button>
            <button
              type="button"
              aria-pressed={activeTab === "WEAPONS"}
              onClick={() => setActiveTab("WEAPONS")}
              className={`px-4 py-2 text-xs sm:text-sm font-bold font-mono tracking-wider transition-all whitespace-nowrap ${
                activeTab === "WEAPONS"
                  ? "bg-[#00ff41]/20 text-[#00ff41] border-b-2 border-[#00ff41]"
                  : "text-[#00ff41]/40 hover:text-[#00ff41]/70 hover:bg-[#00ff41]/5"
              }`}
            >
              所持武器一覧
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="shrink-0 flex justify-center items-center h-64">
            <SciFiPanel variant="accent">
              <div className="p-8">
                <p className="text-xl animate-pulse text-[#00f0ff]">LOADING DATA...</p>
              </div>
            </SciFiPanel>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto w-full flex flex-col flex-1 min-h-0">
            {activeTab === "MOBILE_SUITS" ? (
              <MobileSuitList
                mobileSuits={mobileSuits}
                selectedMs={selectedMs}
                onSelect={handleSelectMs}
              />
            ) : (
              <WeaponInventoryList
                mobileSuits={mobileSuits}
                isBusy={isSaving}
                pilot={pilot}
                onNavigateToEquippedMs={handleNavigateToEquippedMs}
                onEquip={handleEquipFromInventory}
                onWeaponUpgraded={handleWeaponUpgraded}
              />
            )}
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
            ownedMobileSuits={mobileSuits || []}
            playerWeapons={playerWeapons}
            previewWeaponId={previewWeaponId}
            onSetPreviewWeaponId={setPreviewWeaponId}
            onEquipWeapon={handleEquipWeapon}
            onClose={handleCloseWeaponModal}
          />
        )}
      </div>
    </div>
  );
}

