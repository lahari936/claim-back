import type { Metadata } from "next";
import { Geist, Geist_Mono, Source_Serif_4 } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
const serif = Source_Serif_4({ variable: "--font-serif", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "ClaimBack",
  description: "Check a health-insurance claim rejection against your policy and draft the escalation.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} ${serif.variable} antialiased`}>
        <header className="border-b">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
            <Link href="/" className="font-serif text-xl font-semibold tracking-tight">
              Claim<span className="text-primary">Back</span>
            </Link>
            <span className="text-muted-foreground hidden text-sm sm:block">
              Health claim rejections, checked against your policy
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">{children}</main>
        <footer className="text-muted-foreground mx-auto max-w-6xl px-4 pb-10 text-xs sm:px-6">
          Drafts are for your review. Not legal or medical advice. Nothing is filed automatically.
        </footer>
      </body>
    </html>
  );
}
