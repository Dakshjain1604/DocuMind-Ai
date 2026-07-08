import type { Metadata } from "next";
import { Libre_Bodoni, Public_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const display = Libre_Bodoni({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const body = Public_Sans({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

const mono = JetBrains_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "DocuMind — Knowledge Cartography",
  description:
    "Hybrid GraphRAG over documents — vector × lexical × knowledge graph, with cited answers and an interactive entity atlas.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable} ${mono.variable}`}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
