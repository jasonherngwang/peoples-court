import type { Metadata } from "next";
import { Crimson_Pro } from "next/font/google";
import "./globals.css";

const crimsonPro = Crimson_Pro({
  variable: "--font-crimson-pro",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Official High Court Registry of Social Grievances",
  description:
    "Formal adjudication portal for social conflicts. Managed by the People's Court.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${crimsonPro.variable} antialiased bg-background text-foreground min-h-screen selection:bg-navy selection:text-white`}
      >
        <div className="fixed inset-0 pointer-events-none opacity-5 paper-grain" />
        <main className="relative z-10">{children}</main>
      </body>
    </html>
  );
}
