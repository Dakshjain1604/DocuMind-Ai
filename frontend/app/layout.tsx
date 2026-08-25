import type { Metadata } from "next";
import { JetBrains_Mono, Geist } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";

// One clean sans-serif (Geist) for everything, headings included - no
// separate display serif. The high-contrast Libre Bodoni headline font
// read as ornate/editorial, not the simple, formal, high-readability look
// ChatGPT/Claude/Perplexity all share. See globals.css's --serif token,
// which now points at this same font instead of a second one.
const geist = Geist({subsets:['latin'],variable:'--font-sans'});

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
    <html lang="en" className={cn(mono.variable, "font-sans", geist.variable)}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
