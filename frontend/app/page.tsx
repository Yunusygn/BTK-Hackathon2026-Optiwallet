/**
 * Landing Page
 *
 * Uygulamanın ana sayfası. Hero section, özellikler ve CTA içerir.
 */

import Link from "next/link";
import { Sparkles, ShoppingCart, Brain, Zap, ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-background via-background to-brand-50/30 dark:to-brand-950/20">
      <div className="container max-w-6xl px-4 py-16">
        {/* Hero Section */}
        <div className="flex flex-col items-center text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-sm text-muted-foreground shadow-sm">
            <Sparkles className="h-3.5 w-3.5 text-brand-500" />
            <span>BTK Hackathon 2026 — AI Powered</span>
          </div>

          <h1 className="mb-6 text-5xl font-bold tracking-tight md:text-7xl">
            <span className="bg-gradient-to-br from-brand-600 to-brand-400 bg-clip-text text-transparent">
              OptiWallet
            </span>
          </h1>

          <p className="mb-4 text-2xl font-semibold tracking-tight md:text-3xl">
            Bütçeni söyle, gerisini bana bırak.
          </p>

          <p className="mb-12 max-w-2xl text-lg text-muted-foreground">
            Türkiye'nin AI destekli akıllı alışveriş danışmanı. 7 uzman ajan, piyasayı tarar,
            fiyatları karşılaştırır, bütçeni analiz eder ve en doğru kararı{" "}
            <span className="font-semibold text-foreground">gerekçeli olarak</span> sana sunar.
          </p>

          {/* CTA Buttons */}
          <div className="flex flex-col gap-4 sm:flex-row">
            <Link
              href="/chat"
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-6 py-3 text-base font-medium text-primary-foreground shadow-lg transition-all hover:bg-primary/90 hover:shadow-xl"
            >
              Hemen Başla
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-border bg-card px-6 py-3 text-base font-medium transition-all hover:bg-accent"
            >
              Giriş Yap
            </Link>
          </div>

          <p className="mt-4 text-sm text-muted-foreground">
            Misafir olarak başla — kayıt gerekmiyor
          </p>
        </div>

        {/* Features */}
        <div className="mt-24 grid gap-6 md:grid-cols-3">
          <FeatureCard
            icon={<Brain className="h-6 w-6" />}
            title="7 AI Ajanı"
            description="Araştırma, analiz, finans, strateji ve denetim — her ajan kendi alanında uzman."
          />
          <FeatureCard
            icon={<ShoppingCart className="h-6 w-6" />}
            title="40+ Pazaryeri"
            description="Trendyol, Hepsiburada, Amazon TR ve daha fazlası — anlık fiyat karşılaştırma."
          />
          <FeatureCard
            icon={<Zap className="h-6 w-6" />}
            title="10 Saniyede Karar"
            description="45 dakikalık alışveriş araştırması artık 10 saniye. Gerekçeli ve denetlenmiş."
          />
        </div>

        {/* Footer */}
        <footer className="mt-24 text-center text-sm text-muted-foreground">
          <p>© 2026 OptiWallet — BTK Hackathon Projesi</p>
          <p className="mt-1">Powered by Google Gemini</p>
        </footer>
      </div>
    </main>
  );
}

interface FeatureCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
}

function FeatureCard({ icon, title, description }: FeatureCardProps) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm transition-all hover:shadow-md">
      <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-lg bg-brand-100 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400">
        {icon}
      </div>
      <h3 className="mb-2 text-lg font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}