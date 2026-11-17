import type { Metadata } from "next";
import Link from "next/link";
import { Mic, Radio, LogIn, User } from "lucide-react";
import "./globals.css";
import { AppProviders } from "@/components/providers/AppProviders";
import { QuotaBadge } from "@/components/billing/QuotaBadge";

export const metadata: Metadata = {
  title: "Meeting Voice Assistant - Trợ Lý Cuộc Họp Thông Minh",
  description: "Hệ thống phiên âm, tách người nói và tra cứu cuộc họp AI thông minh",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="bg-slate-50 text-slate-900 antialiased min-h-screen flex flex-col font-sans">
        <AppProviders>
          {/* Header Navigation */}
          <header className="sticky top-0 z-40 border-b border-slate-200 bg-white/95 backdrop-blur-md">
            <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
              {/* Brand Logo */}
              <div className="flex items-center gap-6">
                <Link href="/" className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-xs">
                    <Mic className="w-4 h-4 text-emerald-400" />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-base tracking-tight text-slate-900">
                      VoiceAssistant
                    </span>
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 uppercase tracking-wider">
                      PRO
                    </span>
                  </div>
                </Link>

                {/* Primary Flat Navigation Tabs */}
                <nav className="hidden md:flex items-center gap-1 bg-slate-100/80 p-1 rounded-xl text-xs font-bold text-slate-600">
                  <Link
                    href="/"
                    className="px-3 py-1.5 rounded-lg hover:text-slate-900 hover:bg-white transition"
                  >
                    Cuộc Họp & Dự Án
                  </Link>
                  <Link
                    href="/live"
                    className="px-3 py-1.5 rounded-lg hover:text-slate-900 hover:bg-white transition flex items-center gap-1.5"
                  >
                    <Radio className="w-3.5 h-3.5 text-rose-500 animate-pulse" />
                    <span>Thu Âm Trực Tiếp</span>
                  </Link>
                </nav>
              </div>

              {/* Right Action Tools: Quota & User Menu */}
              <div className="flex items-center gap-3">
                <QuotaBadge />

                <Link
                  href="/settings/profile"
                  className="p-2 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 transition"
                  title="Cài đặt tài khoản"
                >
                  <User className="w-4 h-4" />
                </Link>
              </div>
            </div>
          </header>

          {/* Main Viewport */}
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8">
            {children}
          </main>
        </AppProviders>
      </body>
    </html>
  );
}
