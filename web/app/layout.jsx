import "./globals.css";

export const metadata = {
  title: "BIFlow · From raw data to explained decisions",
  description: "AI agents prepare your data, compute your KPIs, detect what changes and explain every decision.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
