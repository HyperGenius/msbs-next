interface ErrorBannerProps {
  message: string | null;
}

export function ErrorBanner({ message }: ErrorBannerProps) {
  if (!message) return null;
  return (
    <div className="border border-[#ff4400]/50 bg-[#ff4400]/10 p-3 text-[#ff4400] text-sm">
      {message}
    </div>
  );
}
