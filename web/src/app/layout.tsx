import type { Metadata } from "next";

import { AppShell } from "@/components/app-shell";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "PromptGuard: DLP for AI prompts", template: "%s | PromptGuard" },
  description:
    "A lightweight gateway that checks prompts for secrets and personal data before they reach an AI tool, then blocks, redacts or warns.",
};

// Runs before first paint so a dark-mode visitor never sees a white flash.
const THEME_SCRIPT = `try{var t=localStorage.getItem('pg-theme');if(t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme: dark)').matches))document.documentElement.classList.add('dark')}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
