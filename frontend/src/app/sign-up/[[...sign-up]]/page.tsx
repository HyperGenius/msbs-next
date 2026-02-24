import { SignUp } from "@clerk/nextjs";
import { SciFiPanel, SciFiHeading } from "@/components/ui";

export default function SignUpPage() {
  return (
    <main className="min-h-screen bg-[#050505] flex items-center justify-center px-4 py-12 font-mono">
      <SciFiPanel variant="accent" className="max-w-md w-full p-8">
        <div className="mb-6 text-center">
          <SciFiHeading level={2} variant="accent" className="border-l-0 pl-0 text-center">
            NEW PILOT REGISTRATION
          </SciFiHeading>
          <p className="text-[#00f0ff]/60 text-sm mt-2">
            &gt; Initialize new pilot profile_
          </p>
        </div>
        <div className="flex justify-center">
          <SignUp
            appearance={{
              elements: {
                rootBox: "w-full",
                cardBox: "bg-transparent shadow-none w-full",
                card: "bg-transparent shadow-none border-0 w-full",
                headerTitle: "text-[#00f0ff] font-mono",
                headerSubtitle: "text-[#00f0ff]/60 font-mono",
                socialButtonsBlockButton:
                  "bg-[#0a0a0a] border border-[#00f0ff]/30 text-[#00f0ff] hover:bg-[#00f0ff]/10 hover:border-[#00f0ff] font-mono",
                socialButtonsBlockButtonText: "text-[#00f0ff] font-mono",
                formFieldLabel: "text-[#00f0ff]/80 font-mono",
                formFieldInput:
                  "bg-[#0a0a0a] border border-[#00f0ff]/30 text-[#00f0ff] font-mono focus:border-[#00ff41] focus:ring-[#00ff41]/20",
                formButtonPrimary:
                  "bg-[#00f0ff]/20 border border-[#00f0ff] text-[#00f0ff] hover:bg-[#00f0ff]/30 font-mono uppercase tracking-wider",
                footerActionLink: "text-[#00ff41] hover:text-[#00ff41]/80 font-mono",
                footerActionText: "text-[#00f0ff]/60 font-mono",
                dividerLine: "bg-[#00f0ff]/20",
                dividerText: "text-[#00f0ff]/40 font-mono",
                identityPreview: "bg-[#0a0a0a] border border-[#00f0ff]/30",
                identityPreviewText: "text-[#00f0ff] font-mono",
                identityPreviewEditButton: "text-[#00ff41] font-mono",
                formFieldAction: "text-[#00ff41] font-mono",
                alert: "bg-[#0a0a0a] border border-[#ffb000]/50 text-[#ffb000] font-mono",
              },
            }}
          />
        </div>
      </SciFiPanel>
    </main>
  );
}
