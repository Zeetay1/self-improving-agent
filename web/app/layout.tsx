import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Self-Improving Ad Copy Agent",
  description:
    "A DTC ad-copy agent that scores its own outputs with an LLM judge, remembers the winners, and improves over time.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
