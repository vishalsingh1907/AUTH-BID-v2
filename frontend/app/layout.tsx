import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "AuthBid — GeM Compliance Intelligence",
  description:
    "AI-Powered Integrated Bid Compliance Verification Platform for GeM Procurement. OSINT-style entity resolution, cross-bidder collusion detection, and hash-chained audit trails.",
  keywords: ["GeM", "Bid Verification", "Compliance", "AI", "Government Procurement", "SIH"],
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/assets/logo-icon.png", type: "image/png" },
    ],
    apple: "/assets/logo-icon.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
