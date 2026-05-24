import type { Metadata } from "next";
import "./globals.css";
import { THEME } from "@/theme/theme"; // Assuming path aliasing, else relative

export const metadata: Metadata = {
  title: "Institutional Market Structure Platform",
  description: "AI-driven Decision Intelligence & Bubble Detection Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body style={{ backgroundColor: THEME.bg, color: THEME.text, margin: 0, minHeight: "100vh" }}>
        {children}
      </body>
    </html>
  );
}
