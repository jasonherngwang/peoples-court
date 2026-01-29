import type { Metadata } from "next";
import { Instrument_Serif, Instrument_Sans } from "next/font/google";
import "./globals.css";

const instrumentSerif = Instrument_Serif({
  variable: "--font-serif",
  subsets: ["latin"],
  display: "swap",
  weight: "400",
});

const instrumentSans = Instrument_Sans({
  variable: "--font-sans",
  subsets: ["latin"],
  display: "swap",
  weight: ["400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: "The People's Court — Social Grievance Adjudication",
  description:
    "Official portal for submission and adjudication of social conflicts. Verdicts rendered with precedent-based analysis.",
  icons: {
    icon: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${instrumentSerif.variable} ${instrumentSans.variable} antialiased bg-cream text-ink min-h-screen selection:bg-blue-light selection:text-white`}
      >
        <main className="relative">{children}</main>
      </body>
    </html>
  );
}
