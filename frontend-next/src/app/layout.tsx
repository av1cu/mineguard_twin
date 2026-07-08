import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar } from "@/components/Sidebar";
import { TopBar } from "@/components/TopBar";

export const metadata: Metadata = {
  title: "MineGuard Twin — SCADA Console",
  description: "AI-driven open-pit mine digital twin SCADA console",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-[#030712] text-slate-100">
        <Providers>
          <div className="flex h-screen w-screen overflow-hidden">
            <Sidebar />
            <div className="flex flex-1 flex-col overflow-hidden">
              <TopBar />
              <main className="flex-1 overflow-y-auto bg-[#030712]">
                {children}
              </main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
