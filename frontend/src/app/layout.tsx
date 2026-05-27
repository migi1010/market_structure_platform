import type { Metadata } from "next";
import "./globals.css";
import { THEME } from "@/theme/theme"; // Assuming path aliasing, else relative

export const metadata: Metadata = {
  title: "MIJI Terminal",
  description: "Institutional market structure, alpha intelligence, and trading workflow terminal.",
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon-192.png", type: "image/png", sizes: "192x192" },
      { url: "/icon-512.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
    shortcut: ["/favicon.ico"],
  },
  applicationName: "MIJI Terminal",
  manifest: "/manifest.webmanifest",
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
