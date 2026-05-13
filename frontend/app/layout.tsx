/**
 * Root Layout
 *
 * Tüm sayfaları saran ana layout.
 * Fontlar, theme provider, query client, toaster burada.
 */

import type { Metadata, Viewport } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Toaster } from "sonner";

import { Providers } from "@/components/providers";
import { cn } from "@/lib/utils";

import "./globals.css";

const inter = Inter({
  subsets: ["latin", "latin-ext"],
  variable: "--font-inter",
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000"),
  title: {
    default: "OptiWallet — Akıllı Alışveriş Danışmanı",
    template: "%s | OptiWallet",
  },
  description:
    "Türkiye'nin AI destekli alışveriş danışmanı. Bütçeni söyle, " +
    "OptiWallet piyasayı tarasın, en doğru kararı versin.",
  keywords: [
    "alışveriş danışmanı",
    "fiyat karşılaştırma",
    "AI shopping",
    "bütçe yönetimi",
    "Trendyol",
    "Hepsiburada",
    "akıllı alışveriş",
  ],
  authors: [{ name: "Yunus Emre Yeğin" }],
  creator: "OptiWallet",
  publisher: "OptiWallet",
  manifest: "/manifest.json",
  openGraph: {
    type: "website",
    locale: "tr_TR",
    url: "/",
    siteName: "OptiWallet",
    title: "OptiWallet — Akıllı Alışveriş Danışmanı",
    description: "AI destekli alışveriş danışmanı. 10 saniyede en doğru kararı al.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "OptiWallet",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "OptiWallet — Akıllı Alışveriş Danışmanı",
    description: "AI destekli alışveriş danışmanı.",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  icons: {
    icon: "/favicon.ico",
    shortcut: "/favicon-16x16.png",
    apple: "/apple-touch-icon.png",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
    { media: "(prefers-color-scheme: dark)", color: "#0c0a09" },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body
        className={cn(
          "min-h-screen bg-background font-sans antialiased",
          inter.variable,
          jetbrainsMono.variable,
        )}
      >
        <Providers>
          {children}
          <Toaster position="top-right" richColors closeButton />
        </Providers>
      </body>
    </html>
  );
}