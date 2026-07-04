import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SwissTech Stock Tracker",
  description: "Inventory management system for SwissTech",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
