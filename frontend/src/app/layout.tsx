import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Meeting Intelligence System",
  description: "Trợ lý phiên âm, tóm tắt và tra cứu cuộc họp AI",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="bg-slate-50 text-slate-900 antialiased min-h-screen">
        <header className="border-b border-slate-200 bg-white">
          <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-slate-900 tracking-tight">
                Meeting Intelligence
              </span>
              <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
                v1.0
              </span>
            </div>
            <nav className="flex items-center gap-6 text-sm font-medium text-slate-600">
              <a href="/" className="hover:text-slate-900 transition-colors">
                Danh Sách Cuộc Họp
              </a>
              <a href="/live" className="hover:text-slate-900 transition-colors">
                Phòng Ghi Âm Trực Tiếp
              </a>
            </nav>
          </div>
        </header>
        <main className="max-w-7xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
