import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import TanstackQueryProvider from "@/providers/TanstackQueryProvider";
import DarkModeToggle from "@/components/DarkModeToggle";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ARSA | Autonomous Research Scientist Agent",
  description: "Autonomous multi-agent AI research team executing literature reviews, hypothesis debate, sandbox experiment coding, statistical evaluation, and peer-reviewed paper generation.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} dark`}>
      <body className="bg-background text-foreground antialiased min-h-screen flex flex-col">
        <TanstackQueryProvider>
          <header className="fixed top-4 right-4 z-50">
            <DarkModeToggle />
          </header>
          {children}
        </TanstackQueryProvider>
      </body>
    </html>
  );
}
