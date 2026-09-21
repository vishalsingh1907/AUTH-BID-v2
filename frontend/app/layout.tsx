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
    "Officer-Supervised Tender Compliance and Bidder Risk Assessment Platform for GeM Procurement. Combines deterministic statutory validation, structured evidence provenance, cross-bidder relationship analysis, explainable risk scoring, and model-assisted evidence review.",
  keywords: ["GeM", "Bid Verification", "Compliance", "Tender Integrity", "Government Procurement", "SIH26100"],
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
