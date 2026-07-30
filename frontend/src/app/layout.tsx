import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "Aegis AI — Enterprise AI Operations Copilot",
  description:
    "Production-grade multi-agent AI platform for enterprise operations. Autonomous investigation, root-cause analysis, and intelligent assistance.",
  openGraph: {
    title: "Aegis AI",
    description: "Enterprise AI Operations Copilot",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body>
        {children}
        <Toaster
          position="bottom-right"
          theme="dark"
          richColors
          closeButton
        />
      </body>
    </html>
  );
}
