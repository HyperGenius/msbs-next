import { SignIn } from "@clerk/nextjs";
import { SciFiPanel, SciFiHeading } from "@/components/ui";

export default function SignInPage() {
  return (
    <main className="min-h-screen bg-[#050505] flex items-center justify-center px-4 py-12 font-mono">
      <SciFiPanel variant="primary" className="max-w-md w-full p-8">
        <div className="mb-6 text-center">
          <SciFiHeading level={2} variant="accent" className="border-l-0 pl-0 text-center">
            SYSTEM LOGIN
          </SciFiHeading>
          <p className="text-[#00ff41]/60 text-sm mt-2">
            &gt; Authenticate to access the simulator_
          </p>
        </div>
        <div className="flex justify-center">
          <SignIn
            appearance={{
              elements: {
                rootBox: "w-full",
                cardBox: "bg-transparent shadow-none w-full",
                card: "bg-transparent shadow-none border-0 w-full",
                headerTitle: "text-[#00ff41] font-mono",
                headerSubtitle: "text-[#00ff41]/60 font-mono",
                socialButtonsBlockButton:
                  "bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] hover:bg-[#00ff41]/10 hover:border-[#00ff41] font-mono",
                socialButtonsBlockButtonText: "text-[#00ff41] font-mono",
                formFieldLabel: "text-[#00ff41]/80 font-mono",
                formFieldInput:
                  "bg-[#0a0a0a] border border-[#00ff41]/30 text-[#00ff41] font-mono focus:border-[#00f0ff] focus:ring-[#00f0ff]/20",
                formButtonPrimary:
                  "bg-[#00ff41]/20 border border-[#00ff41] text-[#00ff41] hover:bg-[#00ff41]/30 font-mono uppercase tracking-wider",
                footerActionLink: "text-[#00f0ff] hover:text-[#00f0ff]/80 font-mono",
                footerActionText: "text-[#00ff41]/60 font-mono",
                dividerLine: "bg-[#00ff41]/20",
                dividerText: "text-[#00ff41]/40 font-mono",
                identityPreview: "bg-[#0a0a0a] border border-[#00ff41]/30",
                identityPreviewText: "text-[#00ff41] font-mono",
                identityPreviewEditButton: "text-[#00f0ff] font-mono",
                formFieldAction: "text-[#00f0ff] font-mono",
                alert: "bg-[#0a0a0a] border border-[#ffb000]/50 text-[#ffb000] font-mono",
              },
            }}
          />
        </div>
      </SciFiPanel>
    </main>
  );
}
