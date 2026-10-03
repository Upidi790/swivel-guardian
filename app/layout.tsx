import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Guardian — Scam Intervention Prototype",
  description: "A human-centered intervention layer for unusual, customer-authorized payments.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
